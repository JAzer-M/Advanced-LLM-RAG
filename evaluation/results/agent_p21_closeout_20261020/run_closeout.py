"""P2.1 acceptance: three fresh plans/checks, hard cap six chats, no tools."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROJECT = Path('/Users/j/Desktop/Advanced-LLM-RAG')
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

import agent


def main():
    cases, hashes = agent.load_replay_cases(
        PROJECT, PROJECT / 'evaluation/results/holdout_v1_20261020', ['h01', 'h10', 'h11'])
    settings = agent.api.load_settings()
    public = {k: settings.get(k) for k in ('base_url', 'model', 'chat_options')}
    frozen = {
        'stage': 'P2.1 final three-case live acceptance; do not start P2.2',
        'case_ids': list(cases), 'max_new_chats': 6, 'automatic_retries': 0,
        'fresh_planning': True, 'fresh_assessment': True, 'reuse_old_model_outputs': False,
        'fresh_retrieval': False, 'tool_execution': False, 'final_answer_generation': False,
        'agent_sha256': agent.digest(Path(agent.__file__)),
        'api_client_sha256': agent.digest(Path(agent.api.__file__)),
        'input_hashes': hashes, 'public_api_options': public,
        'manual_acceptance': {
            'h01': 'Cover smoothing value and reported metric effects, supplied evidence supports them, answer.',
            'h10': ('Keep RAG criterion separate from Self-RAG PopQA/TriviaQA scope. '
                    'Training loss is not support for evaluation criterion. '
                    'RAG criterion missing, Self-RAG criterion supported; propose a scoped local lookup.'),
            'h11': 'Mamba primary paper absent from full inventory; missing, stop without values.'},
        'scope': 'Known development cases; no independent accuracy/generalization claim.'}
    path = OUTPUT / 'protocol_before_run.json'
    if path.exists():
        old = json.loads(path.read_text())
        if {k: v for k, v in old.items() if k != 'frozen_at_utc'} != frozen:
            raise ValueError('Frozen code/data/options changed; no new request.')
    else:
        agent.save_json(path, {'frozen_at_utc': datetime.now(timezone.utc).isoformat(), **frozen})
    wire_path = OUTPUT / 'actual_http_calls.json'
    wire = json.loads(wire_path.read_text()) if wire_path.exists() else []
    request = agent.api._request

    def audited_request(path, payload=None):
        if path != '/chat/completions' or payload is None or len(wire) >= 6:
            raise RuntimeError('Only six audited chat requests are authorized for this closeout.')
        entry = {'number': len(wire) + 1, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                 'prompt_sha256': hashlib.sha256(payload['messages'][0]['content'].encode()).hexdigest(),
                 'public_options': {k: v for k, v in payload.items() if k != 'messages'},
                 'status': 'attempted'}
        wire.append(entry)
        agent.save_json(wire_path, wire)
        try:
            result = request(path, payload)
            entry.update(status='returned', finish_reason=result['choices'][0].get('finish_reason'),
                         usage=result.get('usage'), reported_model=result.get('model'))
            return result
        except Exception as exc:
            entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            agent.save_json(wire_path, wire)

    agent.api._request = audited_request
    summary = agent.run_diagnostics(cases, OUTPUT / 'run', hashes)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary['completed_cases'] != len(cases):
        raise SystemExit('Acceptance outputs failed; retain records, no automatic retries.')


if __name__ == '__main__':
    main()
