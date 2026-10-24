"""真实P2.5成对评测；复用生产函数，不更改生产提示、决策或检索算法。"""
import contextlib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlsplit
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def question_inputs(questions):
    """评分点与Gold不能进入被测系统输入。"""
    return [{'id': q['id'], 'question': q['question']} for q in questions]


def audited_request(prompt, current, calls, protocol, request, persist, settings):
    """请求前记账；精确续接成功响应，失败/中断不自动重试。"""
    if settings() != protocol['api_public_settings']:
        raise RuntimeError('Public API options changed after freeze.')
    signature = hashlib.sha256(json.dumps([current['qid'], current['stage'], prompt,
                                            protocol['api_public_settings']], sort_keys=True).encode()).hexdigest()
    prior = next((c for c in calls if c['signature'] == signature), None)
    if prior:
        if prior['status'] != 'completed':
            raise RuntimeError('Identical request was already attempted; no automatic retry.')
        return prior['response']
    if len(calls) >= protocol['max_actual_chat_attempts']:
        raise RuntimeError('Global attempt budget exhausted.')
    if sum(c['question_id'] == current['qid'] for c in calls) >= protocol['max_actual_chat_attempts_per_question']:
        raise RuntimeError('Per-question attempt budget exhausted.')
    entry = {'number': len(calls)+1, 'question_id': current['qid'], 'stage': current['stage'],
             'signature': signature, 'prompt': prompt, 'status': 'running', 'http_posts': 0,
             'started_at_utc': datetime.now(timezone.utc).isoformat()}
    calls.append(entry)
    persist()
    started = time.perf_counter()
    try:
        response = request(prompt)
        entry.update(status='completed', response=response)
        return response
    except Exception as exc:
        entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        if hasattr(exc, 'response'):
            entry['response'] = exc.response
        raise
    finally:
        entry['elapsed_seconds'] = round(time.perf_counter()-started, 4)
        persist()
        print(f"{current['qid']} {current['stage']} request {entry['number']}: {entry['status']} ({entry['elapsed_seconds']}s)",
              file=sys.__stdout__, flush=True)


def main():
    protocol = json.loads((OUT/'frozen_protocol.json').read_text())
    for name, expected in protocol['source_hashes'].items():
        assert sha(ROOT/name) == expected, f'Frozen input changed: {name}'
    sys.path.insert(0, str(ROOT))
    from src import api_llm as api
    settings = lambda: {key: api.load_settings().get(key) for key in ('base_url', 'model', 'chat_options')}
    assert settings() == protocol['api_public_settings']
    questions = question_inputs(json.loads((OUT/'questions_frozen.json').read_text()))
    if all((OUT/'cases'/q['id']/'result.json').exists() for q in questions):
        print('All cases have terminal records. No API requests repeated.', flush=True)
        return
    # 纯socket预检，不创建chat请求；权限或反代不可用时在模型调用前停止。
    endpoint = urlsplit(settings()['base_url'])
    with socket.create_connection((endpoint.hostname, endpoint.port or 80), timeout=3):
        pass
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    import agent
    from src import agent_tools
    assert (pipeline.RETRIEVAL_TOP_K, pipeline.RERANK_TOP_K, pipeline.RRF_TOP_K, pipeline.RRF_K) == (120,10,120,60)
    assert pipeline.USE_EVIDENCE_COMPLETION and not pipeline.USE_HYDE and not pipeline.USE_MULTI_QUERY
    warm = time.perf_counter()
    resources = agent_tools.load_search_resources()
    assert resources['knowledge_base']['version'] == protocol['kb_version']
    save(OUT/'resource_loading.json', {'elapsed_seconds': round(time.perf_counter()-warm, 4), 'included_in_path_latency': False,
                                     'knowledge_base': resources['knowledge_base']})
    calls_path = OUT/'actual_chat_calls.json'
    calls = json.loads(calls_path.read_text()) if calls_path.exists() else []
    current = {}
    raw_chat, raw_http = api.chat_completion, api._request
    persist = lambda: save(calls_path, calls)

    def observed_http(path, payload=None):
        if path == '/chat/completions':
            assert calls and calls[-1]['status'] == 'running'
            calls[-1]['http_posts'] += 1
            assert calls[-1]['http_posts'] == 1, 'Hidden HTTP retry detected.'
            persist()
        return raw_http(path, payload)

    def call(prompt):
        return audited_request(prompt, current, calls, protocol, raw_chat, persist, settings)

    def rag_generate(prompt):
        if current['stage'] == 'initial':
            current['initial_seconds'] = time.perf_counter()-current['rag_started']
            current['stage'] = 'rag_answer'
        return api.generate_final_answer(prompt)

    batch_started = time.perf_counter()
    with patch.object(pipeline, 'load_knowledge_base', return_value=(resources['index'],resources['chunks'],resources['knowledge_base'])), \
         patch.object(pipeline, 'load_embedding_model', return_value=resources['embedding_model']), \
         patch.object(pipeline, 'CrossEncoder', return_value=resources['reranker_model']), \
         patch.object(pipeline, 'build_bm25_index', return_value=resources['bm25']), \
         patch.object(pipeline, 'generate_final_answer', side_effect=rag_generate), \
         patch.object(api, '_request', side_effect=observed_http), patch.object(api, 'chat_completion', side_effect=call):
        for q in questions:
            qid = q['id']
            folder = OUT/'cases'/qid
            folder.mkdir(parents=True, exist_ok=True)
            result_path = folder/'result.json'
            if result_path.exists(): continue
            current.clear()
            current.update(qid=qid, stage='initial', rag_started=time.perf_counter())
            record = {'id': qid, 'question': q['question'], 'status': 'running'}
            rag_path, shared_path = folder/'rag.json', folder/'shared.json'
            try:
                if rag_path.exists():
                    rag = json.loads(rag_path.read_text())
                    shared = json.loads(shared_path.read_text())
                else:
                    with (folder/'rag.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                        rag = pipeline.main(q['question'], kb_version=protocol['kb_version'], completion_rounds=2)
                    rag['status'] = 'completed'
                    shared = {'initial_seconds': round(current['initial_seconds'],4),
                              'rag_seconds': round(time.perf_counter()-current['rag_started'],4),
                              'initial_call_numbers': [c['number'] for c in calls if c['question_id']==qid and c['stage']=='initial'],
                              'rag_answer_call_numbers': [c['number'] for c in calls if c['question_id']==qid and c['stage']=='rag_answer']}
                    save(rag_path, rag)
                    save(shared_path, shared)
                    (folder/'rag_answer.md').write_text(rag['answer']+'\n')
                record['rag_status'] = rag['status']
                # 复用已有可信输入加载器，传入白名单，旧答案/Gold/分解不进入Agent。
                cases, hashes = agent.load_replay_cases(ROOT, folder, ['rag'])
                cases = {qid: cases['rag']}
                # 加载器按文件名寻找rag.json，后续实验身份沿用真实qid。
                current['stage'] = 'agent_decision'
                agent_started = time.perf_counter()
                decision = agent.run_diagnostics(cases, folder/'loop', hashes, call=call, resources=resources, max_actions=3)
                record['decision_summary'] = decision
                record['agent_status'] = 'failed'
                if decision['completed_cases'] == 1:
                    current['stage'] = 'agent_answer'
                    answer_summary = agent.run_answer(ROOT, folder/'loop'/f'{qid}.json', folder/'answer', call=call)
                    record['answer_summary'] = answer_summary
                    record['agent_status'] = answer_summary['status']
                record['agent_increment_seconds'] = round(time.perf_counter()-agent_started,4)
                record['agent_path_seconds'] = round(shared['initial_seconds']+record['agent_increment_seconds'],4)
                record['rag_path_seconds'] = shared['rag_seconds']
                record['status'] = 'completed'
            except Exception as exc:
                record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            save(result_path, record)
            print(qid, 'case', record['status'], 'agent', record.get('agent_status'), flush=True)
            # 连接错误说明服务/网络前提失效；不把相同故障扩散到余下所有题。
            if any(c['question_id']==qid and c['status']=='failed' and
                   ('连接失败' in c.get('error','') or 'HTTP 503' in c.get('error','') or 'HTTP 429' in c.get('error','')) for c in calls):
                break
    persist()
    save(OUT/'execution_summary.json', {'planned': len(questions), 'terminal_records': sum((OUT/'cases'/q['id']/'result.json').exists() for q in questions),
         'actual_client_attempts': len(calls), 'actual_http_posts': sum(c['http_posts'] for c in calls),
         'failed_attempts': sum(c['status']!='completed' for c in calls), 'automatic_retries': 0,
         'this_session_elapsed_seconds': round(time.perf_counter()-batch_started,4)})


if __name__ == '__main__':
    main()
