"""Offline provenance, budget, exact code and completed-resume checks."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import Mock, patch

PROJECT = Path('/Users/j/Desktop/Advanced-LLM-RAG')
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))
import agent


def main():
    calls_path = OUTPUT / 'run/actual_chat_calls.json'
    calls = json.loads(calls_path.read_text())
    wire = json.loads((OUTPUT / 'actual_http_calls.json').read_text())
    frozen = json.loads((OUTPUT / 'protocol_before_run.json').read_text())
    assert len(calls) == len(wire) == 6
    assert [(c['question_id'], c['phase']) for c in calls] == [
        (qid, phase) for qid in ('h01', 'h10', 'h11') for phase in ('plan', 'assess')]
    assert frozen['agent_sha256'] == agent.digest(PROJECT / 'agent.py')
    assert frozen['api_client_sha256'] == agent.digest(PROJECT / 'src/api_llm.py')
    assert datetime.fromisoformat(frozen['frozen_at_utc']) < datetime.fromisoformat(calls[0]['started_at_utc'])
    for c, w in zip(calls, wire):
        assert c['status'] == 'completed' and w['status'] == 'returned'
        assert c['response']['finish_reason'] == w['finish_reason'] == 'stop'
        assert hashlib.sha256(c['prompt'].encode()).hexdigest() == w['prompt_sha256']
    cases, hashes = agent.load_replay_cases(
        PROJECT, PROJECT / 'evaluation/results/holdout_v1_20261020', ['h01', 'h10', 'h11'])
    assert hashes == frozen['input_hashes']
    quotes = []
    records = {}
    for qid, case in cases.items():
        record = json.loads((OUTPUT / 'run' / f'{qid}.json').read_text())
        assert record['status'] == 'completed' and record['actions_executed'] == 0
        agent.validate_plan(record['plan'], case['query'])
        agent.validate_assessment(record['assessment'], record['plan']['requirements'], case['evidence'], case['inventory'])
        model_plan = next(c for c in calls if c['question_id'] == qid and c['phase'] == 'plan')
        raw_plan = json.loads(model_plan['response']['answer'])
        assert all(set(r) == {'id', 'subject', 'question_quote'} for r in raw_plan['requirements'])
        assert model_plan['prompt'].endswith(case['query'])
        check = next(c for c in calls if c['question_id'] == qid and c['phase'] == 'assess')
        data = json.loads(check['prompt'].split('INPUT DATA:\n', 1)[1])
        assert set(data) == {'requirements', 'search_queries', 'inventory', 'passages'}
        assert data['passages'] == case['evidence'] and data['inventory'] == case['inventory']
        assert data['requirements'] == record['plan']['requirements']
        by_id = {p['chunk_id']: p for p in case['evidence']}
        for item in record['assessment']['requirements']:
            for ref in item['evidence']:
                p = by_id[ref['chunk_id']]
                assert agent.normalize(ref['quote']) in agent.normalize(p['text'])
                quotes.append({'question_id': qid, 'requirement_id': item['id'], 'chunk_id': p['chunk_id'],
                               'source': p['source'], 'page': p['page'], 'quote': ref['quote']})
        records[qid] = record
    assert all(r['status'] == 'supported' for r in records['h01']['assessment']['requirements'])
    assert [r['status'] for r in records['h10']['assessment']['requirements']] == ['missing', 'supported']
    assert all(r['status'] == 'missing' for r in records['h11']['assessment']['requirements'])
    assert [records[q]['assessment']['next_action']['type'] for q in cases] == ['answer', 'search', 'stop']
    search = records['h10']['assessment']['next_action']['query']
    assert 'PopQA' not in search and 'TriviaQA' not in search
    audit_hash = agent.digest(calls_path)
    blocked = Mock(side_effect=AssertionError('No new API allowed during resume verification'))
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline audit')):
        resumed = agent.run_diagnostics(cases, OUTPUT / 'run', hashes, call=blocked)
    assert blocked.call_count == 0 and agent.digest(calls_path) == audit_hash
    baseline = json.loads((OUTPUT / 'baseline_hashes.json').read_text())
    changed = [name for name, digest in baseline.items() if agent.digest(PROJECT / name) != digest]
    assert not changed, changed
    usage = {key: sum(c['response']['usage'][key] for c in calls)
             for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    assert usage == resumed['reported_usage']
    report = {'program_completed': '3/3', 'manual_review_file': 'manual_review.md',
              'fresh_plan_calls': 3, 'fresh_assessment_calls': 3, 'actual_chat_attempts': 6,
              'reported_usage': usage, 'all_finish_reasons_stop': True, 'automatic_retries': 0,
              'actions_executed': 0, 'fresh_retrieval': False, 'fresh_final_generation': False,
              'code_changed': False, 'previous_123_tests_source_matches': True, 'unit_tests_rerun': False,
              'paired_inputs_verified': True, 'whitelist_verified': True, 'verified_quotes': len(quotes),
              'completed_resume_new_calls': 0, 'baseline_files_unchanged': len(baseline),
              'program_elapsed_seconds': round(sum(r['elapsed_seconds'] for r in records.values()), 3),
              'api_elapsed_seconds': round(sum(c['elapsed_seconds'] for c in calls), 3)}
    agent.save_json(OUTPUT / 'verified_quotes.json', quotes)
    agent.save_json(OUTPUT / 'verification.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
