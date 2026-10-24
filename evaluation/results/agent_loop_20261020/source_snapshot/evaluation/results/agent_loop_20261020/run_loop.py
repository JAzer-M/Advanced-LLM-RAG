# P2.3 有预算循环的真实开发检查：h10重新规划，最多6次chat、3个工具行动。
# 运行前冻结源码/输入/选项；协议已存在则读记录，不自动重复实验。
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
for name, value in {'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                    'VECLIB_MAXIMUM_THREADS': '1', 'TOKENIZERS_PARALLELISM': 'false',
                    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}.items():
    os.environ[name] = value


def main():
    if (OUTPUT / 'protocol_before_run.json').exists():
        raise RuntimeError('本次检查已有协议；请查看保存记录，不重复运行。')
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import agent
    from src import agent_tools as tools
    cases, hashes = agent.load_replay_cases(ROOT, ROOT / 'evaluation/results/holdout_v1_20261020', ['h10'])
    settings = agent.api.load_settings()
    public = {name: settings.get(name) for name in ('base_url', 'model', 'chat_options')}
    assert (os.environ.get('RAG_API_KEY') or settings.get('api_key', '')).strip(), '本地凭证未配置。'
    tracked = [Path(__file__).resolve(), ROOT / 'agent.py', ROOT / 'tests/test_agent_loop.py',
               ROOT / 'data/processed/active_kb.json', *sorted((ROOT / 'src').glob('*.py'))]
    source_hashes = {str(path.relative_to(ROOT)): agent.digest(path) for path in tracked}
    agent.save_json(OUTPUT / 'protocol_before_run.json', {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(), 'case_ids': ['h10'],
        'sample_type': 'known_development_case', 'fresh_planning_and_initial_assessment': True,
        'max_chat_requests': 6, 'max_tool_actions': 3, 'max_validation_repairs': 1,
        'neighbor_window': agent.LOOP_NEIGHBOR_WINDOW,
        'max_feedback_passages': agent.MAX_FEEDBACK_PASSAGES, 'max_feedback_chars': agent.MAX_FEEDBACK_CHARS,
        'automatic_network_retries': 0, 'final_answer_generation': False,
        'input_hashes': hashes, 'source_hashes': source_hashes, 'api_public_settings': public,
        'baseline': 'agent_feedback_20261020: search added text; latest model assessment rejected',
        'runtime_inputs': 'question, bound excerpts, original passages, paper inventory, actual tool history only',
        'manual_review': 'verify requested facts and conditions against cited originals; do not infer quality from JSON acceptance',
    })
    for path in tracked:
        if path.suffix == '.py':
            target = OUTPUT / 'source_snapshot' / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)

    wire = []
    request = agent.api._request
    def audited_request(path, payload=None):
        if path != '/chat/completions' or payload is None or len(wire) >= 6:
            raise RuntimeError('本轮最多6次chat请求，禁止其他API操作和自动网络重试。')
        entry = {'number': len(wire) + 1, 'started_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'attempted'}
        wire.append(entry)
        agent.save_json(OUTPUT / 'actual_http_calls.json', wire)
        try:
            result = request(path, payload)
            entry.update(status='returned', finish_reason=result['choices'][0].get('finish_reason'),
                         usage=result.get('usage'), reported_model=result.get('model'))
            return result
        except Exception as exc:
            entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            agent.save_json(OUTPUT / 'actual_http_calls.json', wire)
    agent.api._request = audited_request

    counts = {'resource_loads': 0, 'search': 0, 'read_neighbors': 0, 'embedding_encode': 0, 'reranker_predict': 0}
    load = tools.load_search_resources
    def audited_load():
        counts['resource_loads'] += 1
        resources = load()
        encode, predict = resources['embedding_model'].encode, resources['reranker_model'].predict
        def audited_encode(*args, **kwargs):
            counts['embedding_encode'] += 1
            return encode(*args, **kwargs)
        def audited_predict(*args, **kwargs):
            counts['reranker_predict'] += 1
            return predict(*args, **kwargs)
        resources['embedding_model'].encode = audited_encode
        resources['reranker_model'].predict = audited_predict
        return resources
    tools.load_search_resources = audited_load
    search, read = tools.search_local_kb, tools.read_neighbors
    def audited_search(*args, **kwargs):
        counts['search'] += 1
        return search(*args, **kwargs)
    def audited_read(*args, **kwargs):
        counts['read_neighbors'] += 1
        return read(*args, **kwargs)
    tools.search_local_kb, tools.read_neighbors = audited_search, audited_read
    try:
        summary = agent.run_diagnostics(cases, OUTPUT / 'run', hashes, max_actions=3)
        agent.save_json(OUTPUT / 'run_summary.json', {
            'summary': summary, 'tool_counts': counts, 'http_attempts': len(wire),
            'tracked_inputs_unchanged': all(agent.digest(ROOT / name) == value for name, value in source_hashes.items())
                and all(agent.digest(Path(name)) == value for name, value in hashes.items()),
        })
        print(json.dumps({'summary': summary, 'tool_counts': counts}, ensure_ascii=False, indent=2), flush=True)
        if summary['completed_cases'] != 1:
            raise SystemExit('本次链路失败，保留原文与错误，不自动重试。')
    finally:
        agent.save_json(OUTPUT / 'tool_counts.json', counts)


if __name__ == '__main__':
    main()
