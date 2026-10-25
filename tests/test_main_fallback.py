"""Agent回退使用本题余量；引用仍校验，失败记录和模式身份不能被覆盖。"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
import main as pipeline


class MainFallbackTests(unittest.TestCase):
    def initial(self):
        return {'query': 'What does the paper report?', 'context': '[1] The paper reports accuracy.',
                'selected_ids': [7], 'ledger': {'citation_registry': [
                    {'chunk_id': 7, 'source': 'a.pdf', 'page': 1, 'text': 'The paper reports accuracy.'}]}}

    def test_success_is_degraded_and_preserves_original_failure(self):
        result = {'status': 'failed', 'error': 'Invalid agent quote.', 'mode': 'agent'}
        call = Mock(return_value={'answer': 'The paper reports accuracy [1].'})
        with TemporaryDirectory() as folder:
            pipeline._agent_rag_fallback(result, self.initial(), call, 2, Path(folder))
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['error'], 'Invalid agent quote.')
        self.assertEqual(result['fallback']['agent_status'], 'failed')
        self.assertEqual(result['answer_status'], 'fallback_not_reviewed')
        self.assertEqual(call.call_count, 1)

    def test_no_remaining_budget_does_not_generate(self):
        result = {'status': 'failed', 'error': 'Budget used.'}
        call = Mock()
        with TemporaryDirectory() as folder:
            pipeline._agent_rag_fallback(result, self.initial(), call, 0, Path(folder))
        call.assert_not_called()
        self.assertEqual(result['status'], 'failed')

    def test_invalid_citations_cannot_escape_the_remaining_one_call(self):
        result = {'status': 'failed', 'error': 'Agent failed.'}
        call = Mock(return_value={'answer': 'A claim [99].'})
        with TemporaryDirectory() as folder:
            pipeline._agent_rag_fallback(result, self.initial(), call, 1, Path(folder))
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result['status'], 'failed')

    def test_proxy_failure_is_not_retried_as_fallback(self):
        result = {'status': 'failed', 'error': '反代 API 请求失败：HTTP 429。'}
        call = Mock()
        with TemporaryDirectory() as folder:
            pipeline._agent_rag_fallback(result, self.initial(), call, 5, Path(folder))
        call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
