# 在本轮相同输入上续查“重复行动后改选”：精确复用已发生的3个响应和搜索结果。
# 不修改旧输出；新提示才请求模型，两个阶段合计最多6次实际chat。
import ast
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).resolve().parent
PRIOR = OUTPUT.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
for name, value in {'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                    'VECLIB_MAXIMUM_THREADS': '1', 'TOKENIZERS_PARALLELISM': 'false',
                    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}.items():
    os.environ[name] = value


def main():
    if (OUTPUT / 'protocol_before_run.json').exists():
        raise RuntimeError('本次续查已有协议；请查看保存结果，不重复运行。')
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import agent
    from src import agent_tools as tools
    prior_calls = json.loads((PRIOR / 'run/actual_chat_calls.json').read_text())
    prior_wire = json.loads((PRIOR / 'actual_http_calls.json').read_text())
    prior_record = json.loads((PRIOR / 'run/h10.json').read_text())
    assert len(prior_calls) == len(prior_wire) == 3 and prior_record['halt_reason'] == 'repeated_action'
    prior_protocol = json.loads((PRIOR / 'protocol_before_run.json').read_text())
    old_tree = ast.parse((PRIOR / 'source_snapshot/agent.py').read_text())
    new_tree = ast.parse((ROOT / 'agent.py').read_text())
    def node(tree, name):
        return ast.dump(next(item for item in tree.body if getattr(item, 'name', None) == name), include_attributes=False)
    for name in ('plan_requirements', 'assess_evidence', 'validate_plan', 'validate_assessment', 'execute_action', 'merge_evidence'):
        assert node(old_tree, name) == node(new_tree, name), '只允许复用未改变的提示/校验/工具边界。'
    cases, hashes = agent.load_replay_cases(ROOT, ROOT / 'evaluation/results/holdout_v1_20261020', ['h10'])
    public = {name: agent.api.load_settings().get(name) for name in ('base_url', 'model', 'chat_options')}
    assert public == prior_protocol['api_public_settings']
    cache = {entry['prompt']: entry for entry in prior_calls}
    saved_action = prior_record['steps'][0]['action']
    saved_result = prior_record['steps'][0]['execution']['tool_result']
    for path in (PRIOR / 'run/actual_chat_calls.json', PRIOR / 'run/h10.json', PRIOR / 'source_snapshot/agent.py'):
        hashes[str(path)] = agent.digest(path)
    tracked = [Path(__file__).resolve(), ROOT / 'agent.py', ROOT / 'tests/test_agent_loop.py',
               *sorted((ROOT / 'src').glob('*.py'))]
    source_hashes = {str(path.relative_to(ROOT)): agent.digest(path) for path in tracked}
    agent.save_json(OUTPUT / 'protocol_before_run.json', {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(), 'sample_type': 'exact-prefix replay then new policy feedback',
        'prior_actual_chat_requests': 3, 'max_new_chat_requests': 3, 'combined_actual_chat_cap': 6,
        'max_actions': 3, 'max_validation_or_action_repairs': 1,
        'reused_prefix': '3 identical-prompt completed responses and verified search output; contents unchanged',
        'automatic_network_retries': 0, 'final_answer_generation': False,
        'input_hashes': hashes, 'source_hashes': source_hashes, 'api_public_settings': public,
    })
    for path in tracked:
        target = OUTPUT / 'source_snapshot' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)

    wire, reused = [], []
    counts = {'cached_search': 0, 'new_search': 0, 'new_read_neighbors': 0}
    request = agent.api._request
    def audited_request(path, payload=None):
        if path != '/chat/completions' or payload is None or len(prior_wire) + len(wire) >= 6:
            raise RuntimeError('两个阶段合计最多6次chat请求。')
        entry = {'number': len(prior_wire) + len(wire) + 1, 'status': 'attempted'}
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
    search, read = tools.search_local_kb, tools.read_neighbors
    def cached_search(query, resources, source=None):
        if not counts['cached_search'] and query == saved_action['query'] and source == saved_action['source']:
            assert resources['knowledge_base'] == saved_result['knowledge_base']
            agent.merge_evidence(cases['h10']['evidence'], resources, saved_result)
            counts['cached_search'] += 1
            return deepcopy(saved_result)
        counts['new_search'] += 1
        return search(query, resources, source=source)
    def audited_read(*args, **kwargs):
        counts['new_read_neighbors'] += 1
        return read(*args, **kwargs)
    tools.search_local_kb, tools.read_neighbors = cached_search, audited_read
    def replay_or_call(prompt):
        if prompt in cache:
            entry = cache[prompt]
            reused.append({'prior_number': entry['number'], 'prior_phase': entry['phase']})
            agent.save_json(OUTPUT / 'prefix_reuse.json', reused)
            return {**deepcopy(entry['response']), 'replayed_from': f'../run/actual_chat_calls.json#{entry["number"]}'}
        if len(reused) != 3 or counts['cached_search'] != 1:
            raise RuntimeError('初始提示或原搜索输出发生变化，拒绝复用或追加请求。')
        return agent.api.chat_completion(prompt)
    summary = agent.run_diagnostics(cases, OUTPUT / 'run', hashes, replay_or_call, max_actions=3)
    assert [item['prior_number'] for item in reused] == [1, 2, 3]
    agent.save_json(OUTPUT / 'run_summary.json', {
        'summary': summary, 'new_http_requests': len(wire), 'combined_http_requests': 3 + len(wire),
        'reused_model_responses': len(reused), 'tool_counts': counts,
        'tracked_inputs_unchanged': all(agent.digest(ROOT / name) == value for name, value in source_hashes.items())
            and all(agent.digest(Path(name)) == value for name, value in hashes.items()),
    })
    print(json.dumps({'summary': summary, 'new_http_requests': len(wire), 'tool_counts': counts}, ensure_ascii=False, indent=2), flush=True)
    if summary['completed_cases'] != 1:
        raise SystemExit('续查失败；保留结果，不自动重试。')


if __name__ == '__main__':
    main()
