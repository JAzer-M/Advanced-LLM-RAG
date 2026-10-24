# 回答语言跟随提问语言、模型 JSON 代码块外壳兼容：离线检查，不调用模型、不联网。
import json
import unittest
from unittest.mock import patch

from src.agent_answer import boundary_answer
from src.answer_language import LANGUAGE_RULE, answer_language, localized
from src.model_json import loads_model_json
from src.query_decomposer import decompose_query


class ModelJsonTests(unittest.TestCase):
    def test_fenced_json_is_parsed(self):
        for text in ('```json\n{"a": 1}\n```', '```\n{"a": 1}\n```', '  ```JSON\n{"a": 1}```  ', '{"a": 1}'):
            with self.subTest(text=text):
                self.assertEqual(loads_model_json(text), {'a': 1})

    def test_other_invalid_output_is_still_rejected(self):
        for text in ('not json', '```json\nnot json\n```', 'Here is the JSON: {"a": 1}', '```json\n{"a": 1}\n``` extra'):
            with self.subTest(text=text):
                with self.assertRaises(json.JSONDecodeError):
                    loads_model_json(text)

    def test_decomposer_accepts_a_fenced_reply(self):
        reply = '```json\n' + json.dumps({'needs_decomposition': True, 'sub_queries': ['A?', 'B?']}) + '\n```'
        with patch('llm.generate_answer', return_value=reply):
            actual = decompose_query('Compare A and B.')
        self.assertEqual(actual['status'], 'accepted')
        self.assertEqual(actual['sub_queries'], ['A?', 'B?'])


class AnswerLanguageTests(unittest.TestCase):
    def test_language_follows_the_question(self):
        self.assertEqual(answer_language('VGG和RAG的区别是什么？'), 'zh')
        self.assertEqual(answer_language('What is the difference between RAG and VGG?'), 'en')
        self.assertEqual(answer_language('What does 的 mean in VGG?'), 'en')

    def test_an_explicit_request_wins(self):
        self.assertEqual(answer_language('VGG和RAG的区别是什么？请用英文回答。'), 'en')
        self.assertEqual(answer_language('What is VGG? Please answer in Chinese.'), 'zh')

    def test_localized_text_and_prompt_rule(self):
        self.assertEqual(localized('什么是注意力？', '中', 'en'), '中')
        self.assertEqual(localized('What is attention?', '中', 'en'), 'en')
        self.assertIn('same language as the user', LANGUAGE_RULE)

    def test_boundary_answer_uses_the_question_language(self):
        def data(question):
            return {'question': question, 'halt_reason': 'action_budget',
                    'requirements': [{'id': 'r1', 'subject': 'Atlas', 'need': 'bias init'}],
                    'assessment': [{'id': 'r1', 'status': 'missing', 'gap': ''}]}
        english = boundary_answer(data('How does Atlas initialize biases?'))
        chinese = boundary_answer(data('Atlas 如何初始化偏置？'))
        self.assertTrue(english.startswith('Insufficient evidence'))
        self.assertIn('budget', english)
        self.assertTrue(chinese.startswith('当前证据不足'))
        self.assertIn('预算', chinese)
        self.assertTrue(boundary_answer(data('What is Atlas?'), review_failed=True).startswith('The answer failed review'))


class MainPromptAndGapTests(unittest.TestCase):
    def test_rag_prompt_no_longer_forces_chinese(self):
        import main
        prompt = main.build_prompt('What is VGG?', '[1] context')
        self.assertIn(LANGUAGE_RULE, prompt)
        self.assertNotIn('Simplified Chinese', prompt)

    def test_english_overview_without_direct_comparison_is_not_a_gap(self):
        import main
        query = 'What is the difference between RAG and VGG?'
        answer = ('RAG combines a retriever with a seq2seq generator [1]. VGG is a very deep convolutional '
                  'network for image recognition [2]. The context does not provide a direct comparison of '
                  'their performance.')
        self.assertFalse(main.has_evidence_gap(query, answer))

    def test_english_core_gap_is_still_detected(self):
        import main
        query = 'What is the difference between RAG and VGG?'
        answer = ('RAG combines a retriever with a seq2seq generator [1]. The context does not provide '
                  'information about the VGG architecture.')
        self.assertTrue(main.has_evidence_gap(query, answer))


if __name__ == '__main__':
    unittest.main()
