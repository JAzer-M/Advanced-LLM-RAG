# 规划可用性回归：正常回指/联合主语可用，伪造引文与跨主体条件仍被拒绝。
# 循环测试经过真实记账入口；模型与检索使用小型夹具，不产生网络请求。
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import agent
from test_agent_feedback import cases, resources, supported
from test_agent_step1 import assessment, plan, response


class AgentPlanBindingTests(unittest.TestCase):
    def test_it_refers_to_the_unique_named_paper_in_an_earlier_clause(self):
        query = 'How does Atlas initialize biases, and why does it use positive values?'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': 'How does Atlas initialize biases'},
            {'id': 'r2', 'subject': 'Atlas', 'question_quote': 'why does it use positive values'}]}
        result = agent.bind_requirements(proposal, query)
        quote = result['requirements'][1]['question_quote']
        self.assertIn('atlas', agent.normalize(quote))
        self.assertIn('why does it use positive values', quote)
        self.assertIn(agent.normalize(quote), agent.normalize(query))

    def test_it_is_not_resolved_when_multiple_papers_are_declared(self):
        query = 'Compare Atlas with Nova, and explain why it uses positive values.'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': 'why it uses positive values'},
            {'id': 'r2', 'subject': 'Nova', 'question_quote': 'Nova'}]}
        with self.assertRaisesRegex(ValueError, 'own subject'):
            agent.bind_requirements(proposal, query)

    def test_repeated_named_antecedents_are_not_guessed(self):
        query = 'Atlas compares Atlas settings, and why does it use positive values?'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': 'why does it use positive values'}]}
        with self.assertRaisesRegex(ValueError, 'own subject'):
            agent.bind_requirements(proposal, query)

    def joint_plan(self):
        clause = 'What do Atlas and Nova report about normalization'
        query = clause + ', and what costs does Nova report on Orion?'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': clause},
            {'id': 'r2', 'subject': 'Nova', 'question_quote': clause},
            {'id': 'r3', 'subject': 'Nova', 'question_quote': 'what costs does Nova report on Orion'}]}
        return query, proposal

    def test_joint_subjects_keep_original_quote_and_independent_operative_needs(self):
        query, proposal = self.joint_plan()
        result = agent.bind_requirements(proposal, query)
        for index, other in ((0, 'Nova'), (1, 'Atlas')):
            row = result['requirements'][index]
            self.assertEqual(row['question_quote'], proposal['requirements'][index]['question_quote'])
            self.assertTrue(agent.names_subject(row['subject'], row['need']))
            self.assertFalse(agent.names_subject(other, row['need']))
            self.assertIn('report about normalization', row['need'])
            self.assertNotIn('Orion', agent.search_query(row))
        self.assertIn('Orion', agent.search_query(result['requirements'][2]))

    def test_projection_cannot_invent_a_condition(self):
        query, proposal = self.joint_plan()
        result = agent.bind_requirements(proposal, query)
        result['requirements'][0]['need'] += ' on an unasked benchmark'
        with self.assertRaisesRegex(ValueError, 'bound question excerpt'):
            agent.validate_plan(result, query)

    def test_joint_quote_cannot_pull_in_the_other_papers_later_condition(self):
        query, proposal = self.joint_plan()
        proposal['requirements'][0]['question_quote'] = query
        with self.assertRaisesRegex(ValueError, 'another declared subject'):
            agent.bind_requirements(proposal, query)

    def test_asymmetric_clauses_cannot_be_projected_as_shared_subjects(self):
        query = 'What do Atlas on Orion and Nova on Vega report about normalization?'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': query},
            {'id': 'r2', 'subject': 'Nova', 'question_quote': 'Nova on Vega'}]}
        with self.assertRaisesRegex(ValueError, 'another declared subject'):
            agent.bind_requirements(proposal, query)

    def test_respectively_conditions_are_not_treated_as_a_shared_predicate(self):
        query = 'How do Atlas and Nova perform on Orion and Vega respectively?'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': query},
            {'id': 'r2', 'subject': 'Nova', 'question_quote': query}]}
        with self.assertRaisesRegex(ValueError, 'another declared subject'):
            agent.bind_requirements(proposal, query)

    def test_joint_requirements_still_reject_a_foreign_dataset_in_a_gap(self):
        query, proposal = self.joint_plan()
        requirements = agent.bind_requirements(proposal, query)['requirements']
        value = assessment()
        value['requirements'] = [{
            'id': item['id'], 'status': 'missing', 'evidence': [], 'supported_part': '',
            'reason': '尚无原文。', 'gap': '需要原文。'} for item in requirements]
        value['requirements'][0]['gap'] = 'Atlas on Orion is missing.'
        value['next_action'].update(type='stop', reason='证据不足。')
        with self.assertRaisesRegex(ValueError, 'borrows another requirement scope'):
            agent.validate_assessment(value, requirements, [], [])

    def test_noncontiguous_excerpts_remain_invalid(self):
        proposal = {'requirements': [{'id': 'r1', 'subject': 'Atlas',
                                      'question_quote': 'Atlas uses crop size'}]}
        with self.assertRaisesRegex(ValueError, 'question_quote'):
            agent.bind_requirements(proposal, 'Atlas uses scaling, and which crop size is used?')


class AgentPlanRepairLoopTests(unittest.TestCase):
    def setUp(self):
        settings = patch.object(agent.api, 'load_settings', return_value={'model': 'fixture'})
        settings.start()
        self.addCleanup(settings.stop)
        self.fixture = resources()
        self.inputs = cases(self.fixture)
        self.invalid = plan()
        self.invalid['requirements'][0]['question_quote'] = 'A on an unasked benchmark'

    def run_loop(self, output, call):
        return agent.run_diagnostics(self.inputs, output, {}, call,
                                     max_actions=3, resources=self.fixture)

    def test_one_invalid_plan_can_be_corrected_and_resumed_without_new_calls(self):
        call = Mock(side_effect=[response(self.invalid), response(plan()), response(supported(0))])
        with TemporaryDirectory() as output:
            summary = self.run_loop(output, call)
            record = json.loads((Path(output) / 'c0.json').read_text())
            calls_log = json.loads((Path(output) / 'actual_chat_calls.json').read_text())
            self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 1)
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(record['halt_reason'], 'answer_ready')
        self.assertEqual(record['validation_repairs'][0]['phase'], 'plan')
        self.assertEqual([row['phase'] for row in calls_log], ['plan', 'plan_repair', 'assess'])
        self.assertIn('question_quote', call.call_args_list[1].args[0])
        self.assertIn('A on an unasked benchmark', calls_log[0]['response']['answer'])
        self.assertEqual(call.call_count, 3)

    def test_invalid_correction_stops_after_two_calls(self):
        call = Mock(side_effect=[response(self.invalid), response(self.invalid)])
        with TemporaryDirectory() as output:
            summary = self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(call.call_count, 2)

    def test_plan_and_assessment_corrections_share_the_existing_one_repair_budget(self):
        bad_assessment = supported(0)
        bad_assessment['requirements'][0]['status'] = 'partial'
        call = Mock(side_effect=[response(self.invalid), response(plan()), response(bad_assessment)])
        with TemporaryDirectory() as output:
            summary = self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertEqual(summary['validation_repair_attempts'], 1)
        self.assertEqual(call.call_count, 3)

    def test_plan_repair_does_not_bypass_the_six_call_limit(self):
        call = Mock(side_effect=[response(self.invalid), response(plan())])
        with TemporaryDirectory() as output, patch.object(agent, 'MAX_API_CALLS', 1):
            summary = self.run_loop(output, call)
        self.assertEqual(summary['completed_cases'], 0)
        self.assertEqual(call.call_count, 1)

    def test_transport_or_truncation_is_not_retried_as_a_plan_correction(self):
        incomplete = response(plan())
        incomplete['finish_reason'] = 'length'
        for error in (ConnectionError('HTTP unavailable'), agent.api.IncompleteResponseError(incomplete)):
            call = Mock(side_effect=error)
            with self.subTest(error=type(error).__name__), TemporaryDirectory() as output:
                summary = self.run_loop(output, call)
            self.assertEqual(summary['completed_cases'], 0)
            self.assertEqual(summary['validation_repair_attempts'], 0)
            self.assertEqual(call.call_count, 1)


if __name__ == '__main__':
    unittest.main()
