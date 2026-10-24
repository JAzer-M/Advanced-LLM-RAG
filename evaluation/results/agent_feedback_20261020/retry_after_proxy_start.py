# 用户确认反代重新启动后的一次反馈检查。输入与上次完全相同，新增chat上限1次。
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import agent
from src.knowledge_base import load_knowledge_base

protocol_path = OUTPUT / 'proxy_restarted_protocol.json'
if protocol_path.exists():
    raise SystemExit('本次人工续接已尝试运行；请查看保存结果，不重复请求。')
previous = json.loads((OUTPUT / 'saved_feedback_result.json').read_text(encoding='utf-8'))
old_calls = json.loads((OUTPUT / 'saved_feedback_calls.json').read_text(encoding='utf-8'))
cases, hashes = agent.load_replay_cases(ROOT, ROOT / 'evaluation/results/holdout_v1_20261020', ['h10'])
case = cases['h10']
_, chunks, metadata = load_knowledge_base(ROOT / 'data/processed', case['kb_version'])
evidence, added_ids = agent.merge_evidence(case['evidence'], {'chunks': chunks, 'knowledge_base': metadata},
                                          previous['execution']['tool_result'])
assert evidence == previous['evidence_after'] and added_ids == previous['added_ids']
public = {key: agent.api.load_settings().get(key) for key in ('base_url', 'model', 'chat_options')}
assert public == json.loads((OUTPUT / 'saved_feedback_protocol.json').read_text())['api_public_settings']
agent.save_json(protocol_path, {
    'frozen_at_utc': datetime.now(timezone.utc).isoformat(), 'sample_type': 'human_resume_after_proxy_started',
    'authorization': '用户要求再跑一次，并随后明确确认本机反代已启动，请再检查。',
    'max_new_chat_requests': 1, 'max_tool_actions': 0, 'automatic_retries': 0,
    'same_saved_prompt': True, 'final_answer_generation': False,
    'api_public_settings': public, 'input_hashes': hashes,
    'agent_sha256': agent.digest(Path(agent.__file__)), 'driver_sha256': agent.digest(Path(__file__)),
})
calls = []
def audited_call(prompt):
    assert prompt == old_calls[0]['prompt'], '反馈输入变化，拒绝发送。'
    if calls:
        raise RuntimeError('本次只允许1次模型请求。')
    entry = {'phase': 'reassess', 'prompt': prompt, 'status': 'running'}
    calls.append(entry)
    agent.save_json(OUTPUT / 'proxy_restarted_calls.json', calls)
    try:
        entry['response'] = agent.api.chat_completion(prompt)
        entry['status'] = 'completed'
        return entry['response']
    except Exception as exc:
        entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        if isinstance(exc, agent.api.IncompleteResponseError):
            entry['response'] = exc.response
        raise
    finally:
        agent.save_json(OUTPUT / 'proxy_restarted_calls.json', calls)
record = {'status': 'running', 'initial_plan': previous['initial_plan'],
          'initial_assessment': previous['initial_assessment'], 'added_ids': added_ids,
          'evidence_after': evidence, 'new_tool_actions': 0, 'automatic_action_loop': False}
try:
    record['feedback_assessment'] = agent.assess_evidence(
        case['query'], previous['initial_plan'], evidence, case['inventory'], audited_call)
    record['status'] = 'completed'
except Exception as exc:
    record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
finally:
    record['new_chat_requests'] = len(calls)
    agent.save_json(OUTPUT / 'proxy_restarted_result.json', record)
print(json.dumps({key: record.get(key) for key in ('status', 'error', 'feedback_assessment', 'new_chat_requests')},
                 ensure_ascii=False, indent=2), flush=True)
if record['status'] != 'completed':
    raise SystemExit('本次结果未通过，保留原文，不自动重试。')
