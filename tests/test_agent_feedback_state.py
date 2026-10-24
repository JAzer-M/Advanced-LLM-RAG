# 反馈状态回归：真实循环重放旧h10失败，保留旧结果；不调用模型或重新检索。
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import agent
from src import agent_tools as tools
from test_agent_feedback import tool_result
from test_agent_step1 import response


class SavedFeedbackStateTests(unittest.TestCase):
    def test_unrelated_search_does_not_erase_an_already_supported_requirement(self):
        project = Path(__file__).resolve().parents[1]
        saved = project / 'evaluation/results/agent_auto_improvement_20261022/scoped_inputs/runs/h10_auto/loop'
        case = json.loads((saved / 'inputs.json').read_text())['question']
        original = json.loads((saved / 'question.json').read_text())
        calls = json.loads((saved / 'actual_chat_calls.json').read_text())
        chunks = json.loads((project / 'data/processed/versions' / tools.SEARCH_KB_VERSION / 'chunks.json').read_text())
        resource = {'chunks': chunks, 'knowledge_base': original['steps'][0]['execution']['tool_result']['knowledge_base']}
        call = Mock(side_effect=[entry['response'] for entry in calls])
        with TemporaryDirectory() as output, patch.object(agent.api, 'load_settings', return_value={'model': 'offline-fixture'}), \
                patch.object(tools, 'search_local_kb', return_value=original['steps'][0]['execution']['tool_result']):
            # 固定到旧响应覆盖的首次工具/反馈前缀，避免虚构原记录没有的后续模型响应。
            summary = agent.run_diagnostics({'question': case}, output, {}, call, resources=resource, max_actions=1)
            record = json.loads((Path(output) / 'question.json').read_text())
        self.assertEqual(record['status'], 'completed', record.get('error'))
        self.assertEqual(record['steps'][0]['assessment_after']['requirements'][1], original['assessment']['requirements'][1])
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(call.call_count, 4)
        # 重放仍缺RAG判据且原行动重复，应明确停下；这不是h10答题成功。
        self.assertEqual(record['halt_reason'], 'repeated_action')
        self.assertEqual(record['actions_executed'], 1)


def small_case():
    query = 'Describe A. Describe B.'
    requirements = [{'id': f'r{i}', 'subject': name, 'need': f'Describe {name}',
                     'question_quote': f'Describe {name}'} for i, name in enumerate(('A', 'B'), 1)]
    texts = [('a.pdf', 'A', 'A provides background.'),
             ('b.pdf', 'B', 'B uses the second procedure.'),
             ('a.pdf', 'A', 'A reports extra background.'),
             ('b.pdf', 'B', 'B instead requires a different procedure.'),
             ('a.pdf', 'A', 'A uses the requested procedure.'),
             ('a.pdf', 'A', 'The comparison reports that B requires a different procedure.')]
    chunks = [{'chunk_id': i, 'source': source, 'title': title, 'text': text, 'page': 1, 'section': 'Methods'}
              for i, (source, title, text) in enumerate(texts)]
    resources = {'chunks': chunks, 'knowledge_base': {'version': tools.SEARCH_KB_VERSION,
        'manifest_sha256': 'fixture', 'files': {'faiss.index': 'index', 'chunks.json': 'chunks'}}}
    case = {'query': query, 'kb_version': tools.SEARCH_KB_VERSION,
            'evidence': [{key: c[key] for key in agent.EVIDENCE_FIELDS} for c in chunks[:2]],
            'inventory': [{'source': 'a.pdf', 'title': 'A'}, {'source': 'b.pdf', 'title': 'B'}]}
    return {'requirements': requirements}, resources, {'c0': case}


def initial_check(plan):
    return {'requirements': [
        {'id': 'r1', 'status': 'missing', 'evidence': [], 'supported_part': '',
         'reason': 'Only background for A is available.', 'gap': 'A的做法缺少原文。'},
        {'id': 'r2', 'status': 'supported', 'evidence': [{'chunk_id': 1, 'quote': 'the second procedure'}],
         'supported_part': 'B uses the second procedure.', 'reason': 'The supplied B passage establishes its procedure.', 'gap': ''}],
        'next_action': {'type': 'search', 'reason': 'Need the procedure for A.', 'requirement_ids': ['r1'],
                        'query': agent.search_query(plan['requirements'][0]), 'source': None, 'chunk_id': None},
        'scope_check': {'valid': True, 'reason': 'Each requirement checked independently.'}}


def invalid_b(check):
    check = deepcopy(check)
    check['requirements'][1]['status'] = 'partial'
    return check


class IncrementalFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.resources, self.cases = small_case()
        self.initial = initial_check(self.plan)
        settings = patch.object(agent.api, 'load_settings', return_value={'model': 'fixture'})
        settings.start()
        self.addCleanup(settings.stop)

    def run_loop(self, replies, added_ids, execute_once=False):
        call = Mock(side_effect=[response(v) for v in replies])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=added_ids)) as search:
            options = {'execute_once': True} if execute_once else {'max_actions': 1}
            summary = agent.run_diagnostics(self.cases, output, {}, call, resources=self.resources, **options)
            record = json.loads((Path(output) / 'c0.json').read_text())
            again = agent.run_diagnostics(self.cases, output, {}, call, resources=self.resources, **options)
            self.assertEqual(summary, again)
        return summary, record, call, search

    def complete_a(self):
        value = deepcopy(self.initial)
        value['requirements'][0].update(status='supported', evidence=[{'chunk_id': 4, 'quote': 'requested procedure'}],
            supported_part='A uses the requested procedure.', reason='The new A passage establishes it.', gap='')
        value['next_action'].update(type='answer', requirement_ids=[], query=None, source=None)
        return value

    def test_unrelated_invalid_update_cannot_erase_supported_fact_or_spend_second_repair(self):
        summary, record, call, search = self.run_loop(
            [self.plan, invalid_b(self.initial), self.initial, invalid_b(self.complete_a())], (4,))
        self.assertEqual(record['status'], 'completed', record.get('error'))
        self.assertEqual(record['halt_reason'], 'answer_ready')
        self.assertEqual(record['final_assessment']['requirements'][1], self.initial['requirements'][1])
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(call.call_count, 4)
        self.assertEqual(search.call_count, 1)
        self.assertIn('retained_supported_requirements', call.call_args_list[-1].args[0])

    def test_feedback_can_return_only_the_requirements_requested_for_recheck(self):
        after = self.complete_a()
        after['requirements'] = after['requirements'][:1]
        _, record, call, _ = self.run_loop([self.plan, self.initial, after], (4,))
        self.assertEqual(record['status'], 'completed', record.get('error'))
        self.assertEqual(record['halt_reason'], 'answer_ready')
        self.assertEqual(record['final_assessment']['requirements'][1], self.initial['requirements'][1])
        self.assertEqual(call.call_count, 3)

    def test_real_new_same_source_conflict_reopens_supported_requirement(self):
        after = deepcopy(self.initial)
        after['requirements'][1].update(status='conflicting', supported_part='', gap='B的两段原文结论冲突。',
            reason='New evidence contradicts the old procedure.', evidence=[{'chunk_id': 1, 'quote': 'second procedure'},
                                                                          {'chunk_id': 3, 'quote': 'different procedure'}])
        after['next_action'].update(type='stop', requirement_ids=['r1', 'r2'], query=None, source=None)
        _, record, call, _ = self.run_loop([self.plan, self.initial, after], (3,))
        self.assertEqual(record['status'], 'completed', record.get('error'))
        self.assertEqual(record['final_assessment']['requirements'][1]['status'], 'conflicting')
        self.assertEqual(record['steps'][0]['feedback_scope']['recheck_requirement_ids'], ['r1', 'r2'])
        self.assertEqual(call.call_count, 3)

    def test_cross_source_explicit_subject_also_reopens_supported_requirement(self):
        after = deepcopy(self.initial)
        after['requirements'][1].update(status='conflicting', supported_part='', gap='B的两段原文结论冲突。',
            reason='A different paper explicitly contradicts B.', evidence=[{'chunk_id': 1, 'quote': 'second procedure'},
                                                                         {'chunk_id': 5, 'quote': 'B requires a different procedure'}])
        after['next_action'].update(type='stop', requirement_ids=['r1', 'r2'], query=None, source=None)
        _, record, _, _ = self.run_loop([self.plan, self.initial, after], (5,))
        self.assertEqual(record['status'], 'completed', record.get('error'))
        self.assertEqual(record['final_assessment']['requirements'][1]['status'], 'conflicting')

    def test_related_invalid_state_is_still_rejected_after_shared_repair_is_spent(self):
        summary, record, call, _ = self.run_loop(
            [self.plan, invalid_b(self.initial), self.initial, invalid_b(self.initial)], (3,))
        self.assertEqual(record['status'], 'failed')
        self.assertIn('repair budget was already used', record['error'])
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(call.call_count, 4)

    def test_invalid_state_for_unmet_requirement_is_not_silently_promoted(self):
        after = self.complete_a()
        after['requirements'][0]['status'] = 'partial'
        _, record, call, _ = self.run_loop([self.plan, invalid_b(self.initial), self.initial, after], (4,))
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(call.call_count, 4)

    def test_initial_invalid_state_still_requires_a_real_corrected_response(self):
        _, record, call, search = self.run_loop([self.plan, invalid_b(self.initial), invalid_b(self.initial)], (4,))
        self.assertEqual(record['status'], 'failed')
        search.assert_not_called()
        self.assertEqual(call.call_count, 3)

    def test_single_action_feedback_uses_the_same_state_retention_rules(self):
        _, record, call, _ = self.run_loop([self.plan, self.initial, invalid_b(self.complete_a())], (4,), execute_once=True)
        self.assertEqual(record['status'], 'completed', record.get('error'))
        self.assertEqual(record['feedback_assessment']['requirements'][1], self.initial['requirements'][1])
        self.assertEqual(call.call_count, 3)

    def test_unknown_duplicate_or_missing_recheck_ids_cannot_be_hidden_by_retention(self):
        for kind in ('unknown', 'duplicate', 'missing'):
            with self.subTest(kind=kind):
                after = self.complete_a()
                if kind == 'unknown':
                    extra = deepcopy(after['requirements'][0])
                    extra['id'] = 'r99'
                    after['requirements'].append(extra)
                elif kind == 'duplicate':
                    after['requirements'].append(deepcopy(after['requirements'][1]))
                else:
                    after['requirements'] = after['requirements'][1:]
                _, record, call, _ = self.run_loop([self.plan, invalid_b(self.initial), self.initial, after], (4,))
                self.assertEqual(record['status'], 'failed')
                self.assertEqual(call.call_count, 4)

    def test_rechecked_claims_still_require_real_quotes_and_correct_subject_scope(self):
        for kind in ('quote', 'subject'):
            with self.subTest(kind=kind):
                after = self.complete_a()
                if kind == 'quote':
                    after['requirements'][0]['evidence'][0]['quote'] = 'invented 99.9 percent'
                else:
                    after['requirements'][0]['supported_part'] = 'B uses the second procedure.'
                _, record, call, _ = self.run_loop([self.plan, invalid_b(self.initial), self.initial, after], (4,))
                self.assertEqual(record['status'], 'failed')
                self.assertEqual(call.call_count, 4)


if __name__ == '__main__':
    unittest.main()
