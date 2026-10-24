"""仅重跑三道开发失败题；复用已保存初检，调用现有Agent，不重跑RAG或改写旧成绩。"""
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlsplit
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OLD = OUT.parent / 'agent_p25_20261021'
QIDS = ('b02', 'b03', 'b06')
sys.path.insert(0, str(ROOT))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import agent
    from src import api_llm as api
    from src import agent_tools
    # 复用已离线验证的预写记账/硬上限函数；原P2.5目录只读。
    spec = importlib.util.spec_from_file_location('p25_audit', OLD / 'run_comparison.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    public = lambda: {key: api.load_settings().get(key) for key in ('base_url', 'model', 'chat_options')}
    assert public() == json.loads((OLD/'frozen_protocol.json').read_text())['api_public_settings']
    paths = [ROOT/'agent.py', ROOT/'src/agent_answer.py', ROOT/'src/api_llm.py',
             ROOT/'src/agent_tools.py', OUT/'run_regression.py', OLD/'run_comparison.py',
             OLD/'review_protocol.md', OLD/'questions_frozen.json', OLD/'actual_chat_calls.json']
    paths += [ROOT/'data/processed/versions/all-papers-8-20261020'/name
              for name in ('manifest.json', 'chunks.json', 'faiss.index')]
    paths += [OLD/'cases'/qid/'rag.json' for qid in QIDS]
    paths += sorted((ROOT/'src').glob('*.py'))
    protocol = {'stage': 'planning-fix development regression, not a new holdout',
                'case_ids': list(QIDS), 'max_actual_chat_attempts': 30,
                'max_actual_chat_attempts_per_question': 10,
                'max_decision_calls_per_case': 6, 'max_answer_calls_per_case': 4,
                'max_tool_actions_per_case': 3, 'decision_validation_repairs_per_case': 1,
                'automatic_transport_retries': 0, 'api_public_settings': public(),
                'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in paths},
                'review': 'Reuse frozen P2.5 core points, contiguous quotations and citation checks; '
                          'same assistant review, no independent or new-set improvement claim.'}
    frozen = OUT/'frozen_protocol.json'
    if frozen.exists():
        prior = json.loads(frozen.read_text())
        assert {k:v for k,v in prior.items() if k != 'frozen_at_utc'} == protocol
    else:
        save(frozen, {**protocol, 'frozen_at_utc': datetime.now(timezone.utc).isoformat()})
    if all((OUT/'cases'/qid/'result.json').exists() for qid in QIDS):
        print('All development cases already have terminal records; new API requests: 0.', flush=True)
        return
    endpoint = urlsplit(public()['base_url'])
    try:
        with socket.create_connection((endpoint.hostname, endpoint.port or 80), timeout=3):
            pass
    except Exception as exc:
        save(OUT/'preflight_failure.json', {'at_utc':datetime.now(timezone.utc).isoformat(),
             'error':f'{type(exc).__name__}: {exc}', 'chat_attempts':0})
        raise
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    warm = time.perf_counter()
    resources = agent_tools.load_search_resources()
    save(OUT/'resource_loading.json', {'seconds': time.perf_counter()-warm,
                                     'knowledge_base':resources['knowledge_base']})
    ledger = OUT/'actual_chat_calls.json'
    calls = json.loads(ledger.read_text()) if ledger.exists() else []
    current = {}
    raw_chat, raw_http = api.chat_completion, api._request
    persist = lambda: save(ledger, calls)

    def observed_http(path, payload=None):
        if path == '/chat/completions':
            assert calls and calls[-1]['status'] == 'running'
            calls[-1]['http_posts'] += 1
            assert calls[-1]['http_posts'] == 1
            persist()
        return raw_http(path, payload)

    def call(prompt):
        return audit.audited_request(prompt, current, calls, protocol, raw_chat, persist, public)

    start = time.perf_counter()
    with patch.object(api, '_request', side_effect=observed_http):
        for qid in QIDS:
            folder = OUT/'cases'/qid
            folder.mkdir(parents=True, exist_ok=True)
            if (folder/'result.json').exists():
                continue
            # 唯一输入是原问题、目录、当前库原文；旧答案/Gold/评分点不进入Agent。
            cases, hashes = agent.load_replay_cases(ROOT, OLD/'cases'/qid, ['rag'])
            cases = {qid:cases['rag']}
            current.update(qid=qid, stage='decision')
            result = {'id':qid, 'query':cases[qid]['query'], 'status':'running'}
            with (folder/'execution.log').open('a') as log, \
                    contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                loop = agent.run_diagnostics(cases, folder/'loop', hashes, call=call,
                                             resources=resources, max_actions=3)
                result.update(decision_summary=loop, status='planning_or_assessment_failed')
                if loop['completed_cases'] == 1:
                    current['stage'] = 'answer'
                    answer = agent.run_answer(ROOT, folder/'loop'/f'{qid}.json', folder/'answer', call=call)
                    result.update(answer_status=answer['answer_status'], status=answer['status'])
            save(folder/'result.json', result)
            print(qid, result['status'], flush=True)
    save(OUT/'execution_summary.json', {'elapsed_seconds':time.perf_counter()-start,
         'actual_attempts':len(calls), 'actual_http_posts':sum(c['http_posts'] for c in calls),
         'failed_attempts':sum(c['status']!='completed' for c in calls),
         'reported_usage':{key:sum(c.get('response',{}).get('usage',{}).get(key,0) for c in calls)
                           for key in ('prompt_tokens','completion_tokens','total_tokens')},
         'missing_usage':[c['number'] for c in calls if not c.get('response',{}).get('usage')],
         'automatic_retries':0,
         'cases':{qid:json.loads((OUT/'cases'/qid/'result.json').read_text())['status'] for qid in QIDS}})
    print(json.dumps(json.loads((OUT/'execution_summary.json').read_text()), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
