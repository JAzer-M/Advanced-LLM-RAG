import unittest

from evaluation.metrics import (
    normalized_precision_at_k,
    overall_normalized_precision_at_k,
    precision_at_k,
    recall_at_k,
)


class NormalizedPrecisionTests(unittest.TestCase):
    def test_one_gold_can_be_complete_with_low_raw_precision(self):
        self.assertEqual(precision_at_k([7], [7], 10), 0.1)
        self.assertEqual(normalized_precision_at_k([7], [7], 10), 1)

    def test_gold_larger_than_budget_is_capped_without_changing_recall(self):
        self.assertEqual(normalized_precision_at_k([1, 2], [1, 2, 3, 4], 2), 1)
        self.assertEqual(recall_at_k([1, 2], [1, 2, 3, 4], 2), 0.5)

    def test_overall_uses_total_attainable_gold_not_mean_question_scores(self):
        cases = [([1], [1]), ([2], [2, 3, 4, 5])]
        self.assertEqual(overall_normalized_precision_at_k(cases, 10), 0.4)
        per_question_mean = sum(normalized_precision_at_k(r, g, 10) for r, g in cases) / 2
        self.assertEqual(per_question_mean, 0.625)

    def test_duplicate_ids_and_top_k_cutoff_do_not_add_hits(self):
        self.assertEqual(normalized_precision_at_k([1, 1, 2, 3], [1, 1, 2, 3], 3), 2 / 3)

    def test_no_gold_is_undefined_and_skipped_in_aggregate(self):
        self.assertIsNone(normalized_precision_at_k([1], [], 10))
        self.assertIsNone(overall_normalized_precision_at_k([], 10))
        self.assertIsNone(overall_normalized_precision_at_k([([1], [])], 10))
        self.assertEqual(overall_normalized_precision_at_k([([1], []), ([2], [2])], 10), 1)

    def test_no_hits_stays_zero(self):
        self.assertEqual(normalized_precision_at_k([], [1, 2], 10), 0)

    def test_nonpositive_budget_is_rejected(self):
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    normalized_precision_at_k([], [], k)
                with self.assertRaises(ValueError):
                    overall_normalized_precision_at_k([], k)

    def test_live_summary_preserves_original_metrics_and_gold_weighting(self):
        from evaluation.run_evaluation import evaluate_retrieval, summarize_results

        cases = [([1], [1]), ([2], [2, 3, 4, 5])]
        summary = summarize_results(cases, 10)
        self.assertEqual(summary['normalized_precision'], 0.4)
        self.assertEqual(summary['precision'], 0.1)
        self.assertEqual(summary['recall'], 0.625)
        self.assertEqual(summary['map'], 0.625)
        self.assertEqual(summary['mrr'], 1)
        self.assertEqual(evaluate_retrieval([2], [2, 3, 4, 5], 10)['normalized_precision'], 0.25)


if __name__ == '__main__':
    unittest.main()
