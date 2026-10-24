"""Scope regressions: keep subject bindings and proposed queries within the question."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import agent
from test_agent_step1 import assessment, cases, inventory, missing, passages, plan, response


class AgentScopeTests(unittest.TestCase):
    def test_requirement_scope_quote_must_name_its_own_subject(self):
        value = plan()
        value['requirements'][0].update(subject='Atlas', question_quote='Nova on Orion')
        with self.assertRaisesRegex(ValueError, 'subject'):
            agent.validate_plan(value, 'Compare Atlas with Nova on Orion.')

    def test_method_name_is_not_a_suffix_of_another_method(self):
        value = plan()
        for name in ('Self-RAG', 'Self‑RAG', 'Self–RAG'):
            value['requirements'][0].update(subject='RAG', question_quote=name)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'subject'):
                agent.validate_plan(value, f'Describe {name}.')

    def test_search_cannot_add_another_methods_dataset_to_target_scope(self):
        requirement = {'id': 'r1', 'subject': 'Atlas', 'need': 'the criterion reported by Atlas',
                       'question_quote': 'the criterion reported by Atlas'}
        value = missing(assessment())
        value['next_action'].update(query='Atlas evaluation criterion on Orion', source='a.pdf')
        with self.assertRaisesRegex(ValueError, 'bound query'):
            agent.validate_assessment(value, [requirement], passages(), inventory())

    def test_distinct_method_scopes_and_chinese_context_remain_valid(self):
        query = 'Compare the criterion reported by Atlas with the criterion used by Nova on Orion.'
        value = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'need': 'the criterion reported by Atlas',
             'question_quote': 'the criterion reported by Atlas'},
            {'id': 'r2', 'subject': 'Nova', 'need': 'the criterion used by Nova on Orion',
             'question_quote': 'the criterion used by Nova on Orion'}]}
        self.assertIs(agent.validate_plan(value, query), value)
        chinese = plan()
        chinese['requirements'][0].update(subject='RAG', need='RAG的评测判据是什么', question_quote='RAG的评测判据是什么')
        self.assertIs(agent.validate_plan(chinese, '请说明RAG的评测判据是什么。'), chinese)

    def test_scope_review_rejection_blocks_an_otherwise_valid_action(self):
        value = assessment()
        value['scope_check'] = {'valid': False, 'reason': '把一个主体的数据集条件转移给另一个主体。'}
        with self.assertRaisesRegex(ValueError, 'scope review failed'):
            agent.validate_assessment(value, plan()['requirements'], passages(), inventory())

    def test_scope_review_must_be_a_real_boolean(self):
        for flag in ('true', 1, None):
            value = assessment(); value['scope_check']['valid'] = flag
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, 'scope review failed'):
                agent.validate_assessment(value, plan()['requirements'], passages(), inventory())

    def test_partial_must_identify_an_actually_supported_part(self):
        value = assessment()
        value['requirements'][0].update(status='partial', supported_part='', gap='仅有主题背景。')
        value['next_action'] = missing(assessment())['next_action']
        with self.assertRaisesRegex(ValueError, 'supported_part'):
            agent.validate_assessment(value, plan()['requirements'], passages(), inventory())

    def test_legitimate_partial_fact_can_still_request_more_evidence(self):
        value = assessment()
        value['requirements'][0].update(status='partial', gap='尚缺该做法的适用条件。')
        value['next_action'] = missing(assessment())['next_action']
        self.assertIs(agent.validate_assessment(value, plan()['requirements'], passages(), inventory()), value)

    def test_missing_cannot_declare_an_established_part(self):
        value = missing(assessment())
        value['requirements'][0]['supported_part'] = '训练背景被当成所问评测规则。'
        with self.assertRaisesRegex(ValueError, 'established supported_part'):
            agent.validate_assessment(value, plan()['requirements'], passages(), inventory())

    def test_search_targets_only_one_unmet_requirement(self):
        value = missing(assessment())
        second = deepcopy(value['requirements'][0]); second['id'] = 'r2'
        value['requirements'].append(second)
        requirements = plan()['requirements']
        second = deepcopy(requirements[0]); second['id'] = 'r2'
        requirements.append(second)
        value['next_action']['requirement_ids'] = ['r1', 'r2']
        with self.assertRaisesRegex(ValueError, 'bound query'):
            agent.validate_assessment(value, requirements, passages(), inventory())

    def test_search_cannot_append_an_unrequested_answer_hint(self):
        value = missing(assessment())
        value['next_action']['query'] += ' exact match or answer inclusion?'
        with self.assertRaisesRegex(ValueError, 'bound query'):
            agent.validate_assessment(value, plan()['requirements'], passages(), inventory())

    def test_scope_rejection_is_saved_without_retry_or_tool_execution(self):
        value = assessment()
        value['scope_check'] = {'valid': False, 'reason': '需求范围超出原题。'}
        call = Mock(side_effect=[response(plan()), response(value)])
        with TemporaryDirectory() as temporary, patch.object(agent.api, 'load_settings', return_value={'model': 'fixture'}):
            first = agent.run_diagnostics(cases(), temporary, {}, call)
            agent.run_diagnostics(cases(), temporary, {}, call)
            record = json.loads((Path(temporary) / 'c0.json').read_text())
            raw = json.loads((Path(temporary) / 'actual_chat_calls.json').read_text())
            self.assertEqual(first['completed_cases'], 0)
            self.assertEqual(first['actions_executed'], 0)
            self.assertIn('scope review failed', record['error'])
            self.assertIn('需求范围超出原题', raw[1]['response']['answer'])
            self.assertEqual(call.call_count, 2)

    def test_operative_need_cannot_expand_an_anchored_clause(self):
        value = plan()
        value['requirements'][0]['need'] = 'A on an unasked benchmark'
        with self.assertRaisesRegex(ValueError, 'bound question excerpt'):
            agent.validate_plan(value, 'Describe A.')

    def test_extraction_does_not_accept_a_free_paraphrase_field(self):
        with self.assertRaisesRegex(ValueError, 'extracted requirement'):
            agent.bind_requirements(plan(), 'Describe A.')

    def test_extracting_asymmetric_comparison_keeps_each_methods_conditions(self):
        query = 'How does the criterion reported by Atlas differ from the criterion used by Nova on Orion?'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': 'the criterion reported by Atlas'},
            {'id': 'r2', 'subject': 'Nova', 'question_quote': 'the criterion used by Nova on Orion'}]}
        result = agent.bind_requirements(proposal, query)
        self.assertNotIn('Orion', agent.search_query(result['requirements'][0]))
        self.assertIn('Orion', agent.search_query(result['requirements'][1]))

    def test_single_paper_pronoun_expands_to_its_unique_named_antecedent(self):
        query = 'What value does Atlas Study use, and how does the paper say it affects accuracy?'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas Study', 'question_quote': 'What value does Atlas Study use'},
            {'id': 'r2', 'subject': 'Atlas Study', 'question_quote': 'how does the paper say it affects accuracy'}]}
        result = agent.bind_requirements(proposal, query)
        need = result['requirements'][1]['need']
        self.assertIn('atlas study', agent.normalize(need))
        self.assertIn(agent.normalize(need), agent.normalize(query))

    def test_pronoun_does_not_expand_across_multiple_declared_subjects(self):
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': 'the paper'},
            {'id': 'r2', 'subject': 'Nova', 'question_quote': 'Nova'}]}
        with self.assertRaisesRegex(ValueError, 'own subject'):
            agent.bind_requirements(proposal, 'Compare Atlas and Nova: describe the paper.')

    def test_comparison_quote_cannot_merge_other_declared_subjects(self):
        query = 'Compare Atlas with Nova on Orion.'
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'Atlas', 'question_quote': query},
            {'id': 'r2', 'subject': 'Nova', 'question_quote': 'Nova on Orion'}]}
        with self.assertRaisesRegex(ValueError, 'another declared subject'):
            agent.bind_requirements(proposal, query)

    def test_optional_reference_source_is_checked_instead_of_ignored(self):
        value = assessment()
        value['requirements'][0]['evidence'][0]['source'] = 'a.pdf'
        self.assertIs(agent.validate_assessment(value, plan()['requirements'], passages(), inventory()), value)
        value['requirements'][0]['evidence'][0]['source'] = 'b.pdf'
        with self.assertRaisesRegex(ValueError, 'source must match'):
            agent.validate_assessment(value, plan()['requirements'], passages(), inventory())

    def scoped_checks(self):
        requirements = [
            {'id': 'r1', 'subject': 'Atlas', 'need': 'the criterion reported by Atlas',
             'question_quote': 'the criterion reported by Atlas'},
            {'id': 'r2', 'subject': 'Nova', 'need': 'the criterion used by Nova on Orion',
             'question_quote': 'the criterion used by Nova on Orion'}]
        value = missing(assessment())
        second = deepcopy(value['requirements'][0]); second['id'] = 'r2'
        value['requirements'].append(second)
        value['next_action']['query'] = agent.search_query(requirements[0])
        return requirements, value

    def test_missing_gap_cannot_transfer_another_subjects_dataset(self):
        requirements, value = self.scoped_checks()
        value['requirements'][0]['gap'] = '缺少 Atlas 在 Orion 上的判据。'
        with self.assertRaisesRegex(ValueError, 'borrows another requirement scope'):
            agent.validate_assessment(value, requirements, passages(), inventory())

    def test_partial_gap_cannot_be_another_requirements_missing_fact(self):
        requirements, value = self.scoped_checks()
        value['requirements'][1].update(status='partial', supported_part='Nova的判据已有证据。',
                                        gap='缺少Atlas的判据，因此无法比较。',
                                        evidence=assessment()['requirements'][0]['evidence'])
        with self.assertRaisesRegex(ValueError, 'borrows another requirement scope'):
            agent.validate_assessment(value, requirements, passages(), inventory())

    def test_factual_checker_receives_bound_requests_without_full_comparison(self):
        requirements, value = self.scoped_checks()
        query = 'Compare the criterion reported by Atlas with the criterion used by Nova on Orion.'
        call = Mock(return_value=response(value))
        agent.assess_evidence(query, {'requirements': requirements}, passages(), inventory(), call)
        prompt = call.call_args.args[0]
        data = json.loads(prompt.split('INPUT DATA:\n', 1)[1])
        self.assertNotIn('query', data)
        self.assertNotIn(query, prompt)
        self.assertEqual(data['requirements'], requirements)


if __name__ == '__main__':
    unittest.main()
