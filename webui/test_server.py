"""新版适配层的离线行为检查；不启动模型、不发网络请求。"""
import io
import json
from pathlib import Path
import tempfile
import socket
import threading
import urllib.request
import unittest
from unittest.mock import patch, Mock

from webui import server


def request(path, payload=None, origin=None, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode() if payload is not None else b''
    environ = {'PATH_INFO':path, 'REQUEST_METHOD':'POST' if payload is not None or raw is not None else 'GET',
               'CONTENT_TYPE':'application/json', 'CONTENT_LENGTH':str(len(body)), 'wsgi.input':io.BytesIO(body)}
    if origin:
        environ['HTTP_ORIGIN'] = origin
    response = []
    result = b''.join(server.app(environ, lambda status, headers: response.append((status, headers))))
    return int(response[0][0].split()[0]), result


class WebUIBehaviour(unittest.TestCase):
    def test_idle_connection_does_not_block_page(self):
        # 模拟浏览器先建立连接但暂不发送 HTTP 请求。
        with server.make_server('127.0.0.1', 0, server.app,
                                server_class=server.ThreadedServer) as httpd:
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                with socket.create_connection(httpd.server_address):
                    with urllib.request.urlopen(
                            f'http://127.0.0.1:{httpd.server_port}/api/meta', timeout=2) as response:
                        self.assertEqual(response.status, 200)
            finally:
                httpd.shutdown()
                thread.join(timeout=3)

    def test_concurrent_submissions_are_serialized(self):
        entered = threading.Event()
        release = threading.Event()
        calls = []
        results = []

        def create(payload):
            calls.append(payload)
            if len(calls) == 1:
                entered.set()
                release.wait(2)
                return 202, {'id':'one'}
            return 409, {'error':'busy'}

        with patch.object(server, 'start_job', side_effect=create):
            first = threading.Thread(target=lambda: results.append(request('/api/run', {'query':'a'})[0]))
            second = threading.Thread(target=lambda: results.append(request('/api/run', {'query':'b'})[0]))
            first.start()
            self.assertTrue(entered.wait(1))
            second.start()
            try:
                self.assertEqual(len(calls), 1)
            finally:
                release.set()
                first.join(3)
                second.join(3)
            self.assertEqual(sorted(results), [202, 409])

    def test_three_historical_results_keep_original_status_and_sources(self):
        for name, expected in [('transformer','completed'),('flash','completed'),('unavailable','degraded')]:
            code, raw = request('/api/examples/'+name)
            result = json.loads(raw)
            self.assertEqual(code, 200)
            self.assertEqual(result['status'], expected)
            self.assertEqual(result['origin'], 'saved')
            self.assertTrue(result['citations'])
            self.assertNotIn('api_key', result)
        self.assertEqual(result['answer_status'], 'source_unavailable')

    def test_metadata_exposes_no_private_configuration(self):
        code, raw = request('/api/meta')
        meta = json.loads(raw)
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(meta['papers']), 8)
        self.assertGreaterEqual(meta['chunks'], 1397)
        self.assertFalse({'api_key','base_url','chat_options'} & set(meta))

    def test_invalid_requests_never_launch_worker(self):
        with patch.object(server.subprocess, 'Popen') as launch:
            for payload in [{'query':''},{'query':42},{'query':'x'*2001},
                            {'query':'x','mode':'bad'},{'query':'x','mode':'rag','allow_network':True},
                            {'query':'x','allow_network':'yes'}]:
                self.assertEqual(request('/api/run',payload)[0],400)
            self.assertEqual(request('/api/run',raw=b'{bad')[0],400)
            self.assertEqual(request('/api/run',raw=b'[]')[0],400)
            launch.assert_not_called()

    def test_cross_origin_request_cannot_launch_worker(self):
        with patch.object(server.subprocess, 'Popen') as launch:
            self.assertEqual(request('/api/run',{'query':'x'},origin='https://example.com')[0],403)
            launch.assert_not_called()

    def test_busy_server_rejects_second_submission(self):
        process = Mock(); process.poll.return_value = None
        with patch.dict(server.JOBS, {'existing':{'process':process}}, clear=True), patch.object(server.subprocess,'Popen') as launch:
            self.assertEqual(request('/api/run',{'query':'x'})[0],409)
            launch.assert_not_called()

    def test_polling_does_not_spawn_or_rerun(self):
        process = Mock(); process.poll.return_value = None
        with patch.dict(server.JOBS, {'known':{'process':process,'started':server.time.monotonic()}},clear=True), patch.object(server.subprocess,'Popen') as launch:
            for _ in range(2):
                code, body=request('/api/jobs/known')
                self.assertEqual(code,200)
                self.assertEqual(json.loads(body)['status'],'running')
            launch.assert_not_called()

    def test_worker_exit_without_result_has_explicit_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            process=Mock();process.poll.return_value=1
            job={'process':process,'started':server.time.monotonic(),'folder':Path(folder),'query':'x','mode':'rag'}
            with patch.dict(server.JOBS,{'known':job},clear=True):
                code, raw=request('/api/jobs/known'); result=json.loads(raw)['result']
                self.assertEqual(code,200)
                self.assertEqual(result['status'],'failed')
                self.assertEqual(result['stop_reason'],'worker_failed')
                self.assertTrue(result['answer'])

    def test_unknown_job_and_private_paths_are_not_exposed(self):
        for path in ['/api/jobs/not-real','/api.local.json','/../api.local.json','/api/examples/not-real']:
            self.assertEqual(request(path)[0],404)

    def test_internal_error_is_readable_without_private_details(self):
        with patch.object(server,'metadata',side_effect=RuntimeError('private detail')):
            code, raw=request('/api/meta')
            self.assertEqual(code,500)
            self.assertNotIn(b'private detail',raw)


if __name__ == '__main__':
    unittest.main()
