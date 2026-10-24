"""源码沿用项目目录；下载版把可写数据放在用户目录，资源留在应用包。"""
import os
from pathlib import Path
import sys

APP_VERSION = '0.2.0'

MODEL_REVISIONS = {
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2':'e8f8c211226b894fcb81acc59f3b34ba3efd5f42',
    'BAAI/bge-reranker-base':'2cfc18c9415c912f9d8155881c133215df768a70',
}


def source_root():
    return Path(__file__).resolve().parents[1]


def managed_models():
    return bool(getattr(sys, 'frozen', False) or os.environ.get('PAPERLENS_DATA_DIR'))


def data_root():
    override = os.environ.get('PAPERLENS_DATA_DIR')
    if override: return Path(override).expanduser().resolve()
    if getattr(sys, 'frozen', False):
        if sys.platform == 'win32':
            return Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData/Local')/'PaperLens'
        return Path.home()/'Library/Application Support/PaperLens'
    return source_root()


def model_location(name):
    return str(data_root()/'models'/name.replace('/', '--')/MODEL_REVISIONS[name]) if managed_models() else name


def worker_command(*args):
    if getattr(sys, 'frozen', False): return [sys.executable, *args]
    return [sys.executable, str(source_root()/'webui/server.py'), *args]
