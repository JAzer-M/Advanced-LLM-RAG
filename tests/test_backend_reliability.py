# 后端故障交付：走真实main/工具/复核，仅替换模型、HTTP与CPU资源；不联网。
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import main as pipeline
from src import api_llm as api, arxiv_tools
import test_arxiv_integration as network_fixtures
import test_main_agent as fixtures
from test_agent_answer import ANSWER, response, review
from test_agent_feedback import supported
from test_agent_step1 import assessment, missing


def limited_error(code=429, headers=None, body=b'Rate limit reached.'):
    return HTTPError('https://export.arxiv.org/api/query', code, 'unavailable',
                     headers or {'Retry-After': '120', 'Content-Type': 'text/plain'}, io.BytesIO(body))


class ExternalFailureTraceTests(unittest.TestCase):
    def setUp(self):
        state = patch.object(arxiv_tools, '_request_state', {'last_started': None})
        state.start()
        self.addCleanup(state.stop)
        sleep = patch.object(arxiv_tools.time, 'sleep')
        sleep.start()
        self.addCleanup(sleep.stop)

    def search_failure(self, error):
        with TemporaryDirectory() as temporary, patch.object(arxiv_tools, 'urlopen', side_effect=error) as http:
            with self.assertRaises(type(error)):
                arxiv_tools.search_arxiv('ti:Mamba', temporary)
            record = json.loads((Path(temporary) / 'result.json').read_text())
        self.assertEqual(http.call_count, 1)
        self.assertEqual(record['trace']['automatic_retries'], 0)
        return record['trace']

    def test_429_keeps_retry_after_bounded_body_and_elapsed_without_retry(self):
        trace = self.search_failure(limited_error(body=b'x' * 5000))
        self.assertEqual(trace['failure_kind'], 'rate_limited')
        self.assertEqual(trace['response_headers']['retry-after'], '120')
        self.assertEqual(trace['retry_after_seconds'], 120)
        self.assertLessEqual(len(trace['error_body_excerpt']), 2048)
        self.assertTrue(trace['error_body_truncated'])
        self.assertGreaterEqual(trace['elapsed_seconds'], 0)

    def test_http_date_retry_after_is_interpreted_against_response_date(self):
        trace = self.search_failure(limited_error(headers={
            'Date': 'Fri, 23 Oct 2026 04:00:00 GMT', 'Retry-After': 'Fri, 23 Oct 2026 04:01:30 GMT'}))
        self.assertEqual(trace['retry_after_seconds'], 90)

    def test_invalid_retry_after_does_not_replace_the_original_failure(self):
        trace = self.search_failure(limited_error(headers={'Retry-After': 'eventually'}))
        self.assertEqual(trace['http_status'], 429)
        self.assertIsNone(trace['retry_after_seconds'])

    def test_timeout_and_wrapped_timeout_are_distinct_from_http_rate_limit(self):
        for error in (TimeoutError('timed out'), URLError(TimeoutError('timed out'))):
            with self.subTest(error=type(error).__name__):
                trace = self.search_failure(error)
                self.assertEqual(trace['failure_kind'], 'timeout')
                self.assertNotIn('http_status', trace)
                self.assertGreaterEqual(trace['elapsed_seconds'], 0)

    def test_pdf_failure_records_the_same_diagnostics_without_fake_documents(self):
        error = limited_error(code=503, headers={'Retry-After': '30'})
        with TemporaryDirectory() as temporary, patch.object(arxiv_tools, 'urlopen', side_effect=error) as http:
            with self.assertRaises(HTTPError):
                arxiv_tools.read_arxiv_paper('2312.00752v2', temporary)
            record = json.loads((Path(temporary) / 'result.json').read_text())
        self.assertEqual(record['trace']['failure_kind'], 'http_error')
        self.assertEqual(record['trace']['retry_after_seconds'], 30)
        self.assertEqual(record['documents'], [])
        self.assertEqual(http.call_count, 1)


class BackendDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.case = network_fixtures.MainArxivIntegrationTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def assert_contract(self, result):
        required = {'query', 'mode', 'status', 'answer', 'answer_status', 'stop_reason',
                    'ledger', 'selected_ids', 'actions', 'api_summary', 'network'}
        self.assertTrue(required <= result.keys(), required - result.keys())
        self.assertIsInstance(result['answer'], str)
        self.assertTrue(result['answer'].strip())
        self.assertIsInstance(result['ledger']['citation_registry'], list)
        self.assertIsInstance(result['actions'], list)
        self.assertIsInstance(result['stop_reason'], str)

    def test_agent_429_delivers_unverified_boundary_with_no_extra_model_calls(self):
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / 'run'
            result, call, http = self.case.invoke(out, self.case.replies()[:4], [limited_error()])
            saved = json.loads((out / 'result.json').read_text())
            self.assertEqual(saved, result)
            self.assertEqual(json.loads((out / 'network/result.json').read_text())['status'], 'failed')
            self.assertTrue((out / 'fallback.md').is_file())
        self.assert_contract(result)
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['answer_status'], 'source_unavailable')
        self.assertEqual(result['stop_reason'], 'external_rate_limited')
        self.assertIn('429', result['answer'])
        self.assertIn('120', result['answer'])
        self.assertIn('cannot be verified', result['answer'])
        self.assertIn('does not show whether the paper reports them', result['answer'])
        self.assertNotIn('未报告该数值', result['answer'])
        self.assertEqual(result['network']['failure']['stage'], 'search')
        self.assertEqual(result['actions'][-1]['tool'], 'search_arxiv')
        self.assertEqual(result['actions'][-1]['status'], 'failed')
        self.assertEqual(result['api_summary']['attempts'], 4)
        self.assertEqual(call.call_count, 4)
        self.assertEqual(http.call_count, 1)

    def test_agent_timeout_is_delivered_as_source_unavailable(self):
        with TemporaryDirectory() as temporary:
            result, call, http = self.case.invoke(Path(temporary) / 'run', self.case.replies()[:4],
                                                  [URLError(TimeoutError('timed out'))])
        self.assert_contract(result)
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['stop_reason'], 'external_timeout')
        self.assertIn('timed out', result['answer'])
        self.assertEqual((call.call_count, http.call_count), (4, 1))

    def test_unavailable_source_does_not_repeat_an_unverified_non_reporting_claim(self):
        replies = self.case.replies()[:4]
        replies[2]['requirements'][0]['gap'] = 'Mamba论文未报告该数值。'
        with TemporaryDirectory() as temporary:
            result, call, _ = self.case.invoke(Path(temporary) / 'run', replies, [limited_error()])
        self.assertEqual(result['status'], 'degraded')
        self.assertNotIn('未报告该数值', result['answer'])
        self.assertEqual(call.call_count, 4)

    def test_auto_preserves_initial_answer_and_explains_external_failure(self):
        probe = '当前证据不足，无法回答。[1]'
        replies = self.case.replies()[:4]
        replies.insert(1, probe)
        with TemporaryDirectory() as temporary:
            result, call, http = self.case.invoke(Path(temporary) / 'run', replies, [limited_error()], mode='auto')
        self.assert_contract(result)
        self.assertEqual(result['status'], 'degraded')
        self.assertIn(probe, result['answer'])
        self.assertIn('429', result['answer'])
        self.assertIn('does not show whether the paper reports them', result['answer'])
        self.assertEqual(result['api_summary']['attempts'], 5)
        self.assertEqual((call.call_count, http.call_count), (5, 1))

    def test_pdf_timeout_preserves_search_action_and_actual_cost(self):
        http = [self.case.http_replies()[0], TimeoutError('PDF timed out')]
        with TemporaryDirectory() as temporary:
            result, call, network = self.case.invoke(Path(temporary) / 'run', self.case.replies()[:5], http)
        self.assert_contract(result)
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['network']['failure']['stage'], 'read')
        self.assertEqual([row['tool'] for row in result['actions']], ['search_arxiv', 'read_arxiv_paper'])
        self.assertEqual([row['status'] for row in result['actions']], ['completed', 'failed'])
        self.assertEqual((call.call_count, network.call_count), (5, 2))
        self.assertEqual(result['network']['papers_read'], 0)

    def test_partial_local_answer_is_still_reviewed_when_external_search_fails(self):
        proposal = {'requirements': [
            {'id': 'r1', 'subject': 'A', 'question_quote': 'Describe A'},
            {'id': 'r2', 'subject': 'Mamba', 'question_quote': 'Mamba'}]}
        check = supported(0)
        absent = missing(assessment())['requirements'][0]
        absent.update(id='r2', gap='缺少Mamba原文。', reason='Mamba primary source absent locally.')
        check['requirements'].append(absent)
        check['next_action'].update(type='stop', requirement_ids=['r2'], query=None, source=None, chunk_id=None)
        answer = ANSWER + '\nMamba的证据不足，无法确定。'
        checked = review(ANSWER)
        checked['requirements'].append({'id': 'r2', 'verdict': 'pass', 'answer_quote': answer.splitlines()[1],
                                       'reason': '明确未核实。', 'citations': []})
        route = {**network_fixtures.route(), 'requirement_id': 'r2'}
        replies = [fixtures.DECOMPOSE, proposal, check, route, answer, checked]
        with TemporaryDirectory() as temporary:
            result, call, http = self.case.invoke(Path(temporary) / 'run', replies, [limited_error()],
                                                  query='Describe A and Mamba.')
        self.assertEqual(result['status'], 'degraded', result.get('error'))
        self.assertIn(ANSWER, result['answer'])
        self.assertIn('cannot be verified', result['answer'])
        self.assertEqual(result['agent']['answer_summary']['answer_status'], 'review_passed')
        self.assertEqual((call.call_count, http.call_count), (6, 1))

    def test_three_modes_share_a_result_contract_and_actual_model_cost(self):
        for mode in ('rag', 'agent', 'auto'):
            replies = [fixtures.DECOMPOSE, ANSWER]
            if mode == 'agent':
                replies = [fixtures.DECOMPOSE, network_fixtures.plan('A'), supported(0), ANSWER, review()]
            with self.subTest(mode=mode), TemporaryDirectory() as temporary, \
                    patch.object(api, 'chat_completion', side_effect=[response(r) for r in replies]) as call:
                options = {} if mode == 'rag' else {'output_dir': Path(temporary) / 'run'}
                result = pipeline.main('Describe A.', mode=mode, **options)
                self.assert_contract(result)
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(result['api_summary']['attempts'], len(replies))
                self.assertEqual(result['api_summary']['reported_usage']['total_tokens'], 15 * len(replies))
                self.assertEqual(result['network']['status'], 'not_requested')
                self.assertEqual(call.call_count, len(replies))

    def test_model_transport_failure_returns_a_saved_failure_result_without_retry(self):
        with TemporaryDirectory() as temporary, patch.object(api, 'chat_completion',
                side_effect=[response(fixtures.DECOMPOSE), RuntimeError('HTTP 503')]) as call:
            out = Path(temporary) / 'run'
            result = pipeline.main('Describe A.', mode='auto', output_dir=out)
            self.assertEqual(json.loads((out / 'result.json').read_text()), result)
        self.assert_contract(result)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['api_summary']['failed_attempts'], 1)
        self.assertEqual(result['api_summary']['usage_missing_calls'], [2])
        self.assertEqual(call.call_count, 2)

    def test_rag_generation_failure_preserves_retrieved_evidence(self):
        with patch.object(api, 'chat_completion', side_effect=[response(fixtures.DECOMPOSE), RuntimeError('HTTP 503')]):
            result = pipeline.main('Describe A.', mode='rag')
        self.assert_contract(result)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['selected_ids'], [0])
        self.assertEqual(result['ledger']['citation_registry'][0]['chunk_id'], 0)
        self.assertEqual(result['api_summary']['attempts'], 2)

    def test_answer_collector_does_not_relabel_a_returned_failure_as_completed(self):
        from evaluation import run_answer_evaluation as evaluation
        source = str(Path(pipeline.__file__).resolve())
        metadata = {**self.case.fixture['knowledge_base'], 'index_path': source,
                    'chunks_path': source, 'manifest_path': None}
        with TemporaryDirectory() as temporary, patch('sys.argv', [
                'run_answer_evaluation', '--question-id', 'q2', '--output-dir', temporary]), \
                patch.object(evaluation, 'load_knowledge_base', return_value=(None, None, metadata)), \
                patch.object(api, 'chat_completion', side_effect=[response(fixtures.DECOMPOSE), RuntimeError('HTTP 503')]):
            with self.assertRaises(SystemExit) as stopped:
                evaluation.main()
            self.assertEqual(stopped.exception.code, 1)
            saved = json.loads((Path(temporary) / 'q2.json').read_text())
        self.assertEqual(saved['status'], 'failed')
        self.assertEqual(saved['model_calls'], 2)
        self.assertIn('HTTP 503', saved['error'])

    def test_invalid_planning_returns_an_explanation_without_releasing_a_bad_draft(self):
        bad = network_fixtures.plan('A')
        bad['requirements'][0]['question_quote'] = 'invented scope'
        replies = [fixtures.DECOMPOSE, bad, bad]
        with TemporaryDirectory() as temporary:
            result, call, http = self.case.invoke(Path(temporary) / 'run', replies, query='Describe A.', allow_network=False)
        self.assert_contract(result)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('did not finish', result['answer'])
        self.assertNotIn('invented scope', result['answer'])
        self.assertEqual(call.call_count, 3)
        http.assert_not_called()


if __name__ == '__main__':
    unittest.main()
