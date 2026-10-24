"""跨方法比较不能投影成“单个方法之间的区别”；使用真实失败规划作回归。"""
from copy import deepcopy
import unittest

import agent


class ComparisonIntentTests(unittest.TestCase):
    def proposal(self, query, subjects=('Atlas', 'Nova')):
        return {'requirements': [{'id': f'r{i}', 'subject': subject, 'question_quote': query}
                                 for i, subject in enumerate(subjects, 1)]}

    def test_actual_user_trace_keeps_both_objects_of_the_comparison(self):
        # 逐项复现用户运行中的抽取，不依赖本机临时运行目录。
        query = 'what is the difference between VGG and RAG?'
        proposal = self.proposal(query, ('VGG', 'RAG'))
        bound = agent.bind_requirements(proposal, query)
        for row in bound['requirements']:
            self.assertEqual(row['question_quote'], query)
            self.assertTrue(agent.names_subject(row['subject'], row['need']))
            other = 'RAG' if row['subject'] == 'VGG' else 'VGG'
            self.assertFalse(agent.names_subject(other, row['need']))
            self.assertNotIn('difference between vgg?', row['need'])
            self.assertNotIn('difference between rag?', row['need'])

    def test_symmetric_comparisons_retain_the_relation_and_requested_aspect(self):
        for query in ('What is the difference between Atlas and Nova?',
                      'How do Atlas and Nova differ in their filter sizes?',
                      'Compare Atlas and Nova on representation.',
                      'Atlas 和 Nova 有什么区别？',
                      'Atlas 与 Nova 在表示方式上有何区别？'):
            with self.subTest(query=query):
                rows = agent.bind_requirements(self.proposal(query), query)['requirements']
                for row in rows:
                    self.assertEqual(row['question_quote'], query)
                    self.assertTrue(agent.names_subject(row['subject'], row['need']))
                    other = 'Nova' if row['subject'] == 'Atlas' else 'Atlas'
                    self.assertFalse(agent.names_subject(other, row['need']))
                    self.assertNotRegex(row['need'], r'difference between (?:atlas|nova)\?')
                    for aspect in ('filter sizes', 'representation', '表示方式'):
                        if aspect in query:
                            self.assertIn(aspect, row['need'])

    def test_corrupted_one_sided_comparative_need_is_rejected(self):
        query = 'What is the difference between Atlas and Nova?'
        bound = agent.bind_requirements(self.proposal(query), query)
        bad = deepcopy(bound)
        bad['requirements'][0]['need'] = 'what is the difference between atlas?'
        with self.assertRaisesRegex(ValueError, 'bound question excerpt'):
            agent.validate_plan(bad, query)

    def test_noncomparative_shared_predicate_still_isolates_subjects(self):
        query = 'What do Atlas and Nova report about normalization?'
        rows = agent.bind_requirements(self.proposal(query), query)['requirements']
        self.assertFalse(agent.names_subject('Nova', rows[0]['need']))
        self.assertFalse(agent.names_subject('Atlas', rows[1]['need']))
        self.assertTrue(all('report about normalization' in row['need'] for row in rows))

    def test_asymmetric_later_conditions_still_cannot_be_merged(self):
        query = 'How do Atlas and Nova differ, and what costs does Nova report on Orion?'
        with self.assertRaisesRegex(ValueError, 'another declared subject'):
            agent.bind_requirements(self.proposal(query), query)


if __name__ == '__main__':
    unittest.main()
