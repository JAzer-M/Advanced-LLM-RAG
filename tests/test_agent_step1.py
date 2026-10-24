# Agent 决策原型的测试：证据身份、六次预算、失败留档和精确中断续接。
# Mock 响应替代真实 API；临时目录承载运行记录，测试期间不执行任何补查工具。

"""Behavioral checks for evidence provenance, bounded calls and interruption recovery."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import agent


def plan():
    return {'requirements': [{'id': 'r1', 'subject': 'A', 'need': 'A', 'question_quote': 'A'}]}


def passages():
    return [{'chunk_id': 17, 'source': 'a.pdf', 'page': 2, 'title': 'A',
             'text': 'A uses the ﬁrst procedure.'}]


def inventory():
    return [{'source': 'a.pdf', 'title': 'A'}, {'source': 'b.pdf', 'title': 'B'}]


def assessment():
    return {'requirements': [{'id': 'r1', 'status': 'supported',
                             'evidence': [{'chunk_id': 17, 'quote': 'the first procedure'}],
                             'supported_part': 'A使用第一种做法。',
                             'reason': '原文明确说明。', 'gap': ''}],
            'next_action': {'type': 'answer', 'reason': '全部需求已有证据。',
                            'requirement_ids': [], 'query': None, 'source': None, 'chunk_id': None},
            'scope_check': {'valid': True, 'reason': '需求与行动保持原题范围。'}}


def missing(result):
    result['requirements'][0].update(status='missing', evidence=[], supported_part='', gap='缺少A的具体做法。')
    result['next_action'].update(type='search', requirement_ids=['r1'],
                                 query=agent.search_query(plan()['requirements'][0]), source='a.pdf')
    return result


def response(payload):
    if set(payload) == {'requirements'}:
        payload = {'requirements': [{k: v for k, v in r.items() if k != 'need'}
                                     for r in payload['requirements']]}
    return {'answer': json.dumps(payload, ensure_ascii=False), 'finish_reason': 'stop',
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


def cases(count=1):
    return {f'c{i}': {'query': f'Describe A in case {i}.', 'kb_version': 'fixture',
                      'evidence': [{**p, 'text': p['text'] + f' Case {i}.'} for p in passages()],
                      'inventory': inventory()} for i in range(count)}


class AgentValidationTests(unittest.TestCase):
    def check(self, result):
        return agent.validate_assessment(result, plan()['requirements'], passages(), inventory())

    def test_requirement_cannot_introduce_unnamed_subject(self):
        value = plan(); value['requirements'][0]['subject'] = 'Invented Method'
        with self.assertRaisesRegex(ValueError, 'subject'):
            agent.validate_plan(value, 'Describe A.')

    def test_question_quote_must_really_appear_in_question(self):
        value = plan(); value['requirements'][0]['question_quote'] = 'A on an unasked dataset'
        with self.assertRaisesRegex(ValueError, 'question_quote'):
            agent.validate_plan(value, 'Describe A.')

    def test_plan_rejects_duplicate_or_out_of_order_requirement_ids(self):
        value = plan(); value['requirements'].append(deepcopy(value['requirements'][0]))
        with self.assertRaisesRegex(ValueError, 'IDs'):
            agent.validate_plan(value, 'Describe A.')

    def test_real_quote_allows_existing_nfkc_and_whitespace_normalization(self):
        value = assessment(); value['requirements'][0]['evidence'][0]['quote'] = 'the  FIRST\nprocedure'
        self.assertIs(self.check(value), value)

    def test_citation_number_cannot_masquerade_as_chunk_id(self):
        value = assessment(); value['requirements'][0]['evidence'][0]['chunk_id'] = 1
        with self.assertRaisesRegex(ValueError, 'chunk ID'):
            self.check(value)

    def test_fabricated_quote_is_rejected(self):
        value = assessment(); value['requirements'][0]['evidence'][0]['quote'] = 'A has accuracy 99.9 percent'
        with self.assertRaisesRegex(ValueError, 'Quoted text'):
            self.check(value)

    def test_supported_or_partial_cannot_omit_evidence(self):
        for status in ('supported', 'partial'):
            value = assessment(); value['requirements'][0].update(status=status, evidence=[])
            if status == 'partial':value['requirements'][0]['gap'] = '需要补充细节。'
            with self.subTest(status=status), self.assertRaises(ValueError):self.check(value)

    def test_missing_does_not_allow_unrelated_quotes(self):
        value = missing(assessment()); value['requirements'][0]['evidence'] = assessment()['requirements'][0]['evidence']
        with self.assertRaisesRegex(ValueError, 'Missing'):
            self.check(value)

    def test_cannot_propose_answer_while_requirements_are_missing(self):
        value = missing(assessment()); value['next_action'] = assessment()['next_action']
        with self.assertRaisesRegex(ValueError, 'Answer requires'):
            self.check(value)

    def test_action_source_and_tool_are_limited(self):
        for change in ({'source': 'invented.pdf'}, {'type': 'web_search'}, {'requirement_ids': ['unknown']}):
            value = missing(assessment()); value['next_action'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):self.check(value)

    def test_neighbor_read_must_target_same_source_and_supplied_chunk(self):
        value = missing(assessment())
        value['next_action'].update(type='read_neighbors', query=None, chunk_id=17, source='b.pdf')
        with self.assertRaisesRegex(ValueError, 'source must match'):
            self.check(value)

    def test_every_requirement_must_be_checked_once(self):
        for checks in ([], assessment()['requirements'] * 2):
            value = assessment(); value['requirements'] = checks
            with self.subTest(checks=checks), self.assertRaisesRegex(ValueError, 'every requirement'):
                self.check(value)


class AgentAuditTests(unittest.TestCase):
    def setUp(self):
        settings = patch.object(agent.api, 'load_settings', return_value={'model': 'fixture'})
        settings.start(); self.addCleanup(settings.stop)

    def test_three_cases_use_six_calls_and_completed_resume_uses_none(self):
        call = Mock(side_effect=[response(p) for _ in range(3) for p in (plan(), assessment())])
        with TemporaryDirectory() as temporary:
            first = agent.run_diagnostics(cases(3), temporary, {}, call)
            second = agent.run_diagnostics(cases(3), temporary, {}, call)
            self.assertEqual(first['api_attempts'], 6)
            self.assertEqual(second['api_attempts'], 6)
            self.assertEqual(first['completed_cases'], 3)
            self.assertEqual(first['actions_executed'], 0)
            self.assertEqual(call.call_count, 6)

    def test_budget_stops_before_an_extra_api_request(self):
        call = Mock(side_effect=[response(plan()), response(assessment())])
        with TemporaryDirectory() as temporary, patch.object(agent, 'MAX_API_CALLS', 1):
            summary = agent.run_diagnostics(cases(), temporary, {}, call)
            record = json.loads((Path(temporary) / 'c0.json').read_text())
            self.assertEqual(call.call_count, 1)
            self.assertEqual(summary['api_attempts'], 1)
            self.assertIn('budget exhausted', record['error'])

    def test_failure_is_preserved_and_not_automatically_retried(self):
        call = Mock(side_effect=RuntimeError('Fixture request failed.'))
        with TemporaryDirectory() as temporary:
            first = agent.run_diagnostics(cases(), temporary, {}, call)
            agent.run_diagnostics(cases(), temporary, {}, call)
            record = json.loads((Path(temporary) / 'c0.json').read_text())
            self.assertEqual(first['completed_cases'], 0)
            self.assertEqual(first['failed_api_attempts'], 1)
            self.assertIn('Fixture request failed', record['error'])
            self.assertEqual(call.call_count, 1)

    def test_interruption_reuses_completed_plan_response(self):
        call = Mock(side_effect=[response(plan()), response(assessment())])
        with TemporaryDirectory() as temporary:
            with patch.object(agent, 'assess_evidence', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                agent.run_diagnostics(cases(), temporary, {}, call)
            result = agent.run_diagnostics(cases(), temporary, {}, call)
            self.assertEqual(result['api_attempts'], 2)
            self.assertEqual(result['completed_cases'], 1)
            self.assertEqual(call.call_count, 2)

    def test_input_change_refuses_to_resume_before_any_new_call(self):
        call = Mock(side_effect=[response(plan()), response(assessment())])
        with TemporaryDirectory() as temporary:
            agent.run_diagnostics(cases(), temporary, {}, call)
            with self.assertRaisesRegex(ValueError, 'cannot resume'):
                agent.run_diagnostics(cases(), temporary, {'changed': 'hash'}, call)
            self.assertEqual(call.call_count, 2)

    def test_invalid_assessment_keeps_raw_response_and_has_no_schema_retry(self):
        bad = assessment(); bad['requirements'][0]['evidence'][0]['quote'] = 'Fabricated evidence'
        call = Mock(side_effect=[response(plan()), response(bad)])
        with TemporaryDirectory() as temporary:
            summary = agent.run_diagnostics(cases(), temporary, {}, call)
            raw = json.loads((Path(temporary) / 'actual_chat_calls.json').read_text())
            self.assertEqual(summary['completed_cases'], 0)
            self.assertEqual(summary['failed_api_attempts'], 0)
            self.assertIn('Fabricated evidence', raw[1]['response']['answer'])
            self.assertEqual(call.call_count, 2)

    def test_plan_receives_only_question_and_neither_prompt_receives_old_answers(self):
        call = Mock(side_effect=[response(plan()), response(assessment())])
        case = cases()['c0']
        agent.plan_requirements(case['query'], call)
        agent.assess_evidence(case['query'], plan(), case['evidence'], case['inventory'], call)
        first, second = [item.args[0] for item in call.call_args_list]
        self.assertNotIn(case['evidence'][0]['text'], first)
        self.assertIn(case['evidence'][0]['text'], second)
        self.assertNotIn('OLD_ANSWER_SENTINEL', first + second)


class AgentReplayInputTests(unittest.TestCase):
    def test_replay_whitelist_excludes_old_answer_and_rejects_tampered_passage(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary); folder = root / 'data/processed/versions/fixture'; folder.mkdir(parents=True)
            chunk = {**passages()[0], 'chunk_id': 0}
            agent.save_json(folder / 'chunks.json', [chunk]); (folder / 'faiss.index').write_bytes(b'fixture-index')
            files = {name: agent.digest(folder / name) for name in ('chunks.json', 'faiss.index')}
            agent.save_json(folder / 'manifest.json', {'version': 'fixture', 'chunk_count': 1, 'files': files})
            record = {'status': 'completed', 'query': 'Describe A.', 'knowledge_base': {'version': 'fixture',
                      'files': files, 'manifest_sha256': agent.digest(folder / 'manifest.json')},
                      'ledger': {'citation_registry': [chunk]}, 'context': chunk['text'], 'selected_ids': [0],
                      'answer': 'OLD_ANSWER_SENTINEL', 'gold_evidence': 'GOLD_SENTINEL'}
            agent.save_json(root / 'c0.json', record)
            loaded, hashes = agent.load_replay_cases(root, root, ['c0'])
            self.assertNotIn('SENTINEL', json.dumps(loaded))
            self.assertEqual(len(hashes), 4)
            record['ledger']['citation_registry'][0]['text'] = 'Tampered passage'
            agent.save_json(root / 'c0.json', record)
            with self.assertRaisesRegex(ValueError, 'Saved passage'):
                agent.load_replay_cases(root, root, ['c0'])


if __name__ == '__main__':
    unittest.main()
