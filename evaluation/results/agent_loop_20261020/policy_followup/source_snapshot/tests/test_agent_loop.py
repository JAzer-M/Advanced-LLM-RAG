# Agent循环回归：真实小型邻段、历史反馈、停止条件、一次校验修正和精确续接。
# 模型用替身提供响应；真实模型能否作出好判断另由冻结的小样例检查。
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import agent
from src import agent_tools as tools
from test_agent_feedback import cases, resources, supported, tool_result
from test_agent_step1 import assessment, missing, plan, response


def read_next():
    value = missing(assessment())
    value['next_action'].update(type='read_neighbors', query=None, chunk_id=1)
    return value


def final_support():
    value = supported(1)
    value['requirements'][0]['evidence'] = [{'chunk_id': 2, 'quote': 'requested conclusion'}]
    return value


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        settings = patch.object(agent.api, 'load_settings', return_value={'model': 'fixture'})
        settings.start()
        self.addCleanup(settings.stop)
        self.resources = resources()
        self.resources['chunks'][2]['text'] = 'A establishes the requested conclusion.'
        self.cases = cases(self.resources)

    def run_loop(self, output, call, max_actions=3):
        return agent.run_diagnostics(self.cases, output, {}, call,
                                     max_actions=max_actions, resources=self.resources)

    def test_search_then_real_neighbors_then_answer_ready(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())),
                                 response(read_next()), response(final_support())])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(1,))) as search, \
                patch.object(tools, 'read_neighbors', wraps=tools.read_neighbors) as read:
            summary = self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
            again = self.run_loop(output, call)
        self.assertEqual(summary, again)
        self.assertEqual(record['halt_reason'], 'answer_ready')
        self.assertEqual(record['actions_executed'], 2)
        self.assertEqual([step['added_ids'] for step in record['steps']], [[1], [2]])
        self.assertEqual([item['chunk_id'] for item in record['evidence_after']], [0, 1, 2])
        self.assertEqual(search.call_count, 1)
        read.assert_called_once_with(1, self.resources, source='a.pdf', window=2)
        self.assertEqual(call.call_count, 4)
        self.assertTrue(summary['automatic_action_loop'])
        self.assertEqual(summary['final_answer_generations'], 0)
        self.assertIn('tool_history', call.call_args_list[2].args[0])
        self.assertIn('added_ids', call.call_args_list[2].args[0])
        self.assertIn('read_neighbors', call.call_args_list[3].args[0])

    def test_same_action_with_different_reason_stops_before_repeating_tool(self):
        before = missing(assessment())
        after = deepcopy(before)
        after['next_action']['reason'] = '换了理由，实际检索参数仍相同。'
        call = Mock(side_effect=[response(plan()), response(before), response(after), response(after)])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(1,))) as search:
            self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['halt_reason'], 'repeated_action')
        self.assertEqual(search.call_count, 1)
        self.assertEqual(call.call_count, 4)

    def test_repeated_search_can_replan_once_to_neighbors_without_repeating_search(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())),
                                 response(missing(assessment())), response(read_next()), response(final_support())])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(1,))) as search:
            summary = self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['halt_reason'], 'answer_ready')
        self.assertEqual(record['actions_executed'], 2)
        self.assertEqual(search.call_count, 1)
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertIn('already executed', call.call_args_list[3].args[0])
        self.assertEqual(call.call_count, 5)

    def test_status_repair_and_action_replan_share_one_budget(self):
        bad = missing(assessment())
        bad['requirements'][0].update(status='partial', evidence=[{'chunk_id': 0, 'quote': 'first procedure'}],
                                     supported_part='A采用第一种做法。', gap='')
        call = Mock(side_effect=[response(plan()), response(bad), response(missing(assessment())),
                                 response(missing(assessment()))])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(1,))) as search:
            summary = self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['halt_reason'], 'repeated_action')
        self.assertEqual(search.call_count, 1)
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(call.call_count, 4)

    def test_no_new_evidence_stops_without_another_model_call(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment()))])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(0,))):
            self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['halt_reason'], 'no_new_evidence')
        self.assertEqual(record['steps'][0]['added_ids'], [])
        self.assertEqual(call.call_count, 2)

    def test_action_limit_stops_even_if_model_suggests_a_different_tool(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())), response(read_next())])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(1,))), patch.object(tools, 'read_neighbors') as read:
            self.run_loop(output, call, max_actions=1)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['halt_reason'], 'action_budget')
        read.assert_not_called()

    def test_api_budget_stops_before_starting_an_unreviewable_action(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())), response(read_next())])
        with TemporaryDirectory() as output, patch.object(agent, 'MAX_API_CALLS', 3), \
                patch.object(tools, 'search_local_kb', return_value=tool_result(self.resources, ids=(1,))), \
                patch.object(tools, 'read_neighbors') as read:
            self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['halt_reason'], 'api_budget')
        self.assertEqual(call.call_count, 3)
        read.assert_not_called()

    def test_terminal_answer_and_stop_do_not_execute_tools(self):
        stop = missing(assessment())
        stop['next_action'].update(type='stop', query=None, source=None)
        for value, reason in ((supported(0), 'answer_ready'), (stop, 'model_stop')):
            call = Mock(side_effect=[response(plan()), response(value)])
            with self.subTest(reason=reason), TemporaryDirectory() as output, \
                    patch.object(tools, 'search_local_kb') as search:
                self.run_loop(output, call)
                record = json.loads((Path(output) / 'c0.json').read_text())
            self.assertEqual(record['halt_reason'], reason)
            search.assert_not_called()
            self.assertEqual(call.call_count, 2)

    def test_partial_empty_gap_requests_one_new_validation_and_keeps_raw_response(self):
        bad = supported(0)
        bad['requirements'][0]['status'] = 'partial'
        bad['next_action'] = missing(assessment())['next_action']
        original = deepcopy(bad)
        call = Mock(side_effect=[response(plan()), response(bad), response(supported(0))])
        with TemporaryDirectory() as output:
            summary = self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
            calls = json.loads((Path(output) / 'actual_chat_calls.json').read_text())
        self.assertEqual(record['halt_reason'], 'answer_ready')
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertIn('gap must be a nonempty string', call.call_args_list[2].args[0])
        self.assertEqual(json.loads(calls[1]['response']['answer']), original)
        self.assertEqual(bad, original)

    def test_invalid_repair_is_rejected_without_another_request_or_tool(self):
        bad = supported(0)
        bad['requirements'][0]['status'] = 'partial'
        call = Mock(side_effect=[response(plan()), response(bad), response(bad)])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb') as search:
            summary = self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(call.call_count, 3)
        search.assert_not_called()

    def test_transport_failure_does_not_trigger_validation_repair(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())), RuntimeError('HTTP 503')])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(1,))) as search:
            summary = self.run_loop(output, call)
            self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertEqual(summary['validation_repair_attempts'], 0)
        self.assertEqual(search.call_count, 1)
        self.assertEqual(call.call_count, 3)

    def test_completed_steps_are_reused_after_interruption_before_feedback(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment())),
                                 response(read_next()), response(final_support())])
        original_assess = agent.assess_evidence
        seen = []
        def interrupt_last(*args, **kwargs):
            seen.append(1)
            if len(seen) == 3:
                raise KeyboardInterrupt
            return original_assess(*args, **kwargs)
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb',
                return_value=tool_result(self.resources, ids=(1,))) as search, \
                patch.object(tools, 'read_neighbors', wraps=tools.read_neighbors) as read:
            with patch.object(agent, 'assess_evidence', side_effect=interrupt_last), self.assertRaises(KeyboardInterrupt):
                self.run_loop(output, call)
            summary = self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 1)
        self.assertEqual(search.call_count, 1)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(call.call_count, 4)

    def test_interrupted_tool_is_not_automatically_executed_again(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment()))])
        with TemporaryDirectory() as output, patch.object(tools, 'search_local_kb', side_effect=KeyboardInterrupt) as search:
            with self.assertRaises(KeyboardInterrupt):
                self.run_loop(output, call)
            summary = self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertEqual(search.call_count, 1)

    def test_context_budget_stops_without_dropping_existing_evidence(self):
        call = Mock(side_effect=[response(plan()), response(missing(assessment()))])
        with TemporaryDirectory() as output, patch.object(agent, 'MAX_FEEDBACK_PASSAGES', 1), \
                patch.object(tools, 'search_local_kb', return_value=tool_result(self.resources, ids=(1,))):
            self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
        self.assertEqual(record['halt_reason'], 'context_budget')
        self.assertEqual([item['chunk_id'] for item in record['evidence_after']], [0])
        self.assertEqual(call.call_count, 2)

    def test_loop_limits_and_conflicting_modes_fail_before_calls(self):
        call = Mock()
        for limit in (-1, 4, True, 1.0):
            with self.subTest(limit=limit), TemporaryDirectory() as output, self.assertRaises(ValueError):
                self.run_loop(output, call, max_actions=limit)
        with TemporaryDirectory() as output, self.assertRaises(ValueError):
            agent.run_diagnostics(self.cases, output, {}, call, execute_once=True, max_actions=2, resources=self.resources)
        call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
