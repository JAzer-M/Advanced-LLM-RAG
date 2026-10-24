# 单次执行与反馈：用小型原文夹具验证真实邻段读取、搜索分派、证据合并和中断记账。
# 模型响应使用替身；这里的状态标签只验证控制流程，不代表模型语义验收。
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import agent
from src import agent_tools as tools
from test_agent_step1 import assessment, missing, plan, response


def resources():
    chunks = [{'chunk_id': i, 'source': 'a.pdf', 'page': 1, 'title': 'A', 'section': 'Methods', 'text': text}
              for i, text in enumerate(('A uses the first procedure.', 'A reports the second condition.',
                                        'A gives further background.'))]
    return {'chunks': chunks, 'knowledge_base': {'version': tools.SEARCH_KB_VERSION,
             'manifest_sha256': 'fixture-manifest', 'files': {'faiss.index': 'index', 'chunks.json': 'chunks'}}}


def cases(fixture):
    return {'c0': {'query': 'Describe A.', 'kb_version': tools.SEARCH_KB_VERSION,
                   'evidence': [{key: fixture['chunks'][0][key] for key in agent.EVIDENCE_FIELDS}],
                   'inventory': [{'source': 'a.pdf', 'title': 'A'}]}}


def supported(cid=1):
    value = assessment()
    value['requirements'][0]['evidence'] = [{'chunk_id': cid,
        'quote': 'the first procedure' if cid == 0 else 'the second condition'}]
    return value


def tool_result(fixture, ids=(0, 1)):
    return {'knowledge_base': deepcopy(fixture['knowledge_base']),
            'results': [{**fixture['chunks'][i], 'kb_version': tools.SEARCH_KB_VERSION,
                         'score': 99, 'old_answer': 'OLD_ANSWER_SENTINEL'} for i in ids],
            'trace': {'private_note': 'TOOL_TRACE_SENTINEL'}}


class AgentFeedbackTests(unittest.TestCase):
    def setUp(self):
        settings = patch.object(agent.api, 'load_settings', return_value={'model': 'fixture'})
        settings.start()
        self.addCleanup(settings.stop)
        self.resources = resources()
        self.cases = cases(self.resources)

    def run_once(self, output, call, cases=None):
        return agent.run_diagnostics(cases or self.cases, output, {}, call,
                                     execute_once=True, resources=self.resources)

    def test_search_executes_once_then_model_receives_old_and_new_original_passages(self):
        original = deepcopy(self.cases)
        call = Mock(side_effect=[response(plan()), response(missing(assessment())), response(supported())])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources)) as search:
            summary = self.run_once(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        search.assert_called_once_with(agent.search_query(plan()['requirements'][0]), self.resources, source='a.pdf')
        self.assertEqual(call.call_count, 3)
        self.assertEqual(record['added_ids'], [1])
        self.assertEqual([item['chunk_id'] for item in record['evidence_after']], [0, 1])
        self.assertEqual(record['feedback_assessment']['next_action']['type'], 'answer')
        self.assertEqual(summary['actions_executed'], 1)
        self.assertEqual(summary['reassessment_api_attempts'], 1)
        self.assertEqual(summary['final_answer_generations'], 0)
        self.assertEqual(self.cases, original)
        prompt = call.call_args_list[2].args[0]
        for text in (chunk['text'] for chunk in self.resources['chunks'][:2]):
            self.assertIn(text, prompt)
        self.assertNotIn('OLD_ANSWER_SENTINEL', prompt)
        self.assertNotIn('TOOL_TRACE_SENTINEL', prompt)

    def test_neighbor_action_uses_real_reader_and_feedback_without_search(self):
        before = missing(assessment())
        before['next_action'].update(type='read_neighbors', query=None, chunk_id=0)
        call = Mock(side_effect=[response(plan()), response(before), response(supported())])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb') as search:
            summary = self.run_once(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        search.assert_not_called()
        self.assertEqual(record['execution']['tool_result']['trace']['selected_ids'], [0, 1])
        self.assertEqual(record['execution']['tool_result']['trace']['window'], 1)
        self.assertEqual(record['added_ids'], [1])
        self.assertEqual(summary['completed_cases'], 1)

    def test_new_search_suggestion_is_saved_without_executing_a_second_action(self):
        value = missing(assessment())
        call = Mock(side_effect=[response(plan()), response(value), response(value)])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources)) as search:
            summary = self.run_once(output, call)
        self.assertEqual(search.call_count, 1)
        self.assertEqual(call.call_count, 3)
        self.assertFalse(summary['automatic_action_loop'])
        self.assertEqual(summary['reassessed_actions']['c0']['type'], 'search')

    def test_answer_and_stop_skip_tools_and_redundant_feedback_calls(self):
        stop = missing(assessment())
        stop['next_action'].update(type='stop', query=None, source=None)
        for before in (supported(0), stop):
            call = Mock(side_effect=[response(plan()), response(before)])
            with self.subTest(action=before['next_action']['type']), TemporaryDirectory() as output, \
                    patch.object(tools, 'search_local_kb') as search, \
                    patch.object(tools, 'read_neighbors') as read:
                summary = self.run_once(output, call)
                self.assertEqual(summary['actions_executed'], 0)
                self.assertEqual(summary['reassessment_api_attempts'], 0)
                self.assertEqual(call.call_count, 2)
                search.assert_not_called()
                read.assert_not_called()

    def test_empty_tool_results_still_reassess_without_losing_existing_evidence(self):
        value = missing(assessment())
        call = Mock(side_effect=[response(plan()), response(value), response(value)])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=())):
            self.run_once(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['added_ids'], [])
        self.assertEqual([item['chunk_id'] for item in record['evidence_after']], [0])
        self.assertEqual(call.call_count, 3)

    def test_invalid_model_action_is_rejected_before_tool_execution(self):
        bad = missing(assessment())
        bad['next_action']['query'] = 'Invent an unrelated search'
        call = Mock(side_effect=[response(plan()), response(bad)])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb') as search:
            summary = self.run_once(output, call)
        self.assertEqual(summary['completed_cases'], 0)
        search.assert_not_called()
        self.assertEqual(call.call_count, 2)

    def test_failed_tool_is_logged_and_never_retried_on_resume(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment()))])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                side_effect=RuntimeError('fixture tool failed')) as search:
            first = self.run_once(output, call)
            self.run_once(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(search.call_count, 1)
        self.assertEqual(first['action_attempts'], 1)
        self.assertEqual(record['execution']['status'], 'failed')
        self.assertEqual(call.call_count, 2)

    def test_interruption_before_feedback_reuses_completed_tool_and_model_calls(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())), response(supported())])
        original_assess = agent.assess_evidence
        calls = []
        def interrupt_feedback(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise KeyboardInterrupt
            return original_assess(*args, **kwargs)
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources)) as search:
            with patch.object(agent, 'assess_evidence', side_effect=interrupt_feedback), \
                    self.assertRaises(KeyboardInterrupt):
                self.run_once(output, call)
            summary = self.run_once(output, call)
            resumed = self.run_once(output, call)
        self.assertEqual(search.call_count, 1)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(summary, resumed)
        self.assertEqual(summary['completed_cases'], 1)

    def test_interrupted_tool_is_not_automatically_reexecuted(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment()))])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                side_effect=KeyboardInterrupt) as search:
            with self.assertRaises(KeyboardInterrupt):
                self.run_once(output, call)
            summary = self.run_once(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(search.call_count, 1)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertIn('no automatic retry', record['error'])

    def test_failed_feedback_is_preserved_without_another_tool_or_model_attempt(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())), RuntimeError('fixture API failed')])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources)) as search:
            first = self.run_once(output, call)
            self.run_once(output, call)
        self.assertEqual(search.call_count, 1)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(first['actions_executed'], 1)
        self.assertEqual(first['failed_api_attempts'], 1)

    def test_two_cases_use_at_most_six_model_calls_and_two_tool_actions(self):
        case_pair = {name: deepcopy(self.cases['c0']) for name in ('c0', 'c1')}
        # 同题内容用不同问题原句区分审计签名，避免相同请求被缓存复用。
        case_pair['c1']['query'] = 'Explain A.'
        second_plan = {'requirements': [{'id': 'r1', 'subject': 'A', 'need': 'Explain A', 'question_quote': 'Explain A'}]}
        second_missing = missing(assessment())
        second_missing['next_action']['query'] = agent.search_query(second_plan['requirements'][0])
        call = Mock(side_effect=[response(plan()), response(missing(assessment())), response(supported()),
                                 response(second_plan), response(second_missing), response(supported())])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb', return_value=tool_result(self.resources)):
            summary = self.run_once(output, call, case_pair)
        self.assertEqual(summary['api_attempts'], 6)
        self.assertEqual(summary['actions_executed'], 2)
        self.assertEqual(summary['completed_cases'], 2)

    def test_budget_blocks_feedback_before_an_extra_api_request(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment()))])
        with TemporaryDirectory() as output, patch.object(agent, 'MAX_API_CALLS', 2), \
                patch.object(tools, 'search_local_kb', return_value=tool_result(self.resources)):
            summary = self.run_once(output, call)
        self.assertEqual(summary['actions_executed'], 1)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertEqual(call.call_count, 2)

    def test_mixed_case_version_is_rejected_before_any_model_call(self):
        self.cases['c0']['kb_version'] = 'another-version'
        call = Mock()
        with TemporaryDirectory() as output, self.assertRaisesRegex(ValueError, 'knowledge base'):
            self.run_once(output, call)
        call.assert_not_called()


class EvidenceMergeTests(unittest.TestCase):
    def test_mismatched_snapshot_text_id_and_version_are_rejected(self):
        fixture = resources()
        for field, value in (('text', 'Fabricated text'), ('page', 9), ('chunk_id', True),
                             ('chunk_id', -1), ('kb_version', 'other-version')):
            result = tool_result(fixture, ids=(1,))
            result['results'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                agent.merge_evidence(cases(fixture)['c0']['evidence'], fixture, result)
        result = tool_result(fixture)
        result['knowledge_base']['manifest_sha256'] = 'wrong-manifest'
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            agent.merge_evidence(cases(fixture)['c0']['evidence'], fixture, result)

    def test_budget_rejects_overflow_without_silently_truncating_old_or_new_passages(self):
        fixture = resources()
        original = deepcopy(fixture)
        for field, limit in (('MAX_FEEDBACK_PASSAGES', 1), ('MAX_FEEDBACK_CHARS', 1)):
            with self.subTest(field=field), patch.object(agent, field, limit), \
                    self.assertRaisesRegex(ValueError, 'budget exceeded'):
                agent.merge_evidence(cases(fixture)['c0']['evidence'], fixture, tool_result(fixture))
        self.assertEqual(fixture, original)

    def test_unknown_action_cannot_dispatch_an_unregistered_tool(self):
        with self.assertRaisesRegex(ValueError, 'Only search and read_neighbors'):
            agent.execute_action({'type': 'web_search'}, resources())


if __name__ == '__main__':
    unittest.main()
