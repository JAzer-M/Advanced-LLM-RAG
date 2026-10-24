"""冻结后的小规模开发回归；复用原真实初检，不重跑旧8题、不传旧答案或评分。"""
import contextlib
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.results.auto_closeout_20261022.run_comparison import audited_request,save,sha,shared_initial


def prepare():
    if (OUT/'frozen_protocol.json').exists():raise RuntimeError('Already frozen.')
    from src import api_llm as api
    old=ROOT/'evaluation/results/auto_closeout_20261022/cases'
    plans=[('h10_auto','auto',ROOT/'evaluation/results/holdout_v1_20261020/h10.json',7)]
    inputs=[]
    for rid,mode,path,cap in plans:
        initial=shared_initial(json.loads(path.read_text()))
        item={'id':rid,'mode':mode,'initial':initial,'origin':str(path.relative_to(ROOT)),
              'origin_sha256':sha(path),'max_attempts':cap}
        inputs.append(item)
    save(OUT/'run_inputs.json',inputs)
    cache_source=ROOT/'evaluation/results/agent_auto_improvement_20261022/final/actual_chat_calls.json'
    cached=next(c for c in json.loads(cache_source.read_text()) if c['question_id']=='h10_auto')
    cache_public=json.loads((cache_source.parent/'frozen_protocol.json').read_text())['api_public_settings']
    save(OUT/'probe_cache.json',{'entry':cached,'origin':str(cache_source.relative_to(ROOT)),
                               'origin_sha256':sha(cache_source),'api_public_settings':cache_public})
    paths=[ROOT/'agent.py',ROOT/'main.py',*sorted((ROOT/'src').glob('*.py')),
           ROOT/'tests/test_agent_auto_improvements.py',ROOT/'tests/test_main_auto.py',
           OUT/'run_validation.py',OUT/'run_inputs.json',OUT/'probe_cache.json',
           ROOT/'evaluation/results/auto_closeout_20261022/run_comparison.py']
    public={k:api.load_settings().get(k) for k in ('base_url','model','chat_options')}
    protocol={'stage':'Known-case development regression, not held-out accuracy',
              'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'api_public_settings':public,
              'max_actual_chat_attempts':sum(x['max_attempts'] for x in inputs),
              'max_actual_chat_attempts_per_question':7,'automatic_retries':0,'max_new_http_posts':6,
              'cached_probe':'One exact successful prior probe; logical usage retained, new billing excludes HTTP=0 cache rows.',
              'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths},
              'expected_checks':{'a03_auto':'Threshold values, citation support, one gate, direct delivery.',
                                 'a04_agent':'Beam4 for Transformer and RAG generation; RAG ten docs; no QA settings transfer.',
                                 'a04_auto':'Same facts, one gate before direct generation.',
                                 'a02_agent':'Four LRN constants and after-ReLU, no unsupported extra formula.',
                                 'h10_rag':'Same original incomplete initial context; assess honest partial answer/unsupported inference.',
                                 'h10_auto':'Find RAG EM and Self-RAG answer inclusion with actual local tools; do not guess.'},
              'comparison':'h10 uses the same unmodified original initial evidence for both paths. No synthetic deletion.',
              'limits':'No new-set claim, no tuning after freeze, stop on transport failure, no automatic retry.'}
    save(OUT/'frozen_protocol.json',protocol)
    for p in paths:
        if p.is_relative_to(OUT):continue
        dest=OUT/'source_after'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    print(json.dumps({'runs':len(inputs),'max_actual_attempts':protocol['max_actual_chat_attempts'],'API_calls':0}))


def main():
    protocol=json.loads((OUT/'frozen_protocol.json').read_text())
    for name,digest in protocol['source_hashes'].items():assert sha(ROOT/name)==digest,name
    runs=json.loads((OUT/'run_inputs.json').read_text())
    if all((OUT/'runs'/r['id']/'result.json').exists() for r in runs):
        print('All development runs terminal. No repeated API requests.');return
    from src import api_llm as api
    import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    import main as pipeline
    from src import agent_tools
    warm=time.perf_counter();resources=agent_tools.load_search_resources()
    save(OUT/'resource_loading.json',{'elapsed_seconds':time.perf_counter()-warm,'excluded_from_increment_latency':True})
    calls_path=OUT/'actual_chat_calls.json'
    calls=json.loads(calls_path.read_text()) if calls_path.exists() else []
    raw_chat,raw_request=api.chat_completion,api._request
    current={};persist=lambda:save(calls_path,calls)
    settings=lambda:{k:api.load_settings().get(k) for k in ('base_url','model','chat_options')}
    def observed(path,payload=None):
        if path=='/chat/completions':
            assert calls[-1]['status']=='running';calls[-1]['http_posts']+=1
            assert calls[-1]['http_posts']==1;persist()
        return raw_request(path,payload)
    cache=json.loads((OUT/'probe_cache.json').read_text())
    assert cache['api_public_settings']==settings()
    def request(prompt):
        if prompt==cache['entry']['prompt']:
            calls[-1]['response_source']={'reused_completed_probe':True,'origin':cache['origin'],
                                         'original_call_number':cache['entry']['number']}
            persist()
            return cache['entry']['response']
        if sum(c['http_posts'] for c in calls)>=6:
            raise RuntimeError('Six-new-HTTP-request follow-up budget exhausted.')
        return raw_chat(prompt)
    def call(prompt):
        if sum(c['question_id']==current['qid'] for c in calls)>=current['cap']:
            raise RuntimeError('Frozen per-run development budget exhausted.')
        return audited_request(prompt,current,calls,protocol,request,persist,settings)
    with patch.object(api,'_request',side_effect=observed),patch.object(api,'chat_completion',side_effect=call):
        for r in runs:
            folder=OUT/'runs'/r['id']
            if (folder/'result.json').exists():continue
            folder.mkdir(parents=True,exist_ok=True)
            current.update(qid=r['id'],stage=r['mode'],cap=r['max_attempts'])
            initial=r['initial'];started=time.perf_counter()
            try:
                if r['mode']=='rag':
                    with (folder/'stdout.log').open('w') as log,contextlib.redirect_stdout(log):
                        prompt=pipeline.build_prompt(initial['query'],initial['context'])
                        draft=api.generate_final_answer(prompt)
                        check=pipeline.repair_citations_once(initial['query'],initial['context'],draft,
                              initial['ledger']['citation_registry'],api.generate_final_answer)
                    save(folder/'result.json',{**initial,'mode':'rag','status':'completed' if check['final_check']['structure_passed'] else 'failed',
                                               'answer':check['answer'],'citation_validation':check})
                else:
                    def reuse(query,kb_version,complete_evidence,completion_rounds,agent_output,agent_call,agent_mode):
                        assert query==initial['query'] and kb_version==initial['knowledge_base']['version']
                        return pipeline._answer_with_agent(deepcopy(initial),resources,agent_output,agent_call,mode=agent_mode)
                    with patch.object(pipeline,'_run_pipeline',side_effect=reuse), \
                         patch('src.knowledge_base.load_knowledge_base',return_value=(resources['index'],resources['chunks'],resources['knowledge_base'])), \
                         (OUT/f'{r["id"]}.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                        pipeline.main(initial['query'],mode=r['mode'],output_dir=folder)
            except Exception as exc:
                if not (folder/'result.json').exists():save(folder/'result.json',{'status':'failed','error':f'{type(exc).__name__}: {exc}'})
            save(OUT/'timings'/f'{r["id"]}.json',{'increment_seconds':round(time.perf_counter()-started,4),
                                               'initial_retrieval_rerun':False})
            print(r['id'],json.loads((folder/'result.json').read_text())['status'],flush=True)
            if any(c['question_id']==r['id'] and c['status']!='completed' for c in calls):break
    save(OUT/'execution_summary.json',{'planned_runs':len(runs),'terminal_runs':sum((OUT/'runs'/r['id']/'result.json').exists() for r in runs),
                                      'attempts':len(calls),'http_posts':sum(c['http_posts'] for c in calls),
                                      'failed_attempts':sum(c['status']!='completed' for c in calls),'automatic_retries':0,
                                      'cached_probe_logical_calls':sum(bool(c.get('response_source')) for c in calls)})


if __name__=='__main__':
    if '--prepare' in sys.argv:prepare()
    else:main()
