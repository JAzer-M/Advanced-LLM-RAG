# P3.1只读论文工具：搜索元数据用于定位，固定版本PDF及其原文用于后续证据核对。
# 每次调用写入新的空目录；最多5条搜索结果或一份20MiB/60页PDF，失败不重试、不覆盖。
# 不写知识库，不生成答案；外部原文尚未进入本地chunk_id和引用注册表。
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import ssl
import threading
import time
from urllib.parse import urlencode, urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import pymupdf
import certifi

from src.pdf_loader import load_pdf


MAX_SEARCH_RESULTS = 5
MAX_FEED_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 60
MAX_TEXT_CHARS = 160000
REQUEST_INTERVAL = 3.1
REQUEST_TIMEOUT = 30
_request_lock = threading.Lock()
_request_state = {'last_started': None}


def pinned_id(value):
    """当前仅支持现代带版本ID；不猜版本，不接受任意URL或文件路径。"""
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}\.\d{4,5}v[1-9]\d*', value):
        raise ValueError('Use a modern version-pinned arXiv ID, for example 2312.00752v1.')
    return value


def save_record(folder, record):
    (folder / 'result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def new_output(output_dir):
    folder = Path(output_dir)
    if folder.exists() and any(folder.iterdir()):
        raise ValueError('Use a new empty output directory; previous results and failures are preserved.')
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def fetch_bytes(url, limit, trace):
    """单进程串行、请求间隔至少3.1秒；先记请求，再读有界正文，不自动重试。"""
    request = Request(url, headers={'User-Agent': 'Advanced-LLM-RAG-P3/0.1 (local research)'})
    # Mac框架Python可能没有默认CA文件；追加已安装的Mozilla根证书，保留证书/主机名校验。
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    with _request_lock:
        last = _request_state['last_started']
        if last is not None:
            time.sleep(max(0, REQUEST_INTERVAL - (time.monotonic() - last)))
        _request_state['last_started'] = time.monotonic()
        trace.update(request_url=url, requested_at_utc=datetime.now(timezone.utc).isoformat(),
                     http_attempts=1, automatic_retries=0)
        with urlopen(request, timeout=REQUEST_TIMEOUT, context=context) as response:
            final_url = response.geturl()
            target = urlsplit(final_url)
            trace.update(final_url=final_url, http_status=response.status)
            if target.scheme != 'https' or target.hostname not in {'arxiv.org', 'export.arxiv.org'}:
                raise ValueError('Unexpected response origin for the arXiv request.')
            body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError('arXiv response exceeds this tool byte budget.')
        trace.update(bytes=len(body), response_sha256=hashlib.sha256(body).hexdigest())
        return body


def search_arxiv(query, output_dir, limit=3):
    """输入arXiv检索式，返回带版本的题录；摘要只用于定位论文，不视为回答证据。"""
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError('Use a nonempty arXiv search query of at most 500 characters.')
    if type(limit) is not int or not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise ValueError('Search limit must be an integer from 1 to 5.')
    folder = new_output(output_dir)
    url = 'https://export.arxiv.org/api/query?' + urlencode(
        {'search_query': query.strip(), 'start': 0, 'max_results': limit})
    record = {'tool': 'search_arxiv', 'query': query.strip(), 'status': 'running', 'papers': [],
              'metadata_is_answer_evidence': False, 'trace': {'http_attempts': 0, 'automatic_retries': 0}}
    save_record(folder, record)
    try:
        body = fetch_bytes(url, MAX_FEED_BYTES, record['trace'])
        (folder / 'response.xml').write_bytes(body)
        feed = ET.fromstring(body)
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        if feed.tag != '{http://www.w3.org/2005/Atom}feed':
            raise ValueError('Expected an arXiv Atom feed, not an HTML/error response.')
        entries = feed.findall('a:entry', ns)
        if len(entries) > limit:
            raise ValueError('Search response exceeds the requested result count.')
        for entry in entries:
            identity = urlsplit(entry.findtext('a:id', '', ns))
            if identity.scheme not in {'http', 'https'} or identity.hostname != 'arxiv.org' or not identity.path.startswith('/abs/'):
                raise ValueError('Search returned an error or non-arXiv paper identity.')
            paper_id = pinned_id(identity.path.removeprefix('/abs/'))
            title = ' '.join(entry.findtext('a:title', '', ns).split())
            if not title or any(p['arxiv_id'] == paper_id for p in record['papers']):
                raise ValueError('Search returned an empty title or duplicate paper identity.')
            record['papers'].append({'arxiv_id': paper_id, 'title': title,
                'authors': [a.findtext('a:name', '', ns) for a in entry.findall('a:author', ns)],
                'abstract': ' '.join(entry.findtext('a:summary', '', ns).split()),
                'published': entry.findtext('a:published', '', ns), 'updated': entry.findtext('a:updated', '', ns),
                'abstract_url': f'https://arxiv.org/abs/{paper_id}', 'pdf_url': f'https://arxiv.org/pdf/{paper_id}'})
        record['status'] = 'completed'
    except Exception as exc:
        if isinstance(exc, HTTPError):
            record['trace']['http_status'] = exc.code
        record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        save_record(folder, record)
    return record


def read_arxiv_paper(arxiv_id, output_dir, two_columns=False):
    """下载一个固定版本，复用已有PDF解析器，返回来源/页码/章节/原文和获取记录。"""
    paper_id = pinned_id(arxiv_id)
    if type(two_columns) is not bool:
        raise ValueError('two_columns must be a boolean; layout is an explicit caller choice.')
    folder = new_output(output_dir)
    pdf_url = f'https://arxiv.org/pdf/{paper_id}'
    record = {'tool': 'read_arxiv_paper', 'arxiv_id': paper_id, 'status': 'running',
              'abstract_url': f'https://arxiv.org/abs/{paper_id}', 'pdf_url': pdf_url,
              'two_columns': two_columns, 'trace': {'http_attempts': 0, 'automatic_retries': 0}, 'documents': []}
    save_record(folder, record)
    try:
        body = fetch_bytes(pdf_url, MAX_PDF_BYTES, record['trace'])
        if urlsplit(record['trace']['final_url']).path not in {f'/pdf/{paper_id}', f'/pdf/{paper_id}.pdf'}:
            raise ValueError('PDF response changed the requested version-pinned path.')
        if not body.startswith(b'%PDF-'):
            raise ValueError('Expected PDF bytes, not an abstract or error page.')
        pdf_path = folder / f'{paper_id}.pdf'
        pdf_path.write_bytes(body)
        with pymupdf.open(pdf_path) as pdf:
            if pdf.needs_pass or not 1 <= len(pdf) <= MAX_PDF_PAGES:
                raise ValueError('Encrypted, empty, or over-budget PDF is not supported.')
            record['pages'] = len(pdf)
        documents = load_pdf(pdf_path, two_columns=two_columns)
        if not documents or sum(len(d['text']) for d in documents) > MAX_TEXT_CHARS:
            raise ValueError('PDF text is empty or exceeds the extraction budget; evidence was not silently truncated.')
        # 临时证据使用独立的稳定ID，不能冒充任何知识库中的位置chunk_id。
        record['documents'] = [{**d, 'arxiv_id': paper_id, 'url': pdf_url,
            'evidence_id': f'arxiv:{paper_id}:document:{i}', 'pdf_sha256': record['trace']['response_sha256']}
            for i, d in enumerate(documents)]
        record.update(status='completed', pdf_path=str(pdf_path.resolve()), permanent_kb_import=False)
    except Exception as exc:
        if isinstance(exc, HTTPError):
            record['trace']['http_status'] = exc.code
        record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        save_record(folder, record)
    return record
