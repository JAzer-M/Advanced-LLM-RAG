# P3只读工具的真实解析/落盘回归：HTTP用替身，PDF在内存生成，不联网也不触碰知识库。
import hashlib
import json
import ssl
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pymupdf

from src import arxiv_tools as tools


FEED = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>http://arxiv.org/abs/2312.00752v1</id><title> Example Paper </title>
<author><name>Test Author</name></author><summary>Discovery metadata only.</summary>
<published>2023-12-01T00:00:00Z</published><updated>2023-12-01T00:00:00Z</updated>
</entry></feed>'''


def http_response(body, url):
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = body
    response.geturl.return_value = url
    response.status = 200
    return response


def pdf_bytes(pages=1):
    with pymupdf.open() as doc:
        doc.set_metadata({'title': 'Test Paper'})
        for _ in range(pages):
            doc.new_page().insert_text((72, 72), 'A measurable result is reported in the original paper.')
        return doc.tobytes()


class ArxivToolTests(unittest.TestCase):
    def setUp(self):
        settings = patch.object(tools, '_request_state', {'last_started': None})
        settings.start()
        self.addCleanup(settings.stop)
        sleep = patch.object(tools.time, 'sleep')
        sleep.start()
        self.addCleanup(sleep.stop)

    def test_search_records_pinned_metadata_raw_feed_and_actual_request(self):
        reply = http_response(FEED, 'https://export.arxiv.org/api/query?search_query=ti%3AMamba')
        with TemporaryDirectory() as temporary, patch.object(tools, 'urlopen', return_value=reply) as request:
            result = tools.search_arxiv('ti:Mamba AND all:"state space"', temporary, limit=2)
            stored = json.loads((Path(temporary) / 'result.json').read_text())
            self.assertEqual((Path(temporary) / 'response.xml').read_bytes(), FEED)
        query = parse_qs(urlsplit(request.call_args.args[0].full_url).query)
        self.assertEqual(query['search_query'], ['ti:Mamba AND all:"state space"'])
        self.assertEqual(query['max_results'], ['2'])
        self.assertTrue(request.call_args.kwargs['context'].check_hostname)
        self.assertEqual(request.call_args.kwargs['context'].verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(stored, result)
        self.assertFalse(result['metadata_is_answer_evidence'])
        self.assertEqual(result['papers'][0]['arxiv_id'], '2312.00752v1')
        self.assertEqual(result['papers'][0]['pdf_url'], 'https://arxiv.org/pdf/2312.00752v1')
        self.assertEqual(result['trace']['response_sha256'], hashlib.sha256(FEED).hexdigest())

    def test_empty_feed_is_a_successful_search_without_invented_papers(self):
        with TemporaryDirectory() as temporary, patch.object(tools, 'urlopen', return_value=http_response(
                b'<feed xmlns="http://www.w3.org/2005/Atom"/>', 'https://export.arxiv.org/api/query')):
            result = tools.search_arxiv('ti:unavailable', temporary)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['papers'], [])

    def test_bad_arguments_fail_before_any_network_request(self):
        with TemporaryDirectory() as temporary, patch.object(tools, 'urlopen') as request:
            for query, count in [('', 3), ('a' * 501, 3), ('a', True), ('a', 0), ('a', 6)]:
                with self.subTest(query=query[:5], count=count), self.assertRaises(ValueError):
                    tools.search_arxiv(query, temporary, count)
            for identity in ['2312.00752', '../file', 'https://arxiv.org/pdf/2312.00752v1', '2312.00752v0']:
                with self.subTest(identity=identity), self.assertRaises(ValueError):
                    tools.read_arxiv_paper(identity, temporary)
        request.assert_not_called()

    def test_search_error_feed_unpinned_id_and_duplicate_results_are_rejected(self):
        bad = [FEED.replace(b'2312.00752v1', b'2312.00752'),
               FEED.replace(b'http://arxiv.org/abs/2312.00752v1', b'http://arxiv.org/api/errors'),
               FEED.replace(b'</feed>', b'<entry>' + FEED.split(b'<entry>')[1]),
               b'<html>maintenance</html>']
        for body in bad:
            with self.subTest(body=body[:35]), TemporaryDirectory() as temporary, patch.object(tools, 'urlopen',
                    return_value=http_response(body, 'https://export.arxiv.org/api/query')), self.assertRaises(ValueError):
                tools.search_arxiv('ti:Mamba', temporary)

    def test_http_failure_is_saved_once_and_existing_output_cannot_be_reused(self):
        error = HTTPError('https://export.arxiv.org/api/query', 503, 'unavailable', {}, None)
        with TemporaryDirectory() as temporary, patch.object(tools, 'urlopen', side_effect=error) as request:
            with self.assertRaises(HTTPError):
                tools.search_arxiv('ti:Mamba', temporary)
            result = json.loads((Path(temporary) / 'result.json').read_text())
            original = (Path(temporary) / 'result.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'new empty'):
                tools.search_arxiv('ti:Mamba', temporary)
            self.assertEqual((Path(temporary) / 'result.json').read_bytes(), original)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['trace']['http_status'], 503)
        self.assertEqual(result['trace']['automatic_retries'], 0)

    def test_pdf_read_keeps_real_text_pages_provenance_and_separate_evidence_ids(self):
        body = pdf_bytes(2)
        with TemporaryDirectory() as temporary, patch.object(tools, 'urlopen', return_value=http_response(
                body, 'https://arxiv.org/pdf/2312.00752v1')) as request:
            result = tools.read_arxiv_paper('2312.00752v1', temporary)
            self.assertEqual((Path(temporary) / '2312.00752v1.pdf').read_bytes(), body)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result['pages'], 2)
        self.assertEqual({d['page'] for d in result['documents']}, {1, 2})
        for document in result['documents']:
            self.assertIn('measurable result', document['text'])
            self.assertTrue(document['evidence_id'].startswith('arxiv:2312.00752v1:'))
            self.assertNotIn('chunk_id', document)
            self.assertEqual(document['pdf_sha256'], hashlib.sha256(body).hexdigest())
        self.assertFalse(result['permanent_kb_import'])

    def test_non_pdf_and_unpinned_redirect_are_recorded_as_failures(self):
        for body, url in [(b'<html>unavailable</html>', 'https://arxiv.org/pdf/2312.00752v1'),
                          (pdf_bytes(), 'https://arxiv.org/pdf/2312.00752')]:
            with self.subTest(url=url), TemporaryDirectory() as temporary, patch.object(tools, 'urlopen',
                    return_value=http_response(body, url)):
                with self.assertRaises(ValueError):
                    tools.read_arxiv_paper('2312.00752v1', temporary)
                self.assertEqual(json.loads((Path(temporary) / 'result.json').read_text())['status'], 'failed')

    def test_unknown_final_origin_is_not_accepted_as_primary_evidence(self):
        with TemporaryDirectory() as temporary, patch.object(tools, 'urlopen', return_value=http_response(
                pdf_bytes(), 'https://example.org/pdf/2312.00752v1')):
            with self.assertRaisesRegex(ValueError, 'origin'):
                tools.read_arxiv_paper('2312.00752v1', temporary)

    def test_byte_page_and_text_budgets_fail_without_silent_truncation(self):
        for budget, value in [('MAX_PDF_BYTES', 4), ('MAX_PDF_PAGES', 1), ('MAX_TEXT_CHARS', 5)]:
            with self.subTest(budget=budget), TemporaryDirectory() as temporary, patch.object(tools, budget, value), \
                    patch.object(tools, 'urlopen', return_value=http_response(pdf_bytes(2), 'https://arxiv.org/pdf/2312.00752v1')):
                with self.assertRaises(ValueError):
                    tools.read_arxiv_paper('2312.00752v1', temporary)
                self.assertEqual(json.loads((Path(temporary) / 'result.json').read_text())['documents'], [])

    def test_requests_share_a_serial_rate_budget(self):
        with TemporaryDirectory() as temporary, patch.object(tools, '_request_state', {'last_started': 8.0}), \
                patch.object(tools.time, 'monotonic', side_effect=[10.0, 11.1]), patch.object(tools.time, 'sleep') as sleep, \
                patch.object(tools, 'urlopen', return_value=http_response(FEED, 'https://export.arxiv.org/api/query')):
            tools.search_arxiv('ti:Mamba', temporary)
        self.assertAlmostEqual(sleep.call_args.args[0], 1.1)


if __name__ == '__main__':
    unittest.main()
