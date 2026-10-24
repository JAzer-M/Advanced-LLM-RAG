from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

import evaluation.run_evaluation as evaluation
from src.reranker import select_evidence


class EvaluationAlignmentTests(unittest.TestCase):
    def test_evaluation_preserves_each_subquestion_evidence_within_budget(self):
        chunks = [{'chunk_id': i, 'text': f'Evidence passage {i}.', 'source': 'paper.pdf',
                   'page': i + 1, 'title': 'Fixture', 'section': 'Methods'} for i in range(12)]
        targets = {'Subquestion A': 0, 'Subquestion B': 1,
                   'Subquestion C': 10, 'Subquestion D': 11}

        class Model:
            def predict(self, pairs):
                scores = []
                for query, text in pairs:
                    cid = int(re.search(r'passage (\d+)', text).group(1))
                    scores.append(1000 if targets.get(query) == cid else 100 - cid)
                return scores

        with redirect_stdout(io.StringIO()), patch.object(evaluation, 'FINAL_K', 10), \
                patch.object(evaluation, 'retrieve_two_ways', return_value=(chunks, [])):
            _, ranked, _, _ = evaluation.decomposition_retrieve_and_rerank(
                'Compare the entities.', {'needs_decomposition': True,
                                         'sub_queries': list(targets)},
                chunks, object(), object(), chunks, object(), Model())
        ids = evaluation.get_result_ids(ranked)
        self.assertEqual(ids, [0, 1, 2, 3, 4, 5, 6, 7, 10, 11])
        self.assertEqual(len(ids), 10)

    def test_top_k_sweep_reuses_auxiliary_and_offline_replay_matches(self):
        chunks = [{'chunk_id': i, 'text': f'Evidence passage {i}.', 'source': 'paper.pdf',
                   'page': i + 1, 'title': 'Fixture', 'section': 'Methods'} for i in range(4)]

        class Model:
            def predict(self, pairs):
                return list(range(len(pairs), 0, -1))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            questions = root / 'questions.json'
            questions.write_text(json.dumps([{'id': 'fixture', 'question': 'Locate the evidence.',
                'gold_evidence': [{'source': 'paper.pdf', 'page': 1, 'quote': 'Evidence passage 0.'}]}]))
            chunks_path = root / 'chunks.json'
            chunks_path.write_text(json.dumps(chunks))
            kb = {'version': 'fixture', 'index_path': str(chunks_path),
                  'chunks_path': str(chunks_path), 'manifest_path': None}
            argv = ['run_evaluation', '--questions', str(questions), '--top-k', '5', '10', '20']
            with redirect_stdout(io.StringIO()), \
                    patch.object(evaluation, 'load_knowledge_base', return_value=(object(), chunks, kb)), \
                    patch.object(evaluation, 'load_embedding_model', return_value=object()), \
                    patch.object(evaluation, 'build_bm25_index', return_value=object()), \
                    patch.object(evaluation, 'CrossEncoder', return_value=Model()), \
                    patch.object(evaluation, 'retrieve_two_ways', return_value=(chunks, [])), \
                    patch.object(evaluation, 'decompose_query', return_value={
                        'needs_decomposition': False, 'sub_queries': []}) as decompose, \
                    patch.object(evaluation, 'rewrite_query', return_value='Locate the evidence.') as rewrite:
                with patch.object(sys, 'argv', argv + ['--output-dir', str(root / 'fresh')]):
                    evaluation.main()
                decompose.assert_called_once_with('Locate the evidence.')
                rewrite.assert_called_once_with('Locate the evidence.')
                decompose.reset_mock()
                rewrite.reset_mock()
                with patch.object(sys, 'argv', argv + ['--output-dir', str(root / 'replay'),
                        '--auxiliary-cache', str(root / 'fresh/auxiliary.json')]), \
                        patch.object(evaluation.api, 'chat_completion', side_effect=AssertionError('API forbidden')):
                    evaluation.main()
                decompose.assert_not_called()
                rewrite.assert_not_called()
            fresh = json.loads((root / 'fresh/results.json').read_text())
            replay = json.loads((root / 'replay/results.json').read_text())
            self.assertEqual(fresh['metrics'], replay['metrics'])
            self.assertEqual(set(fresh['metrics']), {'5', '10', '20'})
            self.assertEqual(fresh['metrics']['10']['Dense']['recall'], 1)
            self.assertEqual(fresh['metrics']['10']['Dense']['precision'], 0.1)
            self.assertEqual(replay['api_call_count'], 0)

    def test_wrong_query_cache_is_rejected_without_api(self):
        with patch.object(evaluation.api, 'chat_completion', side_effect=AssertionError('API forbidden')):
            with self.assertRaisesRegex(ValueError, 'does not match'):
                evaluation.auxiliary_queries({'id': 'p1', 'question': 'English query'},
                    {'p1': {'query': 'Different query'}}, [], None)

    def test_selection_respects_budgets_and_global_order(self):
        ranking = [{'chunk_id': i} for i in range(30)]
        evidence = [{'top_ids': [25, 27, 28]}, {'top_ids': [26, 28, 29]}]
        for k in (1, 5, 10, 20):
            ids = [c['chunk_id'] for c in select_evidence(ranking, evidence, k)]
            self.assertEqual(len(ids), k)
            self.assertEqual(ids, sorted(set(ids)))
            if k >= 2:
                self.assertTrue({25, 26} <= set(ids))

    def test_original_retrieval_first_hit_survives_reranker_disagreement(self):
        ranking = [{'chunk_id': i} for i in range(30)]
        without_anchor = select_evidence(ranking, [], 10)
        with_anchor = select_evidence(ranking, [], 10, [19])
        self.assertNotIn(19, [c['chunk_id'] for c in without_anchor])
        self.assertEqual([c['chunk_id'] for c in with_anchor], [*range(9), 19])


if __name__ == '__main__':
    unittest.main()
