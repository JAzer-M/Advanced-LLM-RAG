"""源码和打包程序共享路径约定；测试只使用临时目录，不读私有配置。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.runtime_paths import data_root, model_location, source_root, worker_command


class RuntimeTests(unittest.TestCase):
    def test_source_checkout_keeps_original_paths(self):
        with patch.dict(os.environ, {'PAPERLENS_DATA_DIR':''}), patch.object(sys, 'frozen', False, create=True):
            self.assertEqual(data_root(), Path(__file__).resolve().parents[1])
            self.assertEqual(model_location('BAAI/bge-reranker-base'), 'BAAI/bge-reranker-base')

    def test_frozen_app_uses_user_data_outside_bundle(self):
        with patch.dict(os.environ, {'PAPERLENS_DATA_DIR':''}), patch.object(sys, 'frozen', True, create=True), \
                patch.object(sys, 'platform', 'darwin'), patch('pathlib.Path.home', return_value=Path('/test/home')):
            self.assertEqual(data_root(), Path('/test/home/Library/Application Support/PaperLens'))
            self.assertNotEqual(data_root(), source_root())

    def test_frozen_windows_app_uses_local_app_data(self):
        with patch.dict(os.environ, {'PAPERLENS_DATA_DIR':'', 'LOCALAPPDATA':'/test/local'}), \
                patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'platform', 'win32'):
            self.assertEqual(data_root(), Path('/test/local/PaperLens'))

    def test_data_override_is_shared_by_server_library_and_api(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = str(Path(folder).resolve())
            code = ('import json; from webui import server, library; from src import api_llm; '
                    'print(json.dumps([str(server.ROOT),str(library.ROOT),str(api_llm.SETTINGS_PATH)]))')
            raw = subprocess.check_output([sys.executable, '-B', '-c', code],
                                          env={**os.environ, 'PAPERLENS_DATA_DIR':folder}, text=True)
            self.assertEqual(json.loads(raw), [folder, folder, str(Path(folder)/'api.local.json')])

    def test_frozen_worker_relaunches_executable_without_python_script(self):
        with patch.object(sys, 'frozen', True, create=True):
            self.assertEqual(worker_command('--import-worker', '/test/job'),
                             [sys.executable, '--import-worker', '/test/job'])
        with patch.object(sys, 'frozen', False, create=True):
            self.assertEqual(worker_command('--worker'),
                             [sys.executable, str(source_root()/'webui/server.py'), '--worker'])

    def test_managed_models_live_with_user_data(self):
        with patch.dict(os.environ, {'PAPERLENS_DATA_DIR':'/test/paperlens'}):
            expected = Path('/test/paperlens').resolve()/'models/BAAI--bge-reranker-base/2cfc18c9415c912f9d8155881c133215df768a70'
            self.assertEqual(model_location('BAAI/bge-reranker-base'), str(expected))


if __name__ == '__main__':
    unittest.main()
