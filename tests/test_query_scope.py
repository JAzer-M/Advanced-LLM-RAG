"""来源边界必须在截断前生效，不能改变向量行号与全局chunk_id。"""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np
import agent
from src.query_scope import resolve_query_scope
from src.retriever import retrieve
from src.bm25_retriever import retrieve_bm25
from src import agent_tools


def fixture():
    return [{'chunk_id': i, 'source': source, 'title': title, 'page': 1,
             'section': 'Methods', 'text': f'Evidence {i}.'}
            for i, (source, title) in enumerate([
                ('2000.00001.pdf', 'A precise first paper'),
                ('2000.00002.pdf', 'A different second paper'),
                ('2000.00001.pdf', 'A precise first paper')])]


class QueryScopeTests(unittest.TestCase):
    def test_explicit_paper_header_separates_question_and_source(self):
        q = 'For the paper "A precise first paper" (arXiv: 2000.00001), answer this question: Which metric is used?'
        scope = resolve_query_scope(q, fixture())
        self.assertEqual(scope['sources'], ['2000.00001.pdf'])
        self.assertEqual(scope['retrieval_query'], 'Which metric is used?')

    def test_multiple_named_papers_are_both_preserved(self):
        q = 'Compare A precise first paper with A different second paper.'
        self.assertEqual(set(resolve_query_scope(q, fixture())['sources']), {'2000.00001.pdf', '2000.00002.pdf'})

    def test_ambiguous_general_terms_do_not_force_a_paper(self):
        self.assertEqual(resolve_query_scope('Which paper uses this method?', fixture())['sources'], [])

    def test_conflicting_header_identity_does_not_strip_away_the_conflict(self):
        query = 'For the paper "A different second paper" (arXiv: 2000.00001), answer this question: Which metric?'
        scope = resolve_query_scope(query, fixture())
        self.assertEqual(len(scope['sources']), 2)
        self.assertEqual(scope['retrieval_query'], query)

    def test_invalid_explicit_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_query_scope('Question?', fixture(), ['missing.pdf'])

    def test_dense_filters_before_top_k_without_changing_ids(self):
        model = SimpleNamespace(encode=Mock(return_value=np.zeros((1, 2))))
        index = SimpleNamespace(search=Mock(return_value=(np.array([[.9, .8, .7]]), np.array([[1, 2, 0]]))))
        result = retrieve(model, index, fixture(), 'Question?', top_k=1, sources=['2000.00001.pdf'])
        self.assertEqual(result[0]['chunk_id'], 2)
        self.assertEqual(index.search.call_args.args[1], 3)

    def test_sparse_filters_before_top_k_without_changing_ids(self):
        bm25 = SimpleNamespace(get_scores=lambda query: [.1, 10., .9])
        result = retrieve_bm25(bm25, fixture(), 'metric', top_k=1, sources=['2000.00001.pdf'])
        self.assertEqual(result[0]['chunk_id'], 2)

    def test_unique_explicit_paper_context_can_bind_the_original_question(self):
        question = 'What is the performance of the best model?'
        query = 'For the paper "A precise first paper" (arXiv: 2000.00001), answer this question: ' + question
        p = {'requirements': [{'id': 'r1', 'subject': 'A precise first paper', 'question_quote': question}]}
        plan = agent.bind_requirements(p, query)
        self.assertIn(agent.normalize(plan['requirements'][0]['question_quote']), agent.normalize(query))
        self.assertEqual(agent.search_query(plan['requirements'][0]), question)

    def test_scoped_agent_search_filters_all_candidates_and_keeps_global_ids(self):
        chunks = fixture()
        resources = {'chunks': chunks, 'index': object(), 'embedding_model': object(), 'bm25': object(),
                     'reranker_model': object(), 'knowledge_base': {'version': 'fixture'},
                     'source_scope': ['2000.00001.pdf']}
        with patch.object(agent_tools, 'retrieve', return_value=list(reversed(chunks))), \
                patch.object(agent_tools, 'retrieve_bm25', return_value=chunks), \
                patch.object(agent_tools, 'rerank_results', side_effect=lambda q, c, m, **kw: c):
            result = agent_tools.search_local_kb('metric', resources)
        self.assertEqual(set(result['trace']['candidate_ids']), {0, 2})
        self.assertEqual(result['source'], '2000.00001.pdf')
        with self.assertRaises(ValueError):
            agent_tools.search_local_kb('metric', resources, source='2000.00002.pdf')
        with self.assertRaises(ValueError):
            agent_tools.read_neighbors(1, resources, source='2000.00002.pdf')


if __name__ == '__main__':
    unittest.main()
