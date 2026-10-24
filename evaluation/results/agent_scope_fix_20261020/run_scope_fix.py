"""Bounded development replay; no retrieval, tool execution or final answers."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


PROJECT = Path('/Users/j/Desktop/Advanced-LLM-RAG')
OUTPUT = Path(__file__).resolve().parent
STAGED_CODE = OUTPUT.parent / 'checkout'
CODE = STAGED_CODE if STAGED_CODE.is_dir() else PROJECT
sys.path.insert(0, str(CODE))

import agent


def main():
    agent.api.SETTINGS_PATH = PROJECT / 'api.local.json'
    cases, hashes = agent.load_replay_cases(
        PROJECT, PROJECT / 'evaluation/results/holdout_v1_20261020', ['h01', 'h10', 'h11'])
    settings = agent.api.load_settings()
    public = {k: settings.get(k) for k in ('base_url', 'model', 'chat_options')}
    frozen = {
        'max_chat_attempts': 6, 'automatic_retries': 0, 'actions_executed': 0,
        'fresh_retrieval': False, 'fresh_final_answers': False,
        'development_cases': list(cases), 'input_hashes': hashes,
        'agent_sha256': agent.digest(Path(agent.__file__)),
        'api_client_sha256': agent.digest(Path(agent.api.__file__)),
        'public_settings': public,
        'manual_expectations': {
            'h01': 'Requirements remain within the label-smoothing question; supported; answer.',
            'h10': ('Keep the RAG criterion separate from the Self-RAG PopQA/TriviaQA scope. '
                    'Training loss is not partial support for a correctness criterion. '
                    'RAG criterion missing; Self-RAG criterion supported by supplied original text. '
                    'Propose search or neighbors in the RAG paper without transferred conditions.'),
            'h11': 'Mamba paper absent from complete inventory; missing, stop, no invented values.'},
        'independence': 'Known development cases, not a new holdout or generalization test.'}
    freeze_path = OUTPUT / 'protocol_before_run.json'
    if freeze_path.exists():
        previous = json.loads(freeze_path.read_text())
        if {k: v for k, v in previous.items() if k != 'frozen_at_utc'} != frozen:
            raise ValueError('Frozen code, data or public API settings changed.')
    else:
        agent.save_json(freeze_path, {'frozen_at_utc': datetime.now(timezone.utc).isoformat(), **frozen})

    wire_path = OUTPUT / 'actual_http_calls.json'
    wire = json.loads(wire_path.read_text()) if wire_path.exists() else []
    request = agent.api._request

    def audited_request(path, payload=None):
        if path != '/chat/completions' or payload is None:
            raise ValueError('This experiment only allows audited chat requests.')
        if len(wire) >= frozen['max_chat_attempts']:
            raise RuntimeError('Independent six-chat request budget exhausted.')
        entry = {'number': len(wire) + 1, 'path': path,
                 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                 'prompt_sha256': hashlib.sha256(payload['messages'][0]['content'].encode()).hexdigest(),
                 'public_options': {k: v for k, v in payload.items() if k != 'messages'},
                 'status': 'attempted'}
        wire.append(entry)
        agent.save_json(wire_path, wire)
        try:
            response = request(path, payload)
            entry.update(status='returned', reported_model=response.get('model'),
                         finish_reason=response['choices'][0].get('finish_reason'), usage=response.get('usage'))
            return response
        except Exception as exc:
            entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            agent.save_json(wire_path, wire)

    agent.api._request = audited_request
    summary = agent.run_diagnostics(cases, OUTPUT / 'run', hashes)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary['completed_cases'] != len(cases):
        raise SystemExit('Some diagnostic outputs failed; inspect saved raw responses, no automatic retry.')


if __name__ == '__main__':
    main()
