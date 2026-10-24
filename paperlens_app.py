"""下载版入口：同一程序派生worker，常驻本机服务，网页提供退出入口。"""
import hashlib
import html
import json
import os
from pathlib import Path
import signal
import sys
import traceback
from urllib.request import build_opener, ProxyHandler
import webbrowser

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['HF_HUB_DISABLE_XET'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

from src.runtime_paths import APP_VERSION, data_root


def main():
    # macOS 图形入口将标准流置空；worker 仍需使用父进程传入的管道。
    if sys.stdout is None: sys.stdout = open(1, 'w', encoding='utf-8', buffering=1)
    if sys.stderr is None: sys.stderr = open(2, 'w', encoding='utf-8', buffering=1)
    args = sys.argv[1:]
    if args == ['--self-check']:
        import torch, faiss, pymupdf, transformers, sentence_transformers
        import main as pipeline
        import agent
        from src import api_llm
        for module in (pipeline, agent, api_llm):
            if not Path(module.__file__).is_file(): raise RuntimeError('缺少运行身份所需源码文件。')
        result = {'version':APP_VERSION,'frozen':bool(getattr(sys,'frozen',False)),
                  'executable':sys.executable,'data_root':str(data_root()),
                  'python':sys.version,'torch':torch.__version__,'faiss':faiss.__version__,
                  'pdf':pymupdf.VersionBind,'transformers':transformers.__version__,
                  'sentence_transformers':sentence_transformers.__version__}
        print(json.dumps(result,ensure_ascii=False), flush=True)
        return
    from webui import server
    if args == ['--worker']:
        if sys.stdin is None: sys.stdin = open(0, encoding='utf-8')
        server.worker(); return
    if len(args) == 2 and args[0] == '--import-worker':
        server.library.build(Path(args[1])); return
    if args == ['--prepare-models']:
        server.model_assets.prepare(); return
    if args: raise ValueError('未知启动参数。')
    root = data_root(); (root/'logs').mkdir(parents=True, exist_ok=True)
    log = (root/'logs/launcher.log').open('a', encoding='utf-8', buffering=1)
    sys.stdout = log; sys.stderr = log
    url = f'http://127.0.0.1:{server.PORT}'
    try:
        try:
            with build_opener(ProxyHandler({})).open(url+'/api/meta', timeout=2) as response:
                existing = json.load(response)
        except OSError: existing = None
        if existing is not None:
            identity = hashlib.sha256(str(root).encode()).hexdigest()[:16]
            if existing.get('application') != 'PaperLens' or existing.get('data_id') != identity:
                raise RuntimeError('8849端口已被其他服务或另一个数据目录占用，请先退出该服务。')
            webbrowser.open(url); return
        def terminate(signum, frame): raise SystemExit(0)
        signal.signal(signal.SIGTERM, terminate)
        server.serve(open_browser=True)
    except Exception as exc:
        traceback.print_exc()
        message = str(exc) if isinstance(exc, RuntimeError) else '启动未完成，请查看本机日志。'
        error = root/'startup-error.html'
        error.write_text('<!doctype html><meta charset="utf-8"><title>PaperLens</title>'
                         '<h1>PaperLens 未能启动</h1><p>'+html.escape(message)+'</p><p>日志：'
                         +html.escape(str(root/'logs/launcher.log'))+'</p>', encoding='utf-8')
        webbrowser.open(error.as_uri())
        raise


if __name__ == '__main__':
    main()
