# 引用格式回归：合法的 citation 数字别名本地归一化，错误编号仍应暴露。

import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from src.citation_validation import check_citations, repair_citations_once


class CitationAliasTests(unittest.TestCase):
    def registry(self, count):
        return [{'chunk_id': i, 'source': 'fixture.pdf', 'page': 1, 'text': f'Evidence {i}'}
                for i in range(count)]

    def test_captured_p1_aliases_normalize_without_model_call(self):
        capture = json.loads((Path(__file__).parent / 'fixtures/p1_citation_aliases.json')
                             .read_text(encoding='utf-8'))
        generate = Mock(side_effect=AssertionError('No model call needed for a known numeric alias'))
        result = repair_citations_once('query', 'context', capture['answer'],
                                        self.registry(capture['citation_count']), generate)
        self.assertEqual(result['answer'], capture['answer'].replace('[citation:6]', '[6]'))
        self.assertEqual(result['original_answer'], capture['answer'])
        self.assertTrue(result['final_check']['structure_passed'])
        self.assertTrue(result['normalization_applied'])
        generate.assert_not_called()

    def test_mixed_alias_and_valid_marker_do_not_hide_bad_syntax(self):
        check = check_citations('First claim [citation:2]. Second claim [1].', self.registry(2))
        self.assertFalse(check['structure_passed'])
        self.assertIn('citation:2', check['malformed_markers'])

    def test_out_of_range_alias_cannot_be_silently_accepted(self):
        generate = Mock(return_value='{}')
        result = repair_citations_once('q', 'c', 'A claim [citation:99].', self.registry(2), generate)
        self.assertFalse(result['final_check']['structure_passed'])
        self.assertEqual(result['answer'], 'A claim [citation:99].')

    def test_standard_citations_keep_the_same_answer_without_model_call(self):
        generate = Mock(side_effect=AssertionError('No repair needed'))
        result = repair_citations_once('q', 'c', 'Claim [1].', self.registry(1), generate)
        self.assertEqual(result['answer'], 'Claim [1].')
        self.assertEqual(result['status'], 'not_needed')
        generate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
