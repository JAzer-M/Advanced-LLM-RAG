"""真实PDF断行引文回归：仅兼容排版，不允许改数字、否定词或词内连字符。"""
import unittest
from src.citation_validation import has_source_quote


class QuoteLayoutTests(unittest.TestCase):
    def test_wrapped_word_can_be_copied_without_layout_hyphen(self):
        self.assertTrue(has_source_quote('The classical model achieved 0.80.',
                                         'The classi- cal model achieved 0.80.'))

    def test_different_wrap_positions_are_equivalent(self):
        self.assertTrue(has_source_quote('Domain classifi- cation improves.',
                                         'Domain classi- fication improves.'))

    def test_changed_number_is_still_rejected(self):
        self.assertFalse(has_source_quote('The classical model achieved 0.81.',
                                          'The classi- cal model achieved 0.80.'))

    def test_inserted_negation_is_still_rejected(self):
        self.assertFalse(has_source_quote('The model does not improve classification.',
                                          'The model does improve classi- fication.'))

    def test_intrinsic_unwrapped_hyphen_is_not_removed(self):
        self.assertFalse(has_source_quote('We use fine tuning.', 'We use fine-tuning.'))


if __name__ == '__main__':
    unittest.main()
