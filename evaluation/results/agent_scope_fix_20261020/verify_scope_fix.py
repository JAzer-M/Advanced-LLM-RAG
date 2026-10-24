"""Offline audit of all attempts, exact-input replay and preserved project assets."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

PROJECT = Path('/Users/j/Desktop/Advanced-LLM-RAG')
OUTPUT = Path(__file__).resolve().parent
CODE = OUTPUT.parent / 'checkout'
sys.path.insert(0, str(CODE if CODE.is_dir() else PROJECT))

import agent


def main():
    old = json.loads((OUTPUT / 'run/actual_chat_calls.json').read_text())
    sixth = json.loads((OUTPUT / 'recheck/actual_chat_call.json').read_text())
    seventh = json.loads((OUTPUT / 'isolated_recheck/actual_chat_call.json').read_text())
    calls = old + [sixth, seventh]
    wire = json.loads((OUTPUT / 'actual_http_calls.json').read_text()) + [
        json.loads((OUTPUT / name / 'actual_http_call.json').read_text())
        for name in ('recheck', 'isolated_recheck')]
    assert len(calls) == len(wire) == 7
    assert all(c['response']['finish_reason'] == 'stop' for c in calls)
    assert all(w['status'] == 'returned' for w in wire)
    assert all(hashlib.sha256(c['prompt'].encode()).hexdigest() == w['prompt_sha256']
               for c, w in zip(calls, wire))
    usage = {key: sum(c['response']['usage'][key] for c in calls)
             for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    assert usage == {key: sum(w['usage'][key] for w in wire) for key in usage}
    for name, first in (('', old[0]), ('recheck', sixth), ('isolated_recheck', seventh)):
        frozen = json.loads((OUTPUT / name / 'protocol_before_run.json').read_text())
        assert datetime.fromisoformat(frozen['frozen_at_utc']) < datetime.fromisoformat(first['started_at_utc'])

    cases, hashes = agent.load_replay_cases(
        PROJECT, PROJECT / 'evaluation/results/holdout_v1_20261020', ['h01', 'h10', 'h11'])
    plans = json.loads((OUTPUT / 'isolated_recheck/bound_plans.json').read_text())
    assert len(cases['h10']['inventory']) == 8
    captured = []

    def saved_response(prompt):
        captured.append(prompt)
        assert prompt == seventh['prompt'], 'Final validation must replay the identical model input.'
        return seventh['response']

    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline verification')), \
            patch.object(socket, 'create_connection', side_effect=AssertionError('Offline verification')):
        accepted = agent.assess_evidence(cases['h10']['query'], plans['h10'],
                                         cases['h10']['evidence'], cases['h10']['inventory'], saved_response)
        try:
            agent.validate_assessment(json.loads(sixth['response']['answer']), plans['h10']['requirements'],
                                      cases['h10']['evidence'], cases['h10']['inventory'])
        except ValueError as error:
            assert 'borrows another requirement scope' in str(error)
        else:
            raise AssertionError('Earlier wrong dataset/partial output must remain rejected.')
        agent.validate_plan(plans['h01'], cases['h01']['query'])
        old_h11 = json.loads((OUTPUT / 'run/h11.json').read_text())
        agent.validate_assessment(old_h11['assessment'], plans['h11']['requirements'],
                                  cases['h11']['evidence'], cases['h11']['inventory'])
    data = json.loads(captured[0].split('INPUT DATA:\n', 1)[1])
    assert set(data) == {'requirements', 'search_queries', 'inventory', 'passages'}
    assert data['passages'] == cases['h10']['evidence']
    assert data['inventory'] == cases['h10']['inventory']
    assert [r['status'] for r in accepted['requirements']] == ['missing', 'supported']
    assert accepted['requirements'][0]['evidence'] == []
    action = accepted['next_action']
    assert action['type'] == 'search' and action['requirement_ids'] == ['r1']
    assert 'PopQA' not in action['query'] and 'TriviaQA' not in action['query']
    assert action['query'] == agent.search_query(plans['h10']['requirements'][0])
    by_id = {c['chunk_id']: c for c in cases['h10']['evidence']}
    references = []
    for r in accepted['requirements']:
        for ref in r['evidence']:
            chunk = by_id[ref['chunk_id']]
            assert agent.normalize(ref['quote']) in agent.normalize(chunk['text'])
            references.append({'requirement_id': r['id'], 'chunk_id': chunk['chunk_id'],
                               'source': chunk['source'], 'page': chunk['page'], 'quote': ref['quote']})
    agent.save_json(OUTPUT / 'verified_quotes.json', references)
    agent.save_json(OUTPUT / 'accepted_h10_replay.json', {
        'status': 'completed_offline_exact_prompt_replay', 'query': cases['h10']['query'],
        'plan': plans['h10'], 'assessment': accepted, 'actions_executed': 0,
        'real_api_response': 'isolated_recheck/actual_chat_call.json',
        'api_prompt_sha256': hashlib.sha256(captured[0].encode()).hexdigest(),
        'final_agent_sha256': agent.digest(Path(agent.__file__)), 'additional_api_calls': 0})
    baseline = json.loads((OUTPUT / 'baseline_hashes.json').read_text())
    changed = [name for name, digest in baseline['hashes'].items()
               if not (PROJECT / name).is_file() or agent.digest(PROJECT / name) != digest]
    report = {'actual_chat_attempts': 7, 'reported_usage': usage, 'all_finish_reasons_stop': True,
              'automatic_retries': 0, 'actions_executed': 0, 'fresh_retrieval': False,
              'fresh_final_answers': False, 'latest_prompt_exact_replay': True,
              'latest_checker_statuses': ['missing', 'supported'],
              'h10_manual_result': 'targeted_scope_and_support_correction_pass',
              'h01': 'cached planning anchors rebound locally; no fresh final-revision assessment',
              'h11': 'initial fresh stop and final-validator replay; not a new final-revision full run',
              'new_extractive_planner_live_tested': False,
              'final_validation_only_change_after_last_call': True,
              'baseline_files': len(baseline['hashes']), 'changed_baseline_files_before_publication': changed,
              'paired_input_hashes': hashes, 'verified_reference_count': len(references)}
    agent.save_json(OUTPUT / 'verification.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'paired_input_hashes'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
