"""首次模型准备的文件/进程边界；不下载权重、不请求生成服务。"""
import json
import base64
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import model_assets
from src.runtime_paths import MODEL_REVISIONS, model_location
from webui import server
from webui.test_server import request


class ModelAssetsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.env = patch.dict(os.environ, {'PAPERLENS_DATA_DIR':str(self.root)})
        self.env.start(); self.addCleanup(self.env.stop)

    def test_cold_install_reports_missing_models(self):
        state = model_assets.status()
        self.assertTrue(state['enabled'])
        self.assertEqual(state['status'], 'missing')
        self.assertGreater(state['total_bytes'], 1_500_000_000)

    def test_ready_marker_requires_all_versioned_files(self):
        for repo, files in model_assets.MODEL_FILES.items():
            folder = Path(model_location(repo)); folder.mkdir(parents=True)
            for name, size in files.items():
                path = folder/name; path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('wb') as stream: stream.truncate(size)
        (self.root/'models/ready.json').write_text(json.dumps(MODEL_REVISIONS))
        self.assertEqual(model_assets.status()['status'], 'ready')
        (Path(model_location('BAAI/bge-reranker-base'))/'model.safetensors').unlink()
        self.assertEqual(model_assets.status()['status'], 'missing')

    def test_interrupted_preparation_is_retryable_failure(self):
        folder=self.root/'models'; folder.mkdir()
        (folder/'setup.json').write_text(json.dumps({'status':'running','phase':'download'}))
        (folder/'process.json').write_text(json.dumps({'pid':123456789}))
        with patch.object(model_assets, 'pid_alive', return_value=False):
            state=model_assets.status()
        self.assertEqual(state['status'], 'failed')
        self.assertTrue(state['error'])

    def test_download_failure_is_visible_and_never_publishes_ready(self):
        with patch('huggingface_hub.hf_hub_download', side_effect=TimeoutError('fixture download timeout')):
            with self.assertRaises(TimeoutError): model_assets.prepare()
        self.assertEqual(model_assets.status()['status'], 'failed')
        self.assertFalse((self.root/'models/ready.json').exists())
        self.assertFalse((self.root/'data').exists())

    def test_missing_models_reject_import_before_worker_launch(self):
        payload={'files':[{'name':'test.pdf','data':base64.b64encode(b'%PDF-1.7 fixture').decode()}]}
        with patch.object(server, 'ROOT', self.root), patch.object(server.library, 'ROOT', self.root), \
                patch.dict(server.IMPORTS, {}, clear=True), patch.object(server.subprocess, 'Popen') as launch:
            launch.return_value.pid=123
            code, raw=request('/api/imports', payload)
            self.assertEqual(code, 400)
            self.assertIn('模型', json.loads(raw)['error'])
            launch.assert_not_called()
            self.assertFalse((self.root/'data').exists())

    def test_model_download_endpoint_rejects_cross_origin(self):
        with patch.object(server.subprocess, 'Popen') as launch:
            self.assertEqual(request('/api/setup', {}, origin='https://example.com')[0], 403)
            launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
