# 用户在HTTP 503后明确要求再跑一次；只重发已保存的反馈输入，最多1次chat。
# 原失败记录保持原样，新响应写入独立文件；不重跑规划、搜索或加载模型权重。
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def main():
    if (OUTPUT / 'feedback_retry_protocol.json').exists():
        raise RuntimeError('本次人工授权的重试已经尝试；请查看保存结果。')
    import agent
    from src.knowledge_base import load_knowledge_base
    previous = json.loads((OUTPUT / 'saved_feedback_result.json').read_text(encoding='utf-8'))
    old_calls = json.loads((OUTPUT / 'saved_feedback_calls.json').read_text(encoding='utf-8'))
    assert previous['actions_executed'] == 1 and previous['execution']['status'] == 'executed'
    assert previous['status'] == 'failed' and 'HTTP 503' in previous['error']
    cases, hashes = agent.load_replay_cases(ROOT, ROOT / 'evaluation/results/holdout_v1_20261020', ['h10'])
    case = cases['h10']
    _, chunks, metadata = load_knowledge_base(ROOT / 'data/processed', case['kb_version'])
    evidence, added_ids = agent.merge_evidence(case['evidence'], {'chunks': chunks, 'knowledge_base': metadata},
                                              previous['execution']['tool_result'])
    assert evidence == previous['evidence_after'] and added_ids == previous['added_ids']
    public = {key: agent.api.load_settings().get(key) for key in ('base_url', 'model', 'chat_options')}
    protocol = json.loads((OUTPUT / 'saved_feedback_protocol.json').read_text(encoding='utf-8'))
    assert public == protocol['api_public_settings']
    tracked = {str(path): agent.digest(path) for path in (
        Path(__file__).resolve(), ROOT / 'agent.py', ROOT / 'src/api_llm.py',
        OUTPUT / 'saved_feedback_result.json', OUTPUT / 'saved_feedback_calls.json')}
    agent.save_json(OUTPUT / 'feedback_retry_protocol.json', {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(), 'sample_type': 'human_authorized_feedback_retry',
        'authorization': '用户明确要求现在继续，并将失败的反馈再跑一次。',
        'max_new_chat_requests': 1, 'max_tool_actions': 0, 'automatic_retries': 0,
        'same_saved_prompt': True, 'final_answer_generation': False,
        'input_hashes': hashes, 'tracked_sha256': tracked, 'api_public_settings': public,
    })
    shutil.copyfile(Path(__file__), OUTPUT / 'source_snapshot' / Path(__file__).relative_to(ROOT))
    wire, calls = [], []
    request = agent.api._request
    def audited_request(path, payload=None):
        if path != '/chat/completions' or payload is None or wire:
            raise RuntimeError('本次人工授权最多1次chat请求。')
        entry = {'number': 4, 'status': 'attempted', 'started_at_utc': datetime.now(timezone.utc).isoformat()}
        wire.append(entry)
        agent.save_json(OUTPUT / 'feedback_retry_http.json', wire)
        try:
            result = request(path, payload)
            entry.update(status='returned', finish_reason=result['choices'][0].get('finish_reason'),
                         usage=result.get('usage'), reported_model=result.get('model'))
            return result
        except Exception as exc:
            entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            agent.save_json(OUTPUT / 'feedback_retry_http.json', wire)
    agent.api._request = audited_request
    def audited_call(prompt):
        assert prompt == old_calls[0]['prompt'], '反馈输入变化；拒绝发送。'
        if calls:
            raise RuntimeError('本次只允许一个反馈检查。')
        entry = {'phase': 'reassess', 'prompt': prompt, 'status': 'running'}
        calls.append(entry)
        agent.save_json(OUTPUT / 'feedback_retry_calls.json', calls)
        try:
            entry['response'] = agent.api.chat_completion(prompt)
            entry['status'] = 'completed'
            return entry['response']
        except Exception as exc:
            entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            agent.save_json(OUTPUT / 'feedback_retry_calls.json', calls)
    record = {'status': 'running', 'source_execution': 'saved_feedback_result.json',
              'initial_plan': previous['initial_plan'], 'initial_assessment': previous['initial_assessment'],
              'actions_executed_this_retry': 0, 'previous_actions_executed': 1,
              'evidence_after': evidence, 'added_ids': added_ids, 'automatic_action_loop': False}
    try:
        record['feedback_assessment'] = agent.assess_evidence(
            case['query'], previous['initial_plan'], evidence, case['inventory'], audited_call)
        record['status'] = 'completed'
    except Exception as exc:
        record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    finally:
        record['new_chat_requests'] = len(wire)
        record['tracked_inputs_unchanged'] = all(agent.digest(Path(name)) == value for name, value in tracked.items())
        agent.save_json(OUTPUT / 'feedback_retry_result.json', record)
    print(json.dumps({key: record.get(key) for key in ('status', 'error', 'feedback_assessment', 'new_chat_requests')},
                     ensure_ascii=False, indent=2), flush=True)
    if record['status'] != 'completed':
        raise SystemExit('本次反馈未通过，保留记录，不自动重试。')


if __name__ == '__main__':
    main()
