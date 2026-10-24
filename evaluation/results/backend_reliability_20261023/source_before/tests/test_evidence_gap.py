# 规则化补查回归：来源识别、先过滤来源、候选加深、提前停止和预算。
# 替身检索/重排让结果可预测；这些用例不验证自然语言事实支持。

import unittest
from unittest.mock import patch

from src.evidence_gap import complete_evidence, complete_evidence_once, named_sources, plan_evidence_gap


def passage(cid, source, title):
    return {'chunk_id': cid, 'source': source, 'title': title,
            'page': cid + 1, 'section': 'Methods', 'text': f'Evidence {cid}.',
            'rerank_score': 100 - cid}


class EvidenceGapTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [passage(i, 'alpha.pdf', 'Alpha: Retrieval') for i in range(8)]
        self.chunks += [passage(i, 'beta.pdf', 'Beta: Search') for i in range(8, 16)]

    def test_paper_names_do_not_match_inside_other_method_names(self):
        chunks = [passage(0, 'a.pdf', 'Retrieval-Augmented Generation for NLP'),
                  passage(1, 'b.pdf', 'Self-RAG: Learning to Retrieve'),
                  passage(2, 'c.pdf', 'Corrective Retrieval Augmented Generation')]
        self.assertEqual(named_sources('Compare Self-RAG and CRAG.', chunks), ['b.pdf', 'c.pdf'])
        self.assertEqual(named_sources('Compare RAG and CRAG.', chunks), ['a.pdf', 'c.pdf'])

    def test_diagnostics_separate_wrong_source_and_excluded_candidates(self):
        selected = self.chunks[:5] + self.chunks[10:15]
        local = [{'query': 'What does Beta store?', 'top_ids': [0, 1, 2]}]
        plan = plan_evidence_gap('Compare Alpha and Beta.', self.chunks, local,
                                 selected, self.chunks, 10)
        task = next(t for t in plan['tasks'] if t['source'] == 'beta.pdf')
        self.assertEqual(task['source_matched_top_ids'], [])
        self.assertTrue(task['needs_retrieval'])
        self.assertEqual(task['excluded_global_ids'], [8, 9])

    def test_single_paper_keeps_baseline_without_supplement_calls(self):
        with patch('src.evidence_gap.retrieve') as dense:
            results, trace = complete_evidence_once('Explain Alpha.', self.chunks, [], [],
                object(), object(), self.chunks, object(), object())
        self.assertEqual([c['chunk_id'] for c in results], list(range(10)))
        dense.assert_not_called()
        self.assertEqual(trace['rounds'], 0)

    def test_scoped_supplement_recovers_excluded_paper_and_stops_after_one_round(self):
        # Initial Alpha task hits the wrong paper; the actual search supplies Alpha evidence.
        initial = self.chunks[8:]
        local = [{'query': 'What does Alpha store?', 'top_ids': [8, 9, 10]},
                 {'query': 'What does Beta store?', 'top_ids': [8, 9, 10]}]

        def rank(query, candidates, model, top_k, include_source=True):
            return [{**c, 'rerank_score': 100 - c['chunk_id']}
                    for c in sorted(candidates, key=lambda c: c['chunk_id'])[:top_k]]

        with patch('src.evidence_gap.retrieve', return_value=self.chunks) as dense, \
                patch('src.evidence_gap.retrieve_bm25', return_value=self.chunks), \
                patch('src.evidence_gap.rerank_results', side_effect=rank):
            selected, trace = complete_evidence_once('Compare Alpha and Beta.', initial,
                local, [8], object(), object(), self.chunks, object(), object())
        self.assertEqual(trace['rounds'], 1)
        self.assertEqual(trace['supplement_queries'], 1)
        self.assertTrue({'alpha.pdf', 'beta.pdf'} <= {c['source'] for c in selected})
        self.assertEqual(len({c['chunk_id'] for c in selected}), 10)
        self.assertTrue(all(c['chunk_id'] in trace['merged_candidate_ids'] for c in selected))
        dense.assert_called_once()
        self.assertEqual(trace['stop_reason'], 'single_round_budget_exhausted')

    def test_no_gold_fields_enter_the_completion_interface(self):
        import inspect
        self.assertFalse({'gold_ids', 'gold_evidence', 'reference_points'} &
                         set(inspect.signature(complete_evidence_once).parameters))

    def test_existing_candidates_can_be_repaired_without_another_search(self):
        local = [{'query': 'What does Alpha store?', 'top_ids': [7, 6, 5]},
                 {'query': 'What does Beta store?', 'top_ids': [8, 9, 10]}]
        with patch('src.evidence_gap.retrieve') as dense, \
                patch('src.evidence_gap.rerank_results',
                      side_effect=lambda query, candidates, model, top_k, **kwargs: candidates[:top_k]):
            selected, trace = complete_evidence_once('Compare Alpha and Beta.', self.chunks,
                local, [], object(), object(), self.chunks, object(), object())
        dense.assert_not_called()
        self.assertEqual(trace['rounds'], 0)
        self.assertEqual(trace['stop_reason'], 'selection_repaired_without_search')
        self.assertTrue({5, 6, 7, 8, 9, 10} <= {c['chunk_id'] for c in selected})

    def test_task_limit_is_explicit_and_does_not_recurse(self):
        local = [{'query': f'Compare Alpha and its property {i}', 'top_ids': [8, 9, 10]}
                 for i in range(6)]
        plan = plan_evidence_gap('Compare Alpha and Beta.', self.chunks, local,
                                 self.chunks[:10], self.chunks, 10)
        self.assertEqual(len(plan['tasks']), 4)
        self.assertEqual(plan['truncated_tasks'], 3)

    def test_cross_paper_question_without_decomposition_gets_one_task_per_source(self):
        plan = plan_evidence_gap('Compare Alpha and Beta.', self.chunks, [],
                                 self.chunks[:10], self.chunks, 10)
        self.assertEqual([t['source'] for t in plan['tasks']], ['alpha.pdf', 'beta.pdf'])
        self.assertTrue(all(t['needs_retrieval'] for t in plan['tasks']))

    def test_three_passes_deepen_candidates_and_keep_the_same_final_budget(self):
        chunks = [passage(i, 'alpha.pdf', 'Alpha: Retrieval') for i in range(12)]
        chunks += [passage(i, 'beta.pdf', 'Beta: Search') for i in range(12, 24)]
        local = [{'query': 'What does Alpha store?', 'top_ids': [12, 13, 14]},
                 {'query': 'What does Beta store?', 'top_ids': [0, 1, 2]}]
        def rank(query, candidates, model, top_k, **kwargs):
            return [{**c, 'rerank_score': 100 - c['chunk_id']} for c in candidates[:top_k]]
        with patch('src.evidence_gap.retrieve', return_value=chunks), \
                patch('src.evidence_gap.retrieve_bm25', return_value=chunks), \
                patch('src.evidence_gap.rerank_results', side_effect=rank):
            selected, trace = complete_evidence('Compare Alpha and Beta.', [chunks[12]],
                local, [], object(), object(), chunks, object(), object(),
                candidate_k=2, max_rounds=3)
        self.assertEqual([r['candidate_depth'] for r in trace['round_history']], [2, 4, 6])
        self.assertEqual(trace['rounds'], 3)
        self.assertEqual(len(selected), 10)
        self.assertEqual(len({c['chunk_id'] for c in selected}), 10)
        self.assertTrue(all(r['new_candidate_ids'] for r in trace['round_history']))

    def test_no_new_candidates_stops_before_the_third_pass(self):
        local = [{'query': 'What does Alpha store?', 'top_ids': [8, 9, 10]},
                 {'query': 'What does Beta store?', 'top_ids': [0, 1, 2]}]
        def rank(query, candidates, model, top_k, **kwargs):
            return [{**c, 'rerank_score': 100 - c['chunk_id']} for c in candidates[:top_k]]
        with patch('src.evidence_gap.retrieve', return_value=self.chunks) as dense, \
                patch('src.evidence_gap.retrieve_bm25', return_value=self.chunks), \
                patch('src.evidence_gap.rerank_results', side_effect=rank):
            _, trace = complete_evidence('Compare Alpha and Beta.', self.chunks, local,
                [], object(), object(), self.chunks, object(), object(), candidate_k=2, max_rounds=3)
        self.assertEqual(trace['completed_passes'], 2)
        self.assertEqual(trace['stop_reason'], 'no_new_candidates')
        self.assertEqual(dense.call_count, 4)

    def test_repeated_effective_depth_does_not_search_again(self):
        local = [{'query': 'What does Alpha store?', 'top_ids': [8, 9, 10]},
                 {'query': 'What does Beta store?', 'top_ids': [0, 1, 2]}]
        def rank(query, candidates, model, top_k, **kwargs):
            return [{**c, 'rerank_score': 100 - c['chunk_id']} for c in candidates[:top_k]]
        with patch('src.evidence_gap.retrieve', return_value=self.chunks) as dense, \
                patch('src.evidence_gap.retrieve_bm25', return_value=self.chunks), \
                patch('src.evidence_gap.rerank_results', side_effect=rank):
            _, trace = complete_evidence('Compare Alpha and Beta.', self.chunks[8:], local,
                [], object(), object(), self.chunks, object(), object(), max_rounds=3)
        self.assertEqual(dense.call_count, 2)
        self.assertEqual(trace['stop_reason'], 'repeated_search_plan')

    def test_invalid_round_budget_is_rejected(self):
        for cap in (0, 4):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                complete_evidence('Compare Alpha and Beta.', self.chunks, [], [],
                    object(), object(), self.chunks, object(), object(), max_rounds=cap)


if __name__ == '__main__':
    unittest.main()
