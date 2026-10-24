"""普通比较补充双方简介；未要求的直接性能实验不应触发Auto升级。"""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import main as pipeline
from src import api_llm as api
import test_main_agent as fixtures
from test_agent_step1 import response


class ComparisonContextTests(unittest.TestCase):
    def chunks(self):
        return [{'chunk_id': i, 'source': name + '.pdf', 'title': name,
                 'page': 1 if i % 5 < 4 else 8, 'section': None,
                 'text': ('Abstract ' if i % 5 == 0 else '') + f'{name} original passage {i}.'}
                for i, name in enumerate(['Alpha'] * 5 + ['Beta'] * 5 + ['Gamma'] * 5)]

    def test_overview_adds_opening_passages_without_replacing_selected_evidence(self):
        chunks = self.chunks()
        context, ledger = pipeline.build_evidence_context(chunks, [chunks[4], chunks[9]],
            query='What is the difference between Alpha and Beta?')
        self.assertEqual(ledger['selected_ids'], [4, 9])
        self.assertEqual([c['chunk_id'] for c in ledger['citation_registry'][:2]], [4, 9])
        self.assertEqual(set(ledger['comparison_intro_ids']), {0, 1, 2, 3, 5, 6, 7, 8})
        self.assertNotIn('Gamma original', context)
        for passage in ledger['citation_registry']:
            self.assertEqual(passage['text'], chunks[passage['chunk_id']]['text'])

    def test_specific_aspect_question_keeps_its_existing_context(self):
        chunks = self.chunks()
        for query in ('Compare Alpha and Beta on accuracy.', 'What does Alpha report?',
                      'How does Alpha differ from Beta in filter sizes?'):
            with self.subTest(query=query):
                _, ledger = pipeline.build_evidence_context(chunks, [chunks[4], chunks[9]], query=query)
                self.assertFalse(ledger.get('comparison_intro_ids'))

    def test_missing_abstract_marker_keeps_the_normal_retrieval_path(self):
        chunks = self.chunks()
        chunks[5]['text'] = 'A bibliography entry.'
        self.assertEqual(pipeline.comparison_introductions(
            'What is the difference between Alpha and Beta?', chunks), [])

    def test_optional_head_to_head_caveat_does_not_upgrade_a_broad_comparison(self):
        for caveat in ('现有证据未提供二者在相同任务或基准上的直接对比。',
                       '证据中未提供二者的直接对比实验。',
                       '当前资料没有这两种方法的直接比较数据。',
                       '所提供的证据未包含两者在统一任务或数据集上的直接对比，故无法据此判断性能优劣。',
                       '上下文不足以判断二者性能优劣。'):
            with self.subTest(caveat=caveat):
                answer = 'Alpha 用于图像识别[1]，Beta 用于文本生成[2]。' + caveat
                self.assertFalse(pipeline.has_evidence_gap('What is the difference between Alpha and Beta?', answer))

    def test_required_performance_gap_still_upgrades(self):
        answer = 'Alpha 用于图像识别[1]，Beta 用于文本生成[2]。现有证据未提供二者在同基准上的直接对比。'
        self.assertTrue(pipeline.has_evidence_gap('Compare Alpha and Beta performance on the same benchmark.', answer))

    def test_refusal_and_missing_requested_aspect_still_upgrade(self):
        for answer in ('现有证据未提供直接对比，无法回答。',
                       'Alpha 采用卷积[1]，但现有证据未说明 Beta 的机制，无法完整比较。',
                       'Alpha 采用卷积[1]，现有证据未提供 Beta 的架构，因此无法直接比较。',
                       'Alpha 采用卷积[1]，证据不足以说明 Beta 的用途，所以无法直接比较。',
                       'Alpha 采用卷积[1]，证据没有关于 Beta 的信息，无法直接比较。'):
            with self.subTest(answer=answer):
                self.assertTrue(pipeline.has_evidence_gap('What is the difference between Alpha and Beta?', answer))


class ComparisonRoutingTests(unittest.TestCase):
    def setUp(self):
        fixtures.MainAgentTests.setUp(self)

    def invoke(self, complete_evidence):
        with TemporaryDirectory() as temporary, \
                patch.object(pipeline, 'comparison_introductions', return_value=self.fixture['chunks'][:2]), \
                patch.object(pipeline, 'supplement_evidence', return_value=(
                    self.fixture['chunks'][:1], {'rounds': 2})) as supplement, \
                patch.object(api, 'chat_completion', side_effect=[response(fixtures.DECOMPOSE),
                    {'answer': 'A 的用途与 B 不同[1]。', 'finish_reason': 'stop', 'usage': {}}]) as call:
            result = pipeline.main('What is the difference between A and B?', mode='auto',
                complete_evidence=complete_evidence, output_dir=Path(temporary) / 'run')
            return result, supplement.call_count, call.call_count

    def test_available_introductions_skip_automatic_repeated_completion(self):
        result, supplements, calls = self.invoke(None)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(supplements, 0)
        self.assertEqual(calls, 2)
        self.assertEqual(result['retrieval_diagnostics']['evidence_completion']['max_rounds'], 2)

    def test_explicit_completion_still_executes_the_original_pipeline(self):
        result, supplements, calls = self.invoke(True)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(supplements, 1)
        self.assertEqual(calls, 2)
        self.assertEqual(result['retrieval_diagnostics']['evidence_completion']['rounds'], 2)


if __name__ == '__main__':
    unittest.main()
