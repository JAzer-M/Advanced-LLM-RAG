# 本地UI试验：普通WSGI函数、内存任务字典、独立问答进程；不改变生产检索/回答代码。
# 启动/回放不调用模型；用户点击实时运行后，才复用main及原调用预算。
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
PORT = 8848
KB_VERSION = 'all-papers-8-20261020'
JOBS = {}
EXAMPLES = {
    'flash': {'title': 'FlashAttention 如何减少显存读写？', 'tag': '联网补证据',
              'date': '2026-10-22', 'path': 'evaluation/results/p3_validation_20261022/live/n04/agent_on/result.json'},
    'transformer': {'title': 'Transformer 的前馈网络由什么组成？', 'tag': '本地回答',
                    'date': '2026-10-22', 'path': 'evaluation/results/p3_validation_20261022/live/n01/agent_off/result.json'},
    'unavailable': {'title': '外部论文暂时无法获取时，会怎样？', 'tag': '来源不可用',
                    'date': '2026-10-23', 'path': 'evaluation/results/backend_reliability_20261023/live/main/result.json'},
}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def public_result(result, folder, origin, title=None, date=None, elapsed=None):
    """页面只接收展示字段；配置、密钥、模型提示词和绝对本机路径不发送到浏览器。"""
    if (folder / 'pipeline').is_dir():
        folder = folder / 'pipeline'
    search_path = folder / 'network/search/result.json'
    titles = {f"{paper['arxiv_id']}.pdf": paper['title'] for paper in
              (read_json(search_path).get('papers', []) if search_path.is_file() else [])}
    passages = result.get('ledger', {}).get('citation_registry', [])
    network = result.get('network', {})
    answer_status = (result.get('answer_status') or network.get('answer_status') or
                     result.get('agent', {}).get('answer_summary', {}).get('answer_status') or 'not_reviewed')
    citations = []
    for number, passage in enumerate(passages, 1):
        item = {key: passage.get(key) for key in ('source', 'page', 'title', 'section', 'text', 'origin')}
        item['title'] = titles.get(passage.get('source'), item['title'])
        item['number'] = number
        url = passage.get('url', '')
        if url.startswith('https://arxiv.org/'):
            item['url'] = url
        citations.append(item)
    actions = []
    loop = folder / 'loop/question.json'
    if loop.is_file():
        for step in read_json(loop).get('steps', []):
            actions.append({'tool': step['action']['type'], 'status': step['status']})
    for tool in ('search', 'read'):
        path = folder / f'network/{tool}/result.json'
        if path.is_file():
            item = read_json(path)
            actions.append({'tool': item['tool'], 'status': item['status']})
    return {'query': result.get('query', ''), 'mode': result.get('mode', 'rag'),
            'status': result.get('status', 'failed'), 'answer_status': answer_status,
            'stop_reason': result.get('stop_reason') or result.get('agent', {}).get('halt_reason', ''),
            'answer': result.get('answer') or '本次运行未生成答案，请查看运行状态。',
            'citations': citations, 'actions': actions, 'api_summary': result.get('api_summary', {}),
            'network': {'status': network.get('status', 'not_requested'),
                        'papers_read': network.get('papers_read', 0),
                        'http_tool_calls': network.get('http_tool_calls', 0)},
            'origin': origin, 'title': title, 'date': date, 'elapsed': elapsed,
            'kb_version': result.get('knowledge_base', {}).get('version', KB_VERSION)}


def example_result(identity):
    example = EXAMPLES[identity]
    path = ROOT / example['path']
    elapsed = None
    summary_path = path.parents[2] / 'summary.json'
    if identity == 'unavailable':
        summary_path = path.parents[1] / 'summary.json'
    if summary_path.is_file():
        summary = read_json(summary_path)
        elapsed = summary.get('seconds')
        for row in summary.get('runs', []):
            if row.get('id') == path.parents[1].name and row.get('arm') == path.parent.name:
                elapsed = row.get('seconds')
    return public_result(read_json(path), path.parent, 'saved', example['title'], example['date'], elapsed)


def metadata():
    chunks = read_json(ROOT / f'data/processed/versions/{KB_VERSION}/chunks.json')
    catalog = {}
    for chunk in chunks:
        entry = catalog.setdefault(chunk['source'], {'source': chunk['source'], 'title': chunk['title'], 'chunks': 0})
        entry['chunks'] += 1
    settings_path = ROOT / 'api.local.json'
    settings = read_json(settings_path) if settings_path.is_file() else {}
    return {'papers': list(catalog.values()), 'chunks': len(chunks), 'kb_version': KB_VERSION,
            'model': settings.get('model'),
            'configured': bool(settings.get('model') and (os.environ.get('RAG_API_KEY') or settings.get('api_key'))),
            'examples': [{'id': identity, **{k: item[k] for k in ('title', 'tag', 'date')}}
                         for identity, item in EXAMPLES.items()]}


def job_status(identity):
    job = JOBS[identity]
    elapsed = round(time.monotonic() - job['started'], 1)
    if job['process'].poll() is None:
        return {'id': identity, 'status': 'running', 'elapsed': elapsed}
    job['log'].close()
    path = job['folder'] / 'result.json'
    result = read_json(path) if path.is_file() else {
        'status': 'failed', 'query': job['query'], 'mode': job['mode'],
        'answer': '问答进程未完成，请查看本次运行日志后再手动尝试。'}
    return {'id': identity, 'status': 'finished',
            'result': public_result(result, job['folder'], 'live', elapsed=result.get('ui_elapsed', elapsed))}


def start_job(payload):
    question = payload.get('query', '')
    mode = payload.get('mode', 'auto')
    network = payload.get('allow_network', False)
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
        return 400, {'error': '请输入问题，长度不超过2000个字符。'}
    if mode not in {'rag', 'agent', 'auto'} or type(network) is not bool or (mode == 'rag' and network):
        return 400, {'error': '请选择有效模式；固定RAG只使用本地知识库。'}
    if any(job['process'].poll() is None for job in JOBS.values()):
        return 409, {'error': '已有问题正在运行，请等待本次结束。'}
    identity = uuid4().hex
    folder = ROOT / 'logs/ui_prototype' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + identity[:8])
    folder.mkdir(parents=True)
    log = (folder / 'console.log').open('w', encoding='utf-8')
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1',
           'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'VECLIB_MAXIMUM_THREADS': '1',
           'TOKENIZERS_PARALLELISM': 'false', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    process = subprocess.Popen([str(ROOT/'.venv/bin/python'), str(Path(__file__).resolve()), '--worker'],
                               stdin=subprocess.PIPE, stdout=log, stderr=log, cwd=ROOT, env=env, text=True)
    process.stdin.write(json.dumps({'query': question.strip(), 'mode': mode,
                                   'allow_network': network, 'folder': str(folder)}, ensure_ascii=False))
    process.stdin.close()
    JOBS[identity] = {'process': process, 'folder': folder, 'log': log,
                      'started': time.monotonic(), 'query': question.strip(), 'mode': mode}
    return 202, {'id': identity, 'status': 'running'}


def app(environ, start_response):
    path = environ['PATH_INFO']
    method = environ['REQUEST_METHOD']
    code, value = 404, {'error': '未找到此页面。'}
    content_type = 'application/json; charset=utf-8'
    if method == 'GET' and path in {'/', '/app.js', '/style.css'}:
        name = 'index.html' if path == '/' else path[1:]
        content_type = {'index.html': 'text/html', 'app.js': 'text/javascript', 'style.css': 'text/css'}[name] + '; charset=utf-8'
        code, value = 200, (HERE / name).read_bytes()
    elif method == 'GET' and path == '/api/meta':
        code, value = 200, metadata()
    elif method == 'GET' and path.startswith('/api/examples/'):
        identity = path.rsplit('/', 1)[-1]
        if identity in EXAMPLES:
            code, value = 200, example_result(identity)
    elif method == 'GET' and path.startswith('/api/jobs/'):
        identity = path.rsplit('/', 1)[-1]
        if identity in JOBS:
            code, value = 200, job_status(identity)
    elif method == 'POST' and path == '/api/run':
        origin = environ.get('HTTP_ORIGIN')
        if origin and origin not in {f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'}:
            code, value = 403, {'error': '请从本机问答页面发起请求。'}
        elif environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
            code, value = 415, {'error': '请求必须使用JSON。'}
        else:
            try:
                length = int(environ.get('CONTENT_LENGTH') or 0)
                if not 0 < length <= 16384:
                    raise ValueError('Invalid request size.')
                payload = json.loads(environ['wsgi.input'].read(length))
                if not isinstance(payload, dict):
                    raise ValueError('Expected object.')
                code, value = start_job(payload)
            except (ValueError, TypeError):
                code, value = 400, {'error': '无法读取问题，请检查输入。'}
    body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
    start_response(f'{code} ' + {200: 'OK', 202: 'Accepted', 400: 'Bad Request', 403: 'Forbidden',
                               404: 'Not Found', 409: 'Conflict', 415: 'Unsupported Media Type'}[code],
                   [('Content-Type', content_type), ('Content-Length', str(len(body))),
                    ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')])
    return [body]


def worker():
    payload = json.load(sys.stdin)
    folder = Path(payload['folder'])
    sys.path.insert(0, str(ROOT))
    started = time.monotonic()
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        import main as pipeline
        options = {'mode': payload['mode'], 'kb_version': KB_VERSION, 'allow_network': payload['allow_network']}
        if payload['mode'] != 'rag':
            options['output_dir'] = folder/'pipeline'
        result = pipeline.main(payload['query'], **options)
    except Exception as exc:
        result = {'query': payload['query'], 'mode': payload['mode'], 'status': 'failed',
                  'answer': '本次处理未完成，请查看运行记录中的错误原因。', 'error': f'{type(exc).__name__}: {exc}'}
    result['ui_elapsed'] = round(time.monotonic() - started, 2)
    temporary = folder/'result.tmp'
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(folder/'result.json')


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        worker()
    else:
        print(f'论文问答原型：http://127.0.0.1:{PORT}', flush=True)
        print('历史案例不调用模型；点击“运行问题”才会使用现有API配置。', flush=True)
        with make_server('127.0.0.1', PORT, app) as server:
            server.serve_forever()
