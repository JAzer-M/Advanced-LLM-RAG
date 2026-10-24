"""One additional chat after a documented budget revision: isolated h10 evidence check."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

PROJECT = Path('/Users/j/Desktop/Advanced-LLM-RAG')
OUTPUT = Path(__file__).resolve().parent
CODE = OUTPUT.parent / 'checkout'
sys.path.insert(0, str(CODE if CODE.is_dir() else PROJECT))

import agent


def main():
    agent.api.SETTINGS_PATH = PROJECT / 'api.local.json'
    old_calls = json.loads((OUTPUT / 'run/actual_chat_calls.json').read_text())
    old_wire = json.loads((OUTPUT / 'actual_http_calls.json').read_text())
    if len(old_calls) != 5 or len(old_wire) != 5:
        raise ValueError('Expected five recorded initial attempts.')
    prior_wire = json.loads((OUTPUT / 'recheck/actual_http_call.json').read_text())
    if prior_wire['overall_number'] != 6 or prior_wire['status'] != 'returned':
        raise ValueError('Expected the sixth request to be preserved before the revised seven-chat cap.')
    cases, hashes = agent.load_replay_cases(
        PROJECT, PROJECT / 'evaluation/results/holdout_v1_20261020', ['h01', 'h10', 'h11'])
    plans = {}
    for call in old_calls:
        if call['phase'] == 'plan':
            proposed = json.loads(call['response']['answer'])
            # Only the three extraction fields are carried over. The earlier
            # free paraphrase, old assessment and old answers are not model input.
            extracted = {'requirements': [{k: r[k] for k in ('id', 'subject', 'question_quote')}
                                          for r in proposed['requirements']]}
            plans[call['question_id']] = agent.bind_requirements(extracted, cases[call['question_id']]['query'])
    folder = OUTPUT / 'isolated_recheck'
    folder.mkdir(exist_ok=True)
    settings = agent.api.load_settings()
    public = {k: settings.get(k) for k in ('base_url', 'model', 'chat_options')}
    frozen = {'agent_sha256': agent.digest(Path(agent.__file__)),
              'api_client_sha256': agent.digest(Path(agent.api.__file__)),
              'input_hashes': hashes, 'public_options': public,
              'cached_planning_calls_sha256': agent.digest(OUTPUT / 'run/actual_chat_calls.json'),
              'bound_plans': plans, 'max_new_chat_attempts': 1, 'max_total_chat_attempts': 7,
              'automatic_retries': 0, 'fresh_planning_calls': 0,
              'scope': 'h10 assessment isolated by bound request; cached planning anchors; original full comparison excluded',
              'manual_expectation': 'RAG missing, Self-RAG supported; target RAG local search/neighbors, no transferred PopQA scope.'}
    freeze = folder / 'protocol_before_run.json'
    if freeze.exists():
        previous = json.loads(freeze.read_text())
        if {k: v for k, v in previous.items() if k != 'frozen_at_utc'} != frozen:
            raise ValueError('Recheck code/data/options changed; no reuse or retry.')
    else:
        agent.save_json(freeze, {'frozen_at_utc': datetime.now(timezone.utc).isoformat(), **frozen})
    agent.save_json(folder / 'bound_plans.json', plans)
    record_path = folder / 'h10.json'
    if record_path.exists():
        print('Existing attempted recheck preserved; no automatic retry or new request.')
        return

    wire_path = folder / 'actual_http_call.json'
    if wire_path.exists():
        raise RuntimeError('Final chat already attempted; no automatic retry after interruption.')
    request = agent.api._request

    def audited_request(path, payload=None):
        if path != '/chat/completions' or payload is None or wire_path.exists():
            raise RuntimeError('Only one final audited chat is allowed.')
        wire = {'overall_number': 7, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'prompt_sha256': hashlib.sha256(payload['messages'][0]['content'].encode()).hexdigest(),
                'public_options': {k: v for k, v in payload.items() if k != 'messages'}, 'status': 'attempted'}
        agent.save_json(wire_path, wire)
        try:
            result = request(path, payload)
            wire.update(status='returned', finish_reason=result['choices'][0].get('finish_reason'),
                        usage=result.get('usage'), reported_model=result.get('model'))
            return result
        finally:
            agent.save_json(wire_path, wire)

    def audited_call(prompt):
        call_record = {'number': 7, 'phase': 'h10_assess_isolated_requirements', 'prompt': prompt,
                       'started_at_utc': datetime.now(timezone.utc).isoformat()}
        agent.save_json(folder / 'actual_chat_call.json', call_record)
        started = time.perf_counter()
        try:
            response = agent.api.chat_completion(prompt)
            call_record.update(response=response, status='completed')
            return response
        except Exception as exc:
            call_record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            if isinstance(exc, agent.api.IncompleteResponseError):
                call_record['response'] = exc.response
            raise
        finally:
            call_record['elapsed_seconds'] = round(time.perf_counter() - started, 3)
            agent.save_json(folder / 'actual_chat_call.json', call_record)

    agent.api._request = audited_request
    case = cases['h10']
    record = {'id': 'h10', 'query': case['query'], 'plan': plans['h10'], 'actions_executed': 0,
              'fresh_retrieval': False, 'fresh_final_answer': False}
    try:
        record['assessment'] = agent.assess_evidence(case['query'], plans['h10'], case['evidence'], case['inventory'], audited_call)
        record['status'] = 'completed'
    except Exception as exc:
        record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    agent.save_json(record_path, record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if record['status'] != 'completed':
        raise SystemExit('Isolated recheck failed; revised seven-chat total exhausted, preserve the evidence.')


if __name__ == '__main__':
    main()
