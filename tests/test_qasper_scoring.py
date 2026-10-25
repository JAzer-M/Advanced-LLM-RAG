"""新评测口径的反例；不读取Gold来决定回答类型，不调用生成服务。"""
import unittest
from evaluation import qasper_scoring as scoring


class QasperScoringTests(unittest.TestCase):
    def test_explicit_chinese_refusal_is_recognized(self):
        self.assertEqual(scoring.answer_for_scoring({'answer': '当前证据不足。'}), ('Unanswerable', 'declined'))

    def test_partial_answer_with_negative_qualifier_is_not_a_refusal(self):
        text = 'The context does not specify every metric; it reports accuracy [1].'
        answer, kind = scoring.answer_for_scoring({'answer': text})
        self.assertEqual(kind, 'answered')
        self.assertIn('accuracy', answer)

    def test_negative_yes_no_answer_is_not_unanswerable(self):
        self.assertEqual(scoring.answer_for_scoring({'answer': 'No.'}), ('No.', 'answered'))

    def test_short_answer_keeps_material_condition(self):
        r = {'answer': 'No, unless the source domain is unchanged [1].\n\nThe passages explain why [1].'}
        self.assertEqual(scoring.answer_for_scoring(r, short=True)[0], 'No, unless the source domain is unchanged.')

    def test_short_and_full_answers_are_separate(self):
        r = {'answer': 'Yes [1].\n\nThe method uses column headings [1].'}
        self.assertEqual(scoring.answer_for_scoring(r, short=True)[0], 'Yes.')
        self.assertIn('column headings', scoring.answer_for_scoring(r)[0])

    def test_failed_result_does_not_turn_into_a_correct_refusal(self):
        self.assertEqual(scoring.answer_for_scoring({'status': 'failed', 'answer': 'Insufficient evidence.'}), ('', 'failed'))

    def test_evidence_whitespace_does_not_change_paragraph_identity(self):
        self.assertEqual(scoring.paragraph_f1(['Loss is negative log-likelihood. '],
                                             ['Loss is negative log-likelihood.']), 1)

    def test_different_evidence_is_not_merged(self):
        self.assertEqual(scoring.paragraph_f1(['Accuracy is 81%.'], ['Accuracy is 95%.']), 0)


if __name__ == '__main__':
    unittest.main()
