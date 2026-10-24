# 复用P2.1已验收的h10行动，隔离检查新接的执行与反馈；最多再用1次chat。
# 首次新诊断的2次调用及失败保留；两部分合计不超过用户授权的3次。
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
    if (OUTPUT / 'saved_feedback_protocol.json').exists():
        raise RuntimeError('已有本次反馈协议；请查看记录，不重复执行。')
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import agent
    from src import agent_tools as tools
    prior_http = json.loads((OUTPUT / 'actual_http_calls.json').read_text(encoding='utf-8'))
    assert len(prior_http) == 2
    fresh_record = json.loads((OUTPUT / 'run/h10.json').read_text(encoding='utf-8'))
    assert fresh_record['status'] == 'failed' and fresh_record['actions_executed'] == 0
    cases, hashes = agent.load_replay_cases(ROOT, ROOT / 'evaluation/results/holdout_v1_20261020', ['h10'])
    case = cases['h10']
    saved_path = ROOT / 'evaluation/results/agent_p21_closeout_20261020/run/h10.json'
    saved = json.loads(saved_path.read_text(encoding='utf-8'))
    assert saved['query'] == case['query'] and saved['kb_version'] == case['kb_version']
    agent.validate_plan(saved['plan'], case['query'])
    agent.validate_assessment(saved['assessment'], saved['plan']['requirements'], case['evidence'], case['inventory'])
    settings = agent.api.load_settings()
    public = {key: settings.get(key) for key in ('base_url', 'model', 'chat_options')}
    frozen = json.loads((OUTPUT / 'protocol_before_run.json').read_text(encoding='utf-8'))
    assert public == frozen['api_public_settings']
    assert all(agent.digest(ROOT / name) == value for name, value in frozen['source_hashes'].items())
    tracked = {**hashes, str(saved_path): agent.digest(saved_path), str(Path(__file__)): agent.digest(Path(__file__))}
    agent.save_json(OUTPUT / 'saved_feedback_protocol.json', {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(), 'sample_type': 'accepted_proposal_replay',
        'source': str(saved_path.relative_to(ROOT)), 'action': saved['assessment']['next_action'],
        'initial_diagnostic': 'fresh run rejected; preserved without retry',
        'max_additional_chats': 1, 'combined_chat_cap': 3, 'max_actions': 1, 'automatic_retries': 0,
        'neighbor_window': 1, 'final_answer_generation': False, 'input_hashes': tracked,
        'api_public_settings': public,
    })
    shutil.copyfile(Path(__file__), OUTPUT / 'source_snapshot' / Path(__file__).relative_to(ROOT))
    wire, calls = [], []
    request = agent.api._request
    def audited_request(path, payload=None):
        if path != '/chat/completions' or payload is None or len(prior_http) + len(wire) >= 3:
            raise RuntimeError('两部分合计最多3次chat，不自动重试。')
        entry = {'number': 3, 'status': 'attempted', 'started_at_utc': datetime.now(timezone.utc).isoformat()}
        wire.append(entry)
        agent.save_json(OUTPUT / 'saved_feedback_http.json', wire)
        try:
            result = request(path, payload)
            entry.update(status='returned', finish_reason=result['choices'][0].get('finish_reason'),
                         usage=result.get('usage'), reported_model=result.get('model'))
            return result
        finally:
            agent.save_json(OUTPUT / 'saved_feedback_http.json', wire)
    agent.api._request = audited_request
    def audited_call(prompt):
        if calls:
            raise RuntimeError('只允许一次反馈检查。')
        entry = {'phase': 'reassess', 'prompt': prompt, 'status': 'running'}
        calls.append(entry)
        agent.save_json(OUTPUT / 'saved_feedback_calls.json', calls)
        try:
            entry['response'] = agent.api.chat_completion(prompt)
            entry['status'] = 'completed'
            return entry['response']
        except Exception as exc:
            entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            agent.save_json(OUTPUT / 'saved_feedback_calls.json', calls)

    record = {'status': 'running', 'initial_plan': saved['plan'], 'initial_assessment': saved['assessment'],
              'initial_decision_reused': True, 'actions_executed': 0, 'automatic_action_loop': False}
    path = OUTPUT / 'saved_feedback_result.json'
    agent.save_json(path, record)
    try:
        resources = tools.load_search_resources()
        agent.merge_evidence(case['evidence'], resources)
        record['execution'] = agent.execute_action(saved['assessment']['next_action'], resources)
        record['actions_executed'] = 1
        record['evidence_after'], record['added_ids'] = agent.merge_evidence(
            case['evidence'], resources, record['execution']['tool_result'])
        agent.save_json(path, record)
        record['feedback_assessment'] = agent.assess_evidence(
            case['query'], saved['plan'], record['evidence_after'], case['inventory'], audited_call)
        record['status'] = 'completed'
    except Exception as exc:
        record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    finally:
        record['new_chat_requests'] = len(wire)
        record['combined_chat_requests'] = len(prior_http) + len(wire)
        record['tracked_inputs_unchanged'] = all(agent.digest(Path(name)) == value for name, value in tracked.items())
        agent.save_json(path, record)
    print(json.dumps({key: record.get(key) for key in ('status', 'error', 'actions_executed', 'added_ids',
                     'new_chat_requests', 'combined_chat_requests')}, ensure_ascii=False, indent=2), flush=True)
    if record['status'] != 'completed':
        raise SystemExit('反馈结果未通过验收，保留原文，不自动重试。')


if __name__ == '__main__':
    main()
