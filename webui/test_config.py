"""只用临时配置和本地假 API；不更改用户配置、不调用付费模型。"""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock
from http.server import BaseHTTPRequestHandler, HTTPServer
from webui import server
from webui.test_server import request
from src import api_llm


class ModelConfigTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'settings.json'
        self.path.write_text(json.dumps({'api_key':'test-secret', 'base_url':'https://example.test/v1',
                                         'model':'old', 'chat_options':{'temperature':0.2}}))
        for context in (patch.object(server, 'SETTINGS_PATH', self.path),
                        patch.dict(server.JOBS, {}, clear=True), patch.dict(os.environ, {}, clear=True)):
            context.start()
            self.addCleanup(context.stop)

    def test_models_uses_draft_credentials_without_saving(self):
        from unittest.mock import Mock
        response=Mock();response.read.return_value=b'{"data":[{"id":"b"},{"id":"a"},{"id":"b"}]}'
        opener=MagicMock();opener.open.return_value.__enter__.return_value=response
        original=self.path.read_bytes()
        with patch.object(server,'build_opener',return_value=opener):
            code,raw=request('/api/models',{'base_url':'https://new.test/v1','api_key':'draft-key'})
        self.assertEqual(code,200)
        self.assertEqual(json.loads(raw)['models'],['a','b'])
        sent=opener.open.call_args.args[0]
        self.assertEqual(sent.full_url,'https://new.test/v1/models')
        self.assertEqual(sent.get_header('Authorization'),'Bearer draft-key')
        self.assertEqual(self.path.read_bytes(),original)
        self.assertNotIn(b'draft-key',raw)

    def test_models_does_not_forward_saved_key_to_changed_address(self):
        with patch.object(server,'build_opener') as opener:
            self.assertEqual(request('/api/models',{'base_url':'https://other.test/v1'})[0],400)
            self.assertEqual(request('/api/models',{'base_url':'https://example.test/v1'},origin='https://evil.test')[0],403)
            opener.assert_not_called()

    def test_models_errors_do_not_expose_upstream_body(self):
        from urllib.error import HTTPError
        from unittest.mock import Mock
        opener=Mock();opener.open.side_effect=HTTPError('https://example.test',401,'secret body',{},None)
        with patch.object(server,'build_opener',return_value=opener):
            code,raw=request('/api/models',{'base_url':'https://example.test/v1'})
        self.assertEqual(code,502)
        self.assertNotIn(b'secret',raw)

    def test_public_read_never_returns_secret(self):
        status, raw = request('/api/config')
        self.assertEqual(status, 200)
        self.assertNotIn(b'test-secret', raw)
        self.assertNotIn('api_key', json.loads(raw))

    def test_save_preserves_key_and_options_and_private_permissions(self):
        status, raw = request('/api/config', {'base_url':'https://example.test/v1/', 'model':'new', 'api_key':''})
        self.assertEqual(status, 200)
        data = json.loads(self.path.read_text())
        self.assertEqual(data['api_key'], 'test-secret')
        self.assertEqual(data['model'], 'new')
        self.assertEqual(data['chat_options'], {'temperature':0.2})
        if os.name != 'nt':  # Windows 没有 POSIX 权限位，chmod 只能控制只读，无法表达 0600
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(b'test-secret', raw)

    def test_rejects_bad_and_cross_origin_config_without_mutation(self):
        original = self.path.read_bytes()
        for base in ['http://external.test/v1','https://u:secret@host/v1','https://host/v1?key=secret','file:///tmp/a']:
            self.assertEqual(request('/api/config', {'base_url':base, 'model':'x'})[0],400)
        self.assertEqual(request('/api/config', {'base_url':'https://host/v1','model':'x'},origin='https://evil.test')[0],403)
        self.assertEqual(self.path.read_bytes(), original)

    def test_busy_config_and_environment_key_are_explicit(self):
        from unittest.mock import Mock
        process=Mock();process.poll.return_value=None
        with patch.dict(server.JOBS, {'one':{'process':process}}):
            self.assertEqual(request('/api/config', {'base_url':'https://host/v1','model':'x'})[0],409)
        with patch.dict(os.environ, {'RAG_API_KEY':'environment-secret'}):
            self.assertEqual(request('/api/config', {'base_url':'https://host/v1','model':'x','api_key':'replacement'})[0],400)
            self.assertEqual(json.loads(request('/api/config')[1])['key_source'], 'environment')

    def test_saved_config_is_used_by_existing_generation_client(self):
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append((self.path, self.headers['Authorization'], json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                body=json.dumps({'choices':[{'message':{'content':'local fixture answer'},'finish_reason':'stop'}], 'model':'new-model'}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def log_message(self,*args): pass
        with HTTPServer(('127.0.0.1',0),Handler) as httpd:
            thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
            try:
                self.assertEqual(request('/api/config', {'base_url':f'http://127.0.0.1:{httpd.server_port}/v1','model':'new-model','api_key':'new-test-key'})[0],200)
                with patch.object(api_llm,'SETTINGS_PATH',self.path):
                    self.assertEqual(api_llm.chat_completion('test')['answer'],'local fixture answer')
            finally:
                httpd.shutdown();thread.join(3)
        self.assertEqual(received[0][0], '/v1/chat/completions')
        self.assertEqual(received[0][1], 'Bearer new-test-key')
        self.assertEqual(received[0][2]['model'], 'new-model')

if __name__ == '__main__': unittest.main()
