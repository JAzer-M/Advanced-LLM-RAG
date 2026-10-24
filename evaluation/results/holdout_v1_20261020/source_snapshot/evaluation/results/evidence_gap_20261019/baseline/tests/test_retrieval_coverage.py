from contextlib import redirect_stdout
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import main as pipeline


class RetrievalCoverageTests(unittest.TestCase):
    def run_pipeline(self, best_ids, duplicate_passage=False):
        chunks = [{'chunk_id': i, 'text': f'Entity evidence passage {i}.',
                   'source': f'paper-{i % 2}.pdf', 'page': i + 1,
                   'title': 'Fixture paper', 'section': 'Methods'} for i in range(12)]
        if duplicate_passage:
            chunks[11] = {**chunks[10], 'chunk_id': 11}
        queries = [f'Sub-question {i}' for i in range(len(best_ids))]
        targets = dict(zip(queries, best_ids))

        def retrieve(**kwargs):
            if duplicate_passage and kwargs['query'] in targets:
                return [chunks[11], *chunks[:11]]
            return chunks

        def rank(query, candidates, model, top_k, include_source):
            ordered = list(candidates)
            if query not in targets:
                ordered.sort(key=lambda c: c['chunk_id'])
            if query in targets:
                target = chunks[targets[query]]
                key = lambda c: (c['source'], c['page'], c['text'])
                ordered.sort(key=lambda c: key(c) != key(target))
            return [{**c, 'rerank_score': 1 / (i + 1)}
                    for i, c in enumerate(ordered[:top_k])]

        with redirect_stdout(io.StringIO()), \
                patch.object(pipeline, 'load_settings', return_value={'model': 'fixture'}), \
                patch.object(pipeline, 'load_knowledge_base', return_value=(
                    SimpleNamespace(ntotal=12, d=3), chunks, {'version': 'fixture'})), \
                patch.object(pipeline, 'load_embedding_model', return_value=object()), \
                patch.object(pipeline, 'CrossEncoder', return_value=object()), \
                patch.object(pipeline, 'decompose_query', return_value={
                    'needs_decomposition': bool(queries), 'sub_queries': queries}), \
                patch.object(pipeline, 'build_bm25_index', return_value=object()), \
                patch.object(pipeline, 'retrieve', side_effect=retrieve), \
                patch.object(pipeline, 'retrieve_bm25', return_value=[]), \
                patch.object(pipeline, 'reciprocal_rank_fusion',
                             side_effect=lambda dense_results, **kwargs: dense_results), \
                patch('src.reranker.rerank_results', side_effect=rank), \
                patch.object(pipeline, 'generate_final_answer', return_value='Fixture evidence [1].'):
            return pipeline.main('Compare the entities and their methods.', kb_version='fixture')

    def test_each_subquestion_keeps_its_best_evidence_within_top10_budget(self):
        result = self.run_pipeline([0, 1, 10, 11])
        self.assertEqual(len(result['selected_ids']), 10)
        self.assertTrue({0, 1, 10, 11} <= set(result['selected_ids']))
        self.assertEqual(result['selected_ids'], [0, 1, 2, 3, 4, 5, 6, 7, 10, 11])

    def test_no_decomposition_preserves_original_global_ranking(self):
        result = self.run_pipeline([])
        self.assertEqual(result['selected_ids'], list(range(10)))

    def test_shared_best_passage_is_not_duplicated(self):
        result = self.run_pipeline([11, 11, 11, 11])
        self.assertEqual(result['selected_ids'].count(11), 1)
        self.assertEqual(len(set(result['selected_ids'])), 10)

    def test_duplicate_passage_ids_map_to_the_canonical_candidate(self):
        result = self.run_pipeline([11, 11], duplicate_passage=True)
        self.assertEqual(len(result['selected_ids']), 10)
        self.assertIn(10, result['selected_ids'])
        self.assertNotIn(11, result['selected_ids'])


if __name__ == '__main__':
    unittest.main()
