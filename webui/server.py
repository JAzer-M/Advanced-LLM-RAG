"""新版前端的轻量适配层；问答和公开展示字段复用已验证的后端函数。"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from uuid import uuid4
from socketserver import ThreadingMixIn
from threading import Lock
from wsgiref.simple_server import make_server, WSGIServer

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
# 只复用数据适配/worker，不加载旧 HTML、CSS、JS，不更改检索及回答实现。
from ui_prototype.app import metadata as baseline_metadata, example_result as saved_example, public_result, EXAMPLES
from webui import library

PORT = 8849
JOBS = {}
IMPORTS = {}
JOB_LOCK = Lock()
SETTINGS_PATH = ROOT / 'api.local.json'


def metadata():
    return {**baseline_metadata(), **library.catalog()}


def start_import(payload):
    if any(p.poll() is None for p in IMPORTS.values()):
        return 409, {'error':'已有导入正在进行，请稍后再试。'}
    identity, folder = library.prepare(payload)
    env = {**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
           'VECLIB_MAXIMUM_THREADS':'1','TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    with (folder/'console.log').open('w') as log:
        process = subprocess.Popen([sys.executable,str(HERE/'server.py'),'--import-worker',str(folder)],
                                   stdout=log,stderr=log,cwd=ROOT,env=env)
    IMPORTS[identity] = process
    library.atomic_json(folder/'process.json',{'pid':process.pid})
    return 202, {'id':identity}


def import_status(identity):
    if len(identity)!=32 or any(c not in '0123456789abcdef' for c in identity):
        return 404, {'error':'找不到导入任务。'}
    folder=ROOT/'data/webui/imports'/identity
    if not (folder/'status.json').is_file(): return 404, {'error':'找不到导入任务。'}
    value=json.loads((folder/'status.json').read_text())
    if value['status']=='running':
        process=IMPORTS.get(identity)
        alive=process.poll() is None if process else False
        if not process and (folder/'process.json').exists():
            try: os.kill(json.loads((folder/'process.json').read_text())['pid'],0); alive=True
            except ProcessLookupError: pass
        if not alive:
            value.update(status='failed',stage='导入进程已中断',error='请重新选择文件导入；已有知识库仍保留。')
    return 200, value


def worker():
    payload=json.load(sys.stdin); folder=Path(payload['folder']); started=time.monotonic()
    try:
        import torch
        torch.set_num_threads(1); torch.set_num_interop_threads(1)
        import main as pipeline
        options={'mode':payload['mode'],'kb_version':payload['kb_version'],'allow_network':payload['allow_network']}
        if payload['mode']!='rag': options['output_dir']=folder/'pipeline'
        result=pipeline.main(payload['query'],**options)
    except Exception as exc:
        result={'query':payload['query'],'mode':payload['mode'],'status':'failed','answer':'本次处理未完成，请检查运行日志。','error':f'{type(exc).__name__}: {exc}'}
    result['ui_elapsed']=round(time.monotonic()-started,2)
    library.atomic_json(folder/'result.json',result)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_models(payload):
    """用待保存的地址查询模型；不保存配置，也不生成回答。"""
    settings = json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.is_file() else {}
    base, key = payload.get('base_url', ''), payload.get('api_key', '')
    if not isinstance(base, str) or not isinstance(key, str):
        return 400, {'error': '地址和密钥必须是文字。'}
    base, key = base.strip().rstrip('/'), key.strip()
    try:
        url = urlsplit(base)
        url.port
        valid = (url.scheme in ('http', 'https') and url.hostname and not url.username and not url.password
                 and not url.query and not url.fragment and not any(c.isspace() for c in base)
                 and (url.scheme == 'https' or url.hostname in ('127.0.0.1', 'localhost', '::1')))
    except ValueError:
        valid = False
    if not valid or len(base) > 2000 or len(key) > 4096 or any(c in key for c in '\r\n'):
        return 400, {'error': '请检查 API 基础地址和密钥格式；远程服务需使用 HTTPS。'}
    if not key:
        if base != settings.get('base_url', '').rstrip('/'):
            return 400, {'error': '地址已改变，请填写此地址对应的 API Key，不会将旧密钥发送给新地址。'}
        key = os.environ.get('RAG_API_KEY') or settings.get('api_key', '')
    if not key:
        return 400, {'error': '请填写 API Key 后获取模型。'}
    try:
        # 拒绝重定向，避免鉴权头被带到另一个服务。
        with build_opener(NoRedirect()).open(Request(base + '/models', headers={'Authorization': 'Bearer ' + key}), timeout=10) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('response too large')
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get('data'), list):
            raise ValueError('invalid model list')
        models = sorted({item['id'] for item in data['data'] if isinstance(item, dict)
                         and isinstance(item.get('id'), str) and 0 < len(item['id']) <= 200})
        return 200, {'models': models}
    except HTTPError as exc:
        message = {401:'密钥无效或已失效。',403:'此密钥没有读取模型列表的权限。',404:'服务未提供 /models 接口，可手动填写模型 ID。',429:'服务限流，请稍后再试。'}.get(exc.code, '模型列表请求失败，服务未返回可用列表。')
        return 502, {'error': message}
    except (URLError, TimeoutError, OSError):
        return 502, {'error': '连接模型服务失败或超时，请检查地址与网络。'}
    except (ValueError, UnicodeError):
        return 502, {'error': '服务返回的模型列表格式不兼容，可手动填写模型 ID。'}


def result_details(public, raw, folder):
    """只从已有记录提取路径和本地需求覆盖，不将复核等同事实正确。"""
    public['route'] = ('RAG → Agent' if raw.get('agent', {}).get('invoked') else 'RAG') if raw.get('mode') == 'auto' else public['mode'].upper()
    if public['network']['papers_read']:
        public['route'] += ' → arXiv'
    folder = folder / 'pipeline' if (folder / 'pipeline').is_dir() else folder
    loop = folder / 'loop/question.json'
    public['local_coverage'] = None
    if loop.is_file():
        rows = json.loads(loop.read_text()).get('final_assessment', {}).get('requirements', [])
        if rows:
            public['local_coverage'] = {'total': len(rows), 'supported': sum(row.get('status') == 'supported' for row in rows)}
    return public


def example_result(identity):
    path = ROOT / EXAMPLES[identity]['path']
    return result_details(saved_example(identity), json.loads(path.read_text()), path.parent)


def model_config(payload=None):
    """只回传公开配置；密钥留空表示保留，写入原子替换且仅本机用户可读。"""
    settings = json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.is_file() else {}
    if payload is not None:
        if any(job['process'].poll() is None for job in JOBS.values()):
            return 409, {'error': '请等待当前问答结束后再修改模型配置。'}
        base, model, key = (payload.get(name, '') for name in ('base_url', 'model', 'api_key'))
        if not all(isinstance(item, str) for item in (base, model, key)):
            return 400, {'error': '配置字段必须是文字。'}
        base, model, key = base.strip().rstrip('/'), model.strip(), key.strip()
        url = urlsplit(base)
        if (url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password
                or url.query or url.fragment or any(c.isspace() for c in base)
                or (url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1', '::1'))):
            return 400, {'error': '请输入 HTTPS API 基础地址（本机服务可用 HTTP），不要包含密钥或查询参数。'}
        if not model or len(model) > 200 or len(base) > 2000 or len(key) > 4096 or any(c in key + model for c in '\r\n'):
            return 400, {'error': '请检查模型名、地址和密钥格式。'}
        if not (key or settings.get('api_key') or os.environ.get('RAG_API_KEY')):
            return 400, {'error': '首次配置需要填写 API Key。'}
        if key and os.environ.get('RAG_API_KEY'):
            return 400, {'error': '当前使用环境变量密钥，请先在启动环境中修改 RAG_API_KEY。'}
        if base != settings.get('base_url', '').rstrip('/') and not key:
            return 400, {'error': '地址已改变，请填写新地址对应的密钥；不能沿用旧地址的密钥。'}
        if base != settings.get('base_url', '').rstrip('/') and os.environ.get('RAG_API_KEY'):
            return 400, {'error': '环境变量密钥已绑定当前地址，请在启动环境中同步调整配置。'}
        settings.update(base_url=base, model=model)
        if key:
            settings['api_key'] = key
        # 其他已有参数保持原样，不在网页中暴露或修改。
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=SETTINGS_PATH.parent,
                                             prefix='.api-settings-', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(settings, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
            temporary.replace(SETTINGS_PATH)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
    base = settings.get('base_url', '')
    parsed = urlsplit(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        base = ''
    return 200, {'base_url': base, 'model': settings.get('model', ''),
                 'has_key': bool(os.environ.get('RAG_API_KEY') or settings.get('api_key')),
                 'key_source': 'environment' if os.environ.get('RAG_API_KEY') else 'file',
                 'has_options': bool(settings.get('chat_options'))}


class ThreadedServer(ThreadingMixIn, WSGIServer):
    """浏览器预连接不阻塞其他请求；任务创建仍由锁保证单任务。"""
    daemon_threads = True

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(15)
        return connection, address


def start_job(payload):
    """单用户、单任务；新运行独立落盘，拒绝重复并发请求。"""
    query = payload.get('query', '')
    mode = payload.get('mode', 'auto')
    network = payload.get('allow_network', False)
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 2000:
        return 400, {'error': '请输入 1～2000 字的问题。'}
    if mode not in ('rag', 'auto', 'agent') or type(network) is not bool or (mode == 'rag' and network):
        return 400, {'error': '模式无效；RAG 仅使用本地论文。'}
    if any(job['process'].poll() is None for job in JOBS.values()):
        return 409, {'error': '已有问题正在处理，请等待当前任务结束。'}
    identity = uuid4().hex
    folder = ROOT / 'logs/webui' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + identity[:8])
    folder.mkdir(parents=True)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1',
           'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'VECLIB_MAXIMUM_THREADS': '1',
           'TOKENIZERS_PARALLELISM': 'false', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    # 父进程立即关闭自己的日志句柄；子进程持有副本，轮询不反复关闭文件。
    with (folder / 'console.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(HERE / 'server.py'), '--worker'],
                                   stdin=subprocess.PIPE, stdout=log, stderr=log, cwd=ROOT,
                                   env=env, text=True)
    JOBS[identity] = {'process': process, 'folder': folder, 'query': query.strip(),
                      'mode': mode, 'started': time.monotonic()}
    try:
        process.stdin.write(json.dumps({'query': query.strip(), 'mode': mode,
                                       'allow_network': network, 'folder': str(folder),
                                       'kb_version':library.current()['version']}, ensure_ascii=False))
    finally:
        process.stdin.close()
    return 202, {'id': identity, 'status': 'running'}


def job_status(identity):
    job = JOBS[identity]
    elapsed = round(time.monotonic() - job['started'], 1)
    if job['process'].poll() is None:
        return {'id': identity, 'status': 'running', 'elapsed': elapsed}
    path = job['folder'] / 'result.json'
    result = json.loads(path.read_text()) if path.is_file() else {
        'query': job['query'], 'mode': job['mode'], 'status': 'failed',
        'answer_status': 'unavailable', 'stop_reason': 'worker_failed',
        'answer': '本次问答进程未完成。运行日志已保留，请检查后再手动尝试。'}
    return {'id': identity, 'status': 'finished',
            'result': result_details(public_result(result, job['folder'], 'live', elapsed=result.get('ui_elapsed', elapsed)), result, job['folder'])}


def app(environ, start_response):
    path, method = environ['PATH_INFO'], environ['REQUEST_METHOD']
    code, value = 404, {'error': '没有找到对应页面或任务。'}
    content_type = 'application/json; charset=utf-8'
    try:
        if method == 'GET' and path in ('/', '/app.js', '/style.css'):
            name = 'index.html' if path == '/' else path[1:]
            content_type = {'index.html': 'text/html', 'app.js': 'text/javascript', 'style.css': 'text/css'}[name] + '; charset=utf-8'
            code, value = 200, (HERE / name).read_bytes()
        elif method == 'GET' and path == '/api/meta':
            code, value = 200, metadata()
        elif method == 'GET' and path == '/api/config':
            with JOB_LOCK:
                code, value = model_config()
        elif method == 'GET' and path.startswith('/api/imports/'):
            code, value = import_status(path.rsplit('/',1)[-1])
        elif method == 'GET' and path.startswith('/api/examples/'):
            identity = path.rsplit('/', 1)[-1]
            if identity in EXAMPLES:
                code, value = 200, example_result(identity)
        elif method == 'GET' and path.startswith('/api/jobs/'):
            identity = path.rsplit('/', 1)[-1]
            if identity in JOBS:
                code, value = 200, job_status(identity)
        elif method == 'POST' and path in ('/api/run', '/api/config', '/api/models', '/api/imports'):
            origin = environ.get('HTTP_ORIGIN')
            if origin and origin not in (f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
                code, value = 403, {'error': '请从本机研究台发送问题。'}
            elif environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
                code, value = 415, {'error': '请求必须使用 JSON。'}
            else:
                try:
                    length = int(environ.get('CONTENT_LENGTH') or 0)
                    if not 0 < length <= (29 * 1024 * 1024 if path == '/api/imports' else 16384):
                        raise ValueError('Invalid length')
                    payload = json.loads(environ['wsgi.input'].read(length))
                    if not isinstance(payload, dict):
                        raise ValueError('Invalid payload')
                    if path == '/api/models':
                        code, value = fetch_models(payload)
                    else:
                        with JOB_LOCK:
                            if path == '/api/imports': code, value = start_import(payload)
                            else: code, value = model_config(payload) if path == '/api/config' else start_job(payload)
                except (ValueError, TypeError):
                    code, value = 400, {'error': '无法读取输入，请检查格式。PDF每批1～5篇，总大小不超过20MB。' if path=='/api/imports' else '无法读取输入，请检查格式。'}
    except Exception as exc:
        # 不把内部异常/绝对路径发送到页面，细节留在启动终端。
        print(f'Web UI request failed: {type(exc).__name__}', file=sys.stderr, flush=True)
        code, value = 500, {'error': '本地服务暂时未能完成请求，请查看启动终端。'}
    body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
    names = {200:'OK',202:'Accepted',400:'Bad Request',403:'Forbidden',404:'Not Found',409:'Conflict',415:'Unsupported Media Type',500:'Internal Server Error',502:'Bad Gateway'}
    start_response(f'{code} {names[code]}', [('Content-Type',content_type),('Content-Length',str(len(body))),
                   ('Cache-Control','no-store'),('X-Content-Type-Options','nosniff')])
    return [body]


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        worker()
    elif len(sys.argv)==3 and sys.argv[1]=='--import-worker':
        library.build(Path(sys.argv[2]))
    else:
        print(f'PaperLens 新版研究台：http://127.0.0.1:{PORT}', flush=True)
        print('保持终端打开。案例回放不调用模型，发送问题会使用现有 API。', flush=True)
        with make_server('127.0.0.1', PORT, app, server_class=ThreadedServer) as server:
            server.serve_forever()
