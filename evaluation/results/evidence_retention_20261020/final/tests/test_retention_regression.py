from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import evaluation.run_evaluation as evaluation
from src.evidence_gap import complete_evidence
from src.reranker import rerank_results, select_evidence


def passages(count):
    return [{'chunk_id': i, 'text': f'Evidence passage {i}.',
             'source': 'alpha.pdf' if i < 12 else 'beta.pdf', 'page': i + 1,
             'title': 'Alpha: Retrieval' if i < 12 else 'Beta: Search', 'section': None,
             'rerank_score': 100 - i} for i in range(count)]


class RankedModel:
    def predict(self, pairs):
        return [100 - int(re.search(r'passage (\d+)', text).group(1)) for _, text in pairs]


class RetentionRegressionTests(unittest.TestCase):
    def test_real_main_preserves_pre_augmentation_anchor(self):
        import main as pipeline
        chunks = passages(12)
        original = [chunks[10], *chunks[:10], chunks[11]]

        def dense(*args, **kwargs):
            return original if kwargs['query'] == 'Original question' else [chunks[11]]

        def context(all_chunks, selected):
            return 'Fixture context', {'citation_registry': selected}

        with redirect_stdout(io.StringIO()), \
                patch.object(pipeline, 'load_settings', return_value={'model': 'fixture'}), \
                patch.object(pipeline, 'load_knowledge_base', return_value=(
                    SimpleNamespace(ntotal=12, d=384), chunks, {'version': 'fixture'})), \
                patch.object(pipeline, 'load_embedding_model', return_value=object()), \
                patch.object(pipeline, 'build_bm25_index', return_value=object()), \
                patch.object(pipeline, 'CrossEncoder', return_value=RankedModel()), \
                patch.object(pipeline, 'decompose_query', return_value={
                    'needs_decomposition': False, 'sub_queries': []}), \
                patch.object(pipeline, 'rewrite_query', return_value='Rewritten query'), \
                patch.object(pipeline, 'generate_hypothetical_document', return_value='Synthetic retrieval text'), \
                patch.object(pipeline, 'retrieve', side_effect=dense), \
                patch.object(pipeline, 'retrieve_bm25', side_effect=lambda **kw:
                    original if kw['query'] == 'Original question' else [chunks[11]]), \
                patch.object(pipeline, 'build_evidence_context', side_effect=context), \
                patch.object(pipeline, 'render_complete', return_value={'answer': 'Fixture'}), \
                patch.object(pipeline, 'generate_final_answer', return_value='Supported answer [1].'), \
                patch.multiple(pipeline, USE_MULTI_QUERY=True, USE_HYDE=True, RERANK_TOP_K=10):
            result = pipeline.main('Original question', complete_evidence=False)
        self.assertEqual(result['retrieval_diagnostics']['retrieval_anchor_ids'], [10])
        self.assertIn(10, result['selected_ids'])

    def test_ablation_preserves_original_anchor_in_every_query_mode(self):
        chunks = passages(12)
        original = [chunks[10], *chunks[:10], chunks[11]]
        ranking = rerank_results('Original question', original, RankedModel(), top_k=12)
        with patch.object(evaluation, 'FINAL_K', 10), \
                patch.object(evaluation, 'retrieve_two_ways', return_value=([chunks[11]], [chunks[11]])), \
                patch.object(evaluation, 'retrieve', return_value=[chunks[11]]):
            methods, traces = evaluation.evaluate_query_modes(
                'Original question', {'rewritten_query': 'Rewrite', 'hypothetical_document': 'Synthetic'},
                original, original, original, ranking, [], [], None, [],
                object(), object(), chunks, object(), RankedModel())
        self.assertNotEqual(traces['both']['rrf_ids'][0], 10)
        for mode in ['base', 'rewrite', 'hyde', 'both']:
            self.assertEqual(traces[mode]['retrieval_anchor_ids'], [10])
            self.assertIn(10, methods[f'Pipeline {mode} (0 rounds)'])

    def test_completion_retains_selected_local_top3_not_only_first_hits(self):
        chunks = passages(24)
        local = [{'query': 'What does Alpha store?', 'top_ids': [7, 8, 9]},
                 {'query': 'What does Beta store?', 'top_ids': [18, 19, 20]}]
        for k in [10, 20]:
            with self.subTest(top_k=k), \
                    patch('src.evidence_gap.rerank_results', side_effect=lambda query, candidates, model,
                        top_k, **kw: sorted(candidates, key=lambda c: c['chunk_id'])[:top_k]), \
                    patch('src.evidence_gap.retrieve') as fetch:
                before = select_evidence(chunks, local, k, [0])
                selected, trace = complete_evidence('Compare Alpha and Beta.', chunks, local, [0],
                    object(), object(), chunks, object(), object(), top_k=k, max_rounds=1)
                retained = {cid for item in local for cid in item['top_ids']} & {c['chunk_id'] for c in before}
                self.assertTrue(retained <= {c['chunk_id'] for c in selected})
                self.assertEqual(len(selected), k)
                self.assertEqual(set(trace['retained_local_ids']), retained)
                fetch.assert_not_called()

    def test_completion_k10_and_k20_are_selected_independently(self):
        chunks = passages(30)
        original = [chunks[19], *chunks[:19], *chunks[20:]]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            qpath, cpath = root / 'questions.json', root / 'chunks.json'
            qpath.write_text(json.dumps([{'id': 'fixture', 'question': 'Locate evidence.',
                'gold_evidence': [{'source': chunks[19]['source'], 'page': 20, 'quote': 'Evidence passage 19.'}]}]))
            cpath.write_text(json.dumps(chunks))
            kb = {'version': 'fixture', 'index_path': str(cpath), 'chunks_path': str(cpath), 'manifest_path': None}
            with redirect_stdout(io.StringIO()), \
                    patch.object(sys, 'argv', ['run_evaluation', '--questions', str(qpath), '--top-k', '10', '20',
                        '--candidate-k', '120', '--no-auxiliary', '--complete-evidence', '--completion-rounds', '2',
                        '--output-dir', str(root / 'output')]), \
                    patch.object(evaluation, 'load_knowledge_base', return_value=(object(), chunks, kb)), \
                    patch.object(evaluation, 'load_embedding_model', return_value=object()), \
                    patch.object(evaluation, 'build_bm25_index', return_value=object()), \
                    patch.object(evaluation, 'CrossEncoder', return_value=RankedModel()), \
                    patch.object(evaluation, 'retrieve_two_ways', return_value=(original, [])), \
                    patch.object(evaluation.api, 'chat_completion', side_effect=AssertionError('API forbidden')):
                evaluation.main()
            report = json.loads((root / 'output/results.json').read_text())
            row = report['questions'][0]
            method = 'Evidence Completion (up to 2 rounds)'
            ten = row['metrics_by_k']['10'][method]['retrieved_ids']
            twenty = row['metrics_by_k']['20'][method]['retrieved_ids']
            self.assertEqual(ten, [*range(9), 19])
            self.assertEqual(twenty, list(range(20)))
            self.assertNotEqual(ten, twenty[:10])
            self.assertEqual(set(row['evidence_completion_by_k']), {'10', '20'})
            self.assertEqual(report['api_call_count'], 0)


if __name__ == '__main__':
    unittest.main()
