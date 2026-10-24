"""一次真实三路径对照：共享初检，使用生产main审计和真实Auto/Agent，不传评分点。"""
import contextlib
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlsplit
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def question_inputs(questions):
    return [{'id':q['id'],'question':q['question']} for q in questions]


def shared_initial(rag):
    """不把另一条路径的答案、提示、分解或评分内容带入Agent/Auto。"""
    value={key:deepcopy(rag[key]) for key in
           ('query','knowledge_base','retrieval_diagnostics','selected_ids','context','ledger')}
    value['status']='retrieval_completed'
    return value


def audited_request(prompt,current,calls,protocol,request,persist,settings):
    """每次请求前落盘；仅同题同路径的完整成功响应可续接，失败不重试。"""
    if settings()!=protocol['api_public_settings']:
        raise RuntimeError('Public API options changed after freeze.')
    signature=hashlib.sha256(json.dumps([current['qid'],current['stage'],prompt,
                             protocol['api_public_settings']],sort_keys=True).encode()).hexdigest()
    previous=next((c for c in calls if c['signature']==signature),None)
    if previous:
        if previous['status']!='completed':
            raise RuntimeError('Identical request already attempted; no automatic retry.')
        return previous['response']
    if len(calls)>=protocol['max_actual_chat_attempts']:
        raise RuntimeError('Global attempt budget exhausted.')
    if sum(c['question_id']==current['qid'] for c in calls)>=protocol['max_actual_chat_attempts_per_question']:
        raise RuntimeError('Per-question attempt budget exhausted.')
    entry={'number':len(calls)+1,'question_id':current['qid'],'stage':current['stage'],
           'signature':signature,'prompt':prompt,'status':'running','http_posts':0,
           'started_at_utc':datetime.now(timezone.utc).isoformat()}
    calls.append(entry);persist()
    started=time.perf_counter()
    try:
        response=request(prompt)
        entry.update(status='completed',response=response)
        return response
    except Exception as exc:
        entry.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        if hasattr(exc,'response'):entry['response']=exc.response
        raise
    finally:
        entry['elapsed_seconds']=round(time.perf_counter()-started,4)
        persist()
        print(f"{current['qid']} {current['stage']} #{entry['number']}: {entry['status']} ({entry['elapsed_seconds']}s)",
              file=sys.__stdout__,flush=True)


def main():
    protocol=json.loads((OUT/'frozen_protocol.json').read_text())
    for path,expected in protocol['source_hashes'].items():
        assert sha(ROOT/path)==expected,f'Frozen input changed: {path}'
    qs=question_inputs(json.loads((OUT/'questions_frozen.json').read_text()))
    if all((OUT/'cases'/q['id']/'result.json').exists() for q in qs):
        print('All cases terminal; no API requests repeated.');return
    sys.path.insert(0,str(ROOT))
    from src import api_llm as api
    settings=lambda:{key:api.load_settings().get(key) for key in ('base_url','model','chat_options')}
    assert settings()==protocol['api_public_settings']
    endpoint=urlsplit(settings()['base_url'])
    with socket.create_connection((endpoint.hostname,endpoint.port or 80),timeout=3):pass
    import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    import main as pipeline
    from src import agent_tools
    assert (pipeline.RETRIEVAL_TOP_K,pipeline.RERANK_TOP_K,pipeline.RRF_TOP_K,pipeline.RRF_K)==(120,10,120,60)
    assert pipeline.USE_EVIDENCE_COMPLETION and not pipeline.USE_HYDE and not pipeline.USE_MULTI_QUERY
    warm=time.perf_counter();resources=agent_tools.load_search_resources()
    assert resources['knowledge_base']['version']==protocol['kb_version']
    save(OUT/'resource_loading.json',{'elapsed_seconds':round(time.perf_counter()-warm,4),
                                     'included_in_path_latency':False,'knowledge_base':resources['knowledge_base']})
    calls_path=OUT/'actual_chat_calls.json'
    calls=json.loads(calls_path.read_text()) if calls_path.exists() else []
    current={};raw_chat,raw_http=api.chat_completion,api._request
    persist=lambda:save(calls_path,calls)

    def observed_http(path,payload=None):
        if path=='/chat/completions':
            assert calls and calls[-1]['status']=='running'
            calls[-1]['http_posts']+=1
            assert calls[-1]['http_posts']==1,'Hidden HTTP retry detected.'
            persist()
        return raw_http(path,payload)

    def request(prompt):
        response=raw_chat(prompt)
        if response.get('finish_reason')!='stop':raise api.IncompleteResponseError(response)
        return response

    def call(prompt):
        return audited_request(prompt,current,calls,protocol,request,persist,settings)

    def rag_generate(prompt):
        if current['stage']=='initial':
            current['initial_seconds']=time.perf_counter()-current['rag_started']
            current['stage']='rag'
        return api.generate_final_answer(prompt)

    batch_started=time.perf_counter()
    with patch.object(pipeline,'load_knowledge_base',return_value=(resources['index'],resources['chunks'],resources['knowledge_base'])), \
         patch.object(pipeline,'load_embedding_model',return_value=resources['embedding_model']), \
         patch.object(pipeline,'CrossEncoder',return_value=resources['reranker_model']), \
         patch.object(pipeline,'build_bm25_index',return_value=resources['bm25']), \
         patch.object(pipeline,'generate_final_answer',side_effect=rag_generate), \
         patch.object(api,'_request',side_effect=observed_http),patch.object(api,'chat_completion',side_effect=call):
        for q in qs:
            qid=q['id'];folder=OUT/'cases'/qid;folder.mkdir(parents=True,exist_ok=True)
            if (folder/'result.json').exists():continue
            current.clear();current.update(qid=qid,stage='initial',rag_started=time.perf_counter())
            record={'id':qid,'question':q['question'],'status':'running','arms':{}}
            try:
                if (folder/'rag.json').exists():
                    rag=json.loads((folder/'rag.json').read_text());shared=json.loads((folder/'shared.json').read_text())
                else:
                    with (folder/'rag.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                        rag=pipeline.main(q['question'],kb_version=protocol['kb_version'],completion_rounds=2,mode='rag')
                    rag['status']='completed' if rag['citation_validation']['final_check']['structure_passed'] else 'failed'
                    shared={'initial_seconds':round(current['initial_seconds'],4),
                            'rag_path_seconds':round(time.perf_counter()-current['rag_started'],4),
                            'initial_call_numbers':[c['number'] for c in calls if c['question_id']==qid and c['stage']=='initial']}
                    save(folder/'shared.json',shared);save(folder/'rag.json',rag)
                    (folder/'rag_answer.md').write_text(rag['answer']+'\n',encoding='utf-8')
                record['arms']['rag']={'status':rag['status'],'path_seconds':shared['rag_path_seconds']}
                initial=shared_initial(rag)
                save(folder/'initial.json',initial)

                def reuse_initial(query,kb_version,complete_evidence,completion_rounds,agent_output,agent_call,agent_mode):
                    assert query==initial['query'] and kb_version==protocol['kb_version']
                    assert complete_evidence is None and completion_rounds==2
                    return pipeline._answer_with_agent(deepcopy(initial),resources,agent_output,agent_call,mode=agent_mode)

                for arm in ('agent','auto'):
                    current['stage']=arm;arm_dir=folder/arm
                    if (arm_dir/'result.json').exists():
                        result=json.loads((arm_dir/'result.json').read_text())
                        timing=json.loads((folder/f'{arm}_timing.json').read_text())
                    else:
                        started=time.perf_counter()
                        try:
                            with patch.object(pipeline,'_run_pipeline',side_effect=reuse_initial), \
                                 (folder/f'{arm}.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                                result=pipeline.main(q['question'],mode=arm,output_dir=arm_dir)
                        except Exception as exc:
                            result=json.loads((arm_dir/'result.json').read_text())
                            result['error']=f'{type(exc).__name__}: {exc}'
                        timing={'increment_seconds':round(time.perf_counter()-started,4)}
                        timing['path_seconds']=round(shared['initial_seconds']+timing['increment_seconds'],4)
                        save(folder/f'{arm}_timing.json',timing)
                    record['arms'][arm]={'status':result['status'],**timing,
                                         'route':result.get('routing',{}).get('route')}
                record['status']='completed'
            except Exception as exc:
                record.update(status='failed',error=f'{type(exc).__name__}: {exc}')
            save(folder/'result.json',record)
            print(qid,'terminal',record['status'],{k:v['status'] for k,v in record['arms'].items()},flush=True)
            if any(c['question_id']==qid and c['status']=='failed' and any(word in c.get('error','') for word in
                   ('连接失败','HTTP 503','HTTP 429','ConnectionError','TimeoutError')) for c in calls):break
    persist()
    save(OUT/'execution_summary.json',{'planned':len(qs),
         'terminal_records':sum((OUT/'cases'/q['id']/'result.json').exists() for q in qs),
         'actual_client_attempts':len(calls),'actual_http_posts':sum(c['http_posts'] for c in calls),
         'failed_attempts':sum(c['status']!='completed' for c in calls),'automatic_retries':0,
         'this_session_elapsed_seconds':round(time.perf_counter()-batch_started,4)})


if __name__=='__main__':main()
