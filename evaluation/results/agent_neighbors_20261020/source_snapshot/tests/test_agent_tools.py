# 本地工具回归：搜索预算、来源过滤，以及邻段的原文顺序和读取边界。
# 小型真实 FAISS/BM25 验证接口拼接，模型由替身提供，不下载模型或请求生成 API。

from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

import faiss
import numpy as np

from src import agent_tools as tools
from src.bm25_retriever import build_bm25_index


def passages(count):
    return [{'chunk_id': i, 'source': 'a.pdf' if i % 2 == 0 else 'b.pdf',
             'page': i + 1, 'title': 'Fixture', 'section': 'Methods',
             'text': f'Original evidence passage {i}.'} for i in range(count)]


def resources(chunks):
    model = Mock()
    model.predict.side_effect = lambda pairs: list(range(len(pairs)))
    return {'chunks': chunks, 'index': object(), 'embedding_model': Mock(),
            'bm25': object(), 'reranker_model': model,
            'knowledge_base': {'version': tools.SEARCH_KB_VERSION,
                               'manifest_sha256': 'fixture-manifest',
                               'files': {'faiss.index': 'fixture-index', 'chunks.json': 'fixture-chunks'}}}


class LocalSearchTests(unittest.TestCase):
    def test_loader_explicitly_pins_eight_paper_version_and_returns_reusable_resources(self):
        chunks = passages(3)
        fixture = resources(chunks)
        with patch.object(tools, 'load_knowledge_base', return_value=(
                fixture['index'], chunks, fixture['knowledge_base'])) as load, \
                patch.object(tools, 'load_embedding_model', return_value=fixture['embedding_model']) as embedding, \
                patch.object(tools, 'CrossEncoder', return_value=fixture['reranker_model']) as reranker:
            loaded = tools.load_search_resources()
        self.assertEqual(load.call_args.args[1], 'all-papers-8-20261020')
        self.assertIs(loaded['chunks'], chunks)
        self.assertIs(loaded['index'], fixture['index'])
        self.assertIs(loaded['embedding_model'], fixture['embedding_model'])
        self.assertIs(loaded['reranker_model'], fixture['reranker_model'])
        embedding.assert_called_once_with()
        reranker.assert_called_once_with('BAAI/bge-reranker-base', device='cpu')

    def test_global_search_respects_budgets_and_does_not_mutate_original_passages(self):
        chunks = passages(160)
        original = deepcopy(chunks)
        fixture = resources(chunks)
        with patch.object(tools, 'retrieve', side_effect=lambda *args, top_k: chunks[:top_k]), \
                patch.object(tools, 'retrieve_bm25', side_effect=lambda *args, top_k: list(reversed(chunks))[:top_k]):
            result = tools.search_local_kb('  Locate facts  ', fixture)
        self.assertEqual(result['query'], 'Locate facts')
        self.assertIsNone(result['source'])
        self.assertEqual(len(result['trace']['dense_ids']), 120)
        self.assertEqual(len(result['trace']['bm25_ids']), 120)
        self.assertEqual(len(result['trace']['candidate_ids']), 120)
        self.assertEqual(len(result['results']), 10)
        self.assertEqual(len(fixture['reranker_model'].predict.call_args.args[0]), 120)
        self.assertEqual(chunks, original)
        self.assertTrue(all(c['kb_version'] == tools.SEARCH_KB_VERSION for c in result['results']))
        self.assertEqual(result['trace']['generation_api_calls'], 0)

    def test_source_filter_runs_before_truncation_and_preserves_original_chunk_ids(self):
        chunks = passages(134)
        for i, chunk in enumerate(chunks):
            chunk['source'] = 'other.pdf' if i < 130 else 'target.pdf'
        fixture = resources(chunks)
        # 目标论文全部排在全库 120 名之后，先截断再过滤的实现会丢掉它们。
        with patch.object(tools, 'retrieve', side_effect=lambda *args, top_k: chunks[:top_k]) as dense, \
                patch.object(tools, 'retrieve_bm25', side_effect=lambda *args, top_k: chunks[:top_k]) as sparse:
            result = tools.search_local_kb('Locate target evidence', fixture, source='target.pdf')
        self.assertEqual(dense.call_args.kwargs['top_k'], 134)
        self.assertEqual(sparse.call_args.kwargs['top_k'], 134)
        self.assertEqual(set(result['trace']['candidate_ids']), {130, 131, 132, 133})
        self.assertEqual({c['chunk_id'] for c in result['results']}, {130, 131, 132, 133})
        self.assertTrue(all(c['source'] == 'target.pdf' for c in result['results']))

    def test_real_faiss_and_bm25_return_canonical_text_and_metadata(self):
        chunks = passages(3)
        chunks[0]['text'] = 'Needle evidence describes the requested criterion.'
        chunks[1]['text'] = 'Unrelated background from another source.'
        chunks[2]['text'] = 'Needle evidence supplies a second qualifying condition.'
        fixture = resources(chunks)
        fixture['index'] = faiss.IndexFlatIP(2)
        fixture['index'].add(np.array([[1., 0.], [0., 1.], [.8, .6]], dtype=np.float32))
        fixture['embedding_model'].encode.return_value = np.array([[1., 0.]], dtype=np.float32)
        fixture['bm25'] = build_bm25_index(chunks)
        result = tools.search_local_kb('needle criterion', fixture, source='a.pdf')
        self.assertEqual({c['chunk_id'] for c in result['results']}, {0, 2})
        for item in result['results']:
            expected = chunks[item['chunk_id']]
            for key in ('source', 'page', 'title', 'section', 'text'):
                self.assertEqual(item[key], expected[key])
        self.assertEqual(fixture['embedding_model'].encode.call_args.args[0], ['needle criterion'])

    def test_invalid_queries_fail_before_retrieval(self):
        fixture = resources(passages(2))
        with patch.object(tools, 'retrieve') as dense, patch.object(tools, 'retrieve_bm25') as sparse:
            for query in ('', '  \n', None, 123, True, []):
                with self.subTest(query=query), self.assertRaises(ValueError):
                    tools.search_local_kb(query, fixture)
        dense.assert_not_called()
        sparse.assert_not_called()

    def test_unknown_or_noncanonical_sources_fail_before_retrieval(self):
        fixture = resources(passages(2))
        with patch.object(tools, 'retrieve') as dense, patch.object(tools, 'retrieve_bm25') as sparse:
            for source in ('missing.pdf', 'Fixture', 'A.pdf', '', ' ', 123, []):
                with self.subTest(source=source), self.assertRaises(ValueError):
                    tools.search_local_kb('criterion', fixture, source=source)
        dense.assert_not_called()
        sparse.assert_not_called()

    def test_empty_retrieval_returns_empty_results_without_reranking(self):
        fixture = resources(passages(2))
        with patch.object(tools, 'retrieve', return_value=[]), \
                patch.object(tools, 'retrieve_bm25', return_value=[]):
            result = tools.search_local_kb('criterion', fixture)
        self.assertEqual(result['results'], [])
        self.assertEqual(result['trace']['candidate_ids'], [])
        self.assertEqual(result['trace']['selected_ids'], [])
        fixture['reranker_model'].predict.assert_not_called()

    def test_retrieval_error_propagates_without_retry(self):
        fixture = resources(passages(2))
        with patch.object(tools, 'retrieve', side_effect=RuntimeError('fixture failure')) as dense, \
                patch.object(tools, 'retrieve_bm25') as sparse:
            with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                tools.search_local_kb('criterion', fixture)
        self.assertEqual(dense.call_count, 1)
        sparse.assert_not_called()

    def test_missing_fixed_version_does_not_fall_back_or_load_models(self):
        with patch.object(tools, 'load_knowledge_base', side_effect=FileNotFoundError('missing version')) as load, \
                patch.object(tools, 'load_embedding_model') as embedding:
            with self.assertRaises(FileNotFoundError):
                tools.load_search_resources()
        self.assertEqual(load.call_count, 1)
        embedding.assert_not_called()


class ReadNeighborsTests(unittest.TestCase):
    def test_default_window_returns_center_and_one_passage_on_each_side(self):
        chunks = passages(7)
        for chunk in chunks:
            chunk['source'] = 'a.pdf'
        fixture = resources(chunks)
        result = tools.read_neighbors(3, fixture, source='a.pdf')
        self.assertEqual(result['trace']['selected_ids'], [2, 3, 4])
        self.assertEqual([item['offset'] for item in result['results']], [-1, 0, 1])
        self.assertEqual(result['chunk_id'], 3)
        self.assertEqual(result['source'], 'a.pdf')
        self.assertEqual(result['knowledge_base'], fixture['knowledge_base'])
        for item in result['results']:
            for key, value in chunks[item['chunk_id']].items():
                self.assertEqual(item[key], value)
            self.assertEqual(item['kb_version'], tools.SEARCH_KB_VERSION)

    def test_interleaved_sources_use_document_order_instead_of_global_id_distance(self):
        # 全库中 A/B 交错排列，A 的相邻片段是 2、4、6，而非全库的 3、4、5。
        result = tools.read_neighbors(4, resources(passages(9)), source='a.pdf')
        self.assertEqual(result['trace']['selected_ids'], [2, 4, 6])
        self.assertEqual([item['offset'] for item in result['results']], [-1, 0, 1])
        self.assertTrue(all(item['source'] == 'a.pdf' for item in result['results']))

    def test_window_stops_at_document_boundaries(self):
        chunks = passages(6)
        for i, chunk in enumerate(chunks):
            chunk['source'] = 'a.pdf' if i < 3 else 'b.pdf'
        for anchor, source, expected_ids, offsets in (
                (2, 'a.pdf', [0, 1, 2], [-2, -1, 0]),
                (3, 'b.pdf', [3, 4, 5], [0, 1, 2])):
            with self.subTest(anchor=anchor):
                result = tools.read_neighbors(anchor, resources(chunks), source=source, window=2)
                self.assertEqual(result['trace']['selected_ids'], expected_ids)
                self.assertEqual([item['offset'] for item in result['results']], offsets)

    def test_single_passage_document_returns_only_center(self):
        result = tools.read_neighbors(0, resources(passages(1)), source='a.pdf', window=2)
        self.assertEqual(result['trace']['selected_ids'], [0])
        self.assertEqual(result['results'][0]['offset'], 0)

    def test_window_zero_and_maximum_bound_the_amount_of_context(self):
        fixture = resources(passages(13))
        for window, expected in ((0, [6]), (2, [2, 4, 6, 8, 10])):
            with self.subTest(window=window):
                result = tools.read_neighbors(6, fixture, source='a.pdf', window=window)
                self.assertEqual(result['trace']['selected_ids'], expected)
                self.assertEqual(result['trace']['window'], window)
                self.assertEqual(result['trace']['max_window'], 2)

    def test_invalid_chunk_ids_are_rejected_instead_of_using_implicit_indices(self):
        fixture = resources(passages(3))
        for chunk_id in (-1, 3, True, False, 1.0, '1', None, []):
            with self.subTest(chunk_id=chunk_id), self.assertRaises(ValueError):
                tools.read_neighbors(chunk_id, fixture, source='a.pdf')
        with self.assertRaises(ValueError):
            tools.read_neighbors(0, resources([]), source='a.pdf')

    def test_wrong_or_noncanonical_source_is_rejected(self):
        fixture = resources(passages(3))
        for source in ('b.pdf', 'A.pdf', 'Fixture', '', None, 123, []):
            with self.subTest(source=source), self.assertRaises(ValueError):
                tools.read_neighbors(0, fixture, source=source)

    def test_invalid_windows_are_rejected(self):
        fixture = resources(passages(3))
        for window in (-1, 3, True, False, 1.0, '1', None, []):
            with self.subTest(window=window), self.assertRaises(ValueError):
                tools.read_neighbors(0, fixture, source='a.pdf', window=window)

    def test_raw_text_and_metadata_are_preserved_without_mutating_input(self):
        fixture = resources(passages(7))
        original_chunks = deepcopy(fixture['chunks'])
        original_metadata = deepcopy(fixture['knowledge_base'])
        result = tools.read_neighbors(2, fixture, source='a.pdf')
        self.assertEqual(fixture['chunks'], original_chunks)
        self.assertEqual(fixture['knowledge_base'], original_metadata)
        self.assertEqual(result['trace']['read_chars'],
                         sum(len(original_chunks[i]['text']) for i in (0, 2, 4)))
        result['results'][0]['text'] = 'Changed output copy'
        self.assertEqual(fixture['chunks'], original_chunks)

    def test_reading_needs_only_chunks_and_metadata_without_loading_or_searching(self):
        # 独立读取不需要向量模型、重排模型或索引；这些入口被调用就让测试失败。
        fixture = resources(passages(5))
        minimal = {key: fixture[key] for key in ('chunks', 'knowledge_base')}
        with patch.object(tools, 'load_search_resources', side_effect=AssertionError('model load')), \
                patch.object(tools, 'search_local_kb', side_effect=AssertionError('search')):
            result = tools.read_neighbors(2, minimal, source='a.pdf')
        self.assertEqual(result['trace']['selected_ids'], [0, 2, 4])
        self.assertEqual(result['trace']['generation_api_calls'], 0)


if __name__ == '__main__':
    unittest.main()
