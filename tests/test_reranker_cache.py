"""缓存只复用同一请求内相同模型/查询/原文的分数；不减少候选或补查轮数。"""
import unittest
from unittest.mock import patch

from src.evidence_gap import complete_evidence
from src.reranker import rerank_results


class CountingModel:
    def __init__(self):
        self.pairs = []

    def predict(self, pairs):
        self.pairs.extend(pairs)
        return [float(sum(map(ord, query + text)) % 997) for query, text in pairs]


class RerankerCacheTests(unittest.TestCase):
    def chunks(self):
        return [{'chunk_id': i, 'source': f'{name}.pdf', 'title': name.title(),
                 'page': i + 1, 'section': None, 'text': f'Evidence {i}.', 'rerank_score': float(100 - i)}
                for i, name in enumerate(['alpha'] * 8 + ['beta'] * 8)]

    def test_same_pairs_across_overlapping_calls_are_scored_once(self):
        model, cache = CountingModel(), {}
        chunks = self.chunks()
        rerank_results('query', chunks[:4], model, score_cache=cache)
        actual = rerank_results('query', chunks[2:6], model, score_cache=cache)
        expected = rerank_results('query', chunks[2:6], CountingModel())
        self.assertEqual(actual, expected)
        self.assertEqual(len(model.pairs), 6)

    def test_queries_text_sources_and_models_have_separate_scores(self):
        model, cache = CountingModel(), {}
        chunk = self.chunks()[0]
        for query, candidate in [('q', chunk), ('other', chunk),
                                 ('q', {**chunk, 'text': 'Changed.'}),
                                 ('q', {**chunk, 'source': 'other.pdf'})]:
            rerank_results(query, [candidate], model, score_cache=cache)
        other = CountingModel()
        rerank_results('q', [chunk], other, score_cache=cache)
        self.assertEqual(len(model.pairs), 4)
        self.assertEqual(len(other.pairs), 1)

    def test_repeated_rows_keep_their_own_metadata_and_order(self):
        chunk = self.chunks()[0]
        rows = [chunk, {**chunk, 'chunk_id': 999, 'page': 99}]
        model = CountingModel()
        actual = rerank_results('q', rows, model, score_cache={})
        self.assertEqual([r['chunk_id'] for r in actual], [0, 999])
        self.assertEqual(len(model.pairs), 1)
        self.assertEqual(actual[0]['rerank_score'], actual[1]['rerank_score'])

    def test_two_completion_rounds_keep_rankings_candidates_and_budget(self):
        chunks = self.chunks()
        local = [{'query': 'What does Alpha store?', 'top_ids': [8, 9, 10]},
                 {'query': 'What does Beta store?', 'top_ids': [0, 1, 2]}]
        results, traces, counts = [], [], []
        for cache in (None, {}):
            model = CountingModel()
            with patch('src.evidence_gap.retrieve', return_value=chunks), \
                    patch('src.evidence_gap.retrieve_bm25', return_value=chunks):
                selected, trace = complete_evidence('Compare Alpha and Beta.', chunks, local, [],
                    object(), object(), chunks, object(), model, candidate_k=2,
                    max_rounds=2, score_cache=cache)
            results.append(selected)
            traces.append([{key: row[key] for key in ('candidate_depth', 'supplement_queries',
                            'new_candidate_ids', 'selected_ids')} for row in trace['round_history']])
            counts.append(len(model.pairs))
        self.assertEqual(results[0], results[1])
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(len(traces[1]), 2)
        self.assertLess(counts[1], counts[0])


if __name__ == '__main__':
    unittest.main()
