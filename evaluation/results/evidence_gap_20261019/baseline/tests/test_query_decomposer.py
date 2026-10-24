import json
from pathlib import Path
import unittest
from unittest.mock import patch

from src.query_decomposer import decompose_query


class QueryDecomposerTests(unittest.TestCase):
    def evaluate(self, payload):
        response = payload if isinstance(payload, str) else json.dumps(payload)
        with patch('llm.generate_answer', return_value=response) as generate:
            actual = decompose_query('Compare the named methods and their scoring.')
        generate.assert_called_once()
        return actual

    def test_captured_response_preserves_all_four_subqueries(self):
        capture = json.loads((Path(__file__).parent / 'fixtures/p6_four_subqueries.json')
                             .read_text(encoding='utf-8'))
        expected = json.loads(capture['response'])
        with patch('llm.generate_answer', return_value=capture['response']) as generate:
            actual = decompose_query(capture['query'])
        self.assertTrue(actual['needs_decomposition'])
        self.assertEqual(actual['sub_queries'], expected['sub_queries'])
        generate.assert_called_once()

    def test_two_to_four_subqueries_are_preserved(self):
        for count in (2, 3, 4):
            with self.subTest(count=count):
                queries = [f'Information need {i}' for i in range(count)]
                actual = self.evaluate({'needs_decomposition': True, 'sub_queries': queries})
                self.assertEqual(actual['sub_queries'], queries)
                self.assertEqual(actual['status'], 'accepted')

    def test_duplicates_and_surrounding_spaces_do_not_waste_retrieval(self):
        actual = self.evaluate({'needs_decomposition': True,
                                'sub_queries': [' First entity? ', 'Second entity?', 'First entity?']})
        self.assertEqual(actual['sub_queries'], ['First entity?', 'Second entity?'])
        self.assertEqual(actual['proposed_count'], 3)

    def test_invalid_counts_have_visible_rejection_and_no_queries(self):
        for queries in ([], ['one'], ['same', ' same '], ['a', 'b', 'c', 'd', 'e']):
            with self.subTest(queries=queries):
                actual = self.evaluate({'needs_decomposition': True, 'sub_queries': queries})
                self.assertFalse(actual['needs_decomposition'])
                self.assertEqual(actual['sub_queries'], [])
                self.assertEqual(actual['status'], 'rejected')
                self.assertEqual(actual['reason'], 'sub_query_count_out_of_range')

    def test_invalid_entries_reject_the_whole_plan_with_reason(self):
        for queries in (['first', ' '], ['first', 2], ['first', None]):
            with self.subTest(queries=queries):
                actual = self.evaluate({'needs_decomposition': True, 'sub_queries': queries})
                self.assertEqual(actual['sub_queries'], [])
                self.assertEqual(actual['reason'], 'invalid_sub_query')

    def test_bad_json_and_schema_are_distinct_from_not_needed(self):
        cases = [('not JSON', 'invalid_json'),
                 ([], 'not_an_object'),
                 ({'needs_decomposition': 'true', 'sub_queries': []},
                  'needs_decomposition_not_boolean'),
                 ({'needs_decomposition': True, 'sub_queries': 'a, b'},
                  'sub_queries_not_list'),
                 ({'needs_decomposition': False, 'sub_queries': ['a']},
                  'not_needed_with_sub_queries')]
        for payload, reason in cases:
            with self.subTest(payload=payload):
                actual = self.evaluate(payload)
                self.assertEqual(actual['status'], 'rejected')
                self.assertEqual(actual['reason'], reason)
                self.assertFalse(actual['needs_decomposition'])

    def test_valid_single_need_is_not_needed(self):
        actual = self.evaluate({'needs_decomposition': False, 'sub_queries': []})
        self.assertEqual(actual['status'], 'not_needed')
        self.assertEqual(actual['sub_queries'], [])

    def test_api_failure_propagates_without_retry(self):
        with patch('llm.generate_answer', side_effect=RuntimeError('fixture API failure')) as generate:
            with self.assertRaisesRegex(RuntimeError, 'fixture API failure'):
                decompose_query('A question')
        generate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
