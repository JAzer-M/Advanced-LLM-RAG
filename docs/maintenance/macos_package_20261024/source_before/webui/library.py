"""网页论文库：独立版本指针，导入失败不改当前库，不改实验激活指针。"""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = 'all-papers-8-20261020'
EMBEDDING = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
MAX_BYTES = 20 * 1024 * 1024


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.writing-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def current():
    path = ROOT / 'data/webui/library.json'
    if path.exists(): return json.loads(path.read_text())
    # 旧工作区沿用八篇基线；新安装从空库开始，不依赖本机实验资产。
    baseline = ROOT / 'data/processed/versions' / BASE_VERSION / 'manifest.json'
    return {'version': BASE_VERSION if baseline.is_file() else None}


def catalog():
    # 元数据与问答读取同一个网页库版本。完整配对校验在导入/问答时执行。
    state = current()
    if state['version'] is None:
        return {'papers':[], 'chunks':0, 'kb_version':None}
    chunks = json.loads((ROOT / 'data/processed/versions' / state['version'] / 'chunks.json').read_text())
    papers = {}
    for chunk in chunks:
        row = papers.setdefault(chunk['source'], {'source':chunk['source'], 'title':chunk['title'], 'chunks':0})
        row['chunks'] += 1
    return {'papers':list(papers.values()), 'chunks':len(chunks), 'kb_version':state['version']}


def paper_title(pdf, fallback):
    """缺少元数据时尝试首页顶部大字标题，排除竖排水印；失败用文件名。"""
    title=(pdf.metadata.get('title') or '').strip()
    if title: return title
    lines=[line for block in pdf[0].get_text('dict')['blocks'] if 'lines' in block
           for line in block['lines'] if abs(line['dir'][1])<0.1
           and line['bbox'][1]<pdf[0].rect.height*0.35 and any(s['text'].strip() for s in line['spans'])]
    spans=[span for line in lines for span in line['spans'] if span['text'].strip()]
    if spans:
        largest=max(s['size'] for s in spans)
        # 标题可能采用大小写混排字号，选中标题行后保留整行，避免只剩大写首字母。
        title=' '.join(''.join(s['text'] for s in line['spans']).strip() for line in lines
                       if max(s['size'] for s in line['spans'])>=largest-0.5)
        if largest>=12 and 10<=len(title)<=300: return title
    return fallback


def prepare(payload):
    files = payload.get('files')
    if not isinstance(files, list) or not 1 <= len(files) <= 5:
        raise ValueError('每次请选择1～5篇PDF，总大小不超过20MB。')
    if type(payload.get('two_columns', False)) is not bool:
        raise ValueError('双栏选项格式错误。')
    decoded, total = [], 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not isinstance(item.get('data'), str):
            raise ValueError('文件格式错误。')
        name = item['name']
        if not name.lower().endswith('.pdf') or '/' in name or '\\' in name or len(name) > 180 or any(ord(c)<32 for c in name):
            raise ValueError('请上传文件名正常的PDF。')
        try: body = base64.b64decode(item['data'], validate=True)
        except ValueError: raise ValueError('无法读取上传文件。') from None
        total += len(body)
        if not body.startswith(b'%PDF-') or total > MAX_BYTES:
            raise ValueError('需要有效PDF，且本批文件总大小不能超过20MB。')
        decoded.append((name, body))
    identity = uuid4().hex
    folder = ROOT / 'data/webui/imports' / identity
    folder.mkdir(parents=True)
    records = []
    for n, (name, body) in enumerate(decoded):
        path = folder / f'{n}.pdf'; path.write_bytes(body)
        records.append({'name':name, 'path':str(path), 'sha256':hashlib.sha256(body).hexdigest()})
    atomic_json(folder/'request.json', {'files':records,'two_columns':payload.get('two_columns',False)})
    atomic_json(folder/'status.json', {'id':identity,'status':'running','stage':'排队准备','files':[r['name'] for r in records]})
    return identity, folder


def build(folder):
    """独立进程内运行；全批成功才切换，重复文件跳过。"""
    import fcntl
    import faiss
    import pymupdf
    from src.knowledge_base import load_knowledge_base, create_version
    from src.pdf_loader import load_pdf
    from src.embedding import load_embedding_model, embed_chunks
    from src.chunking_semantic import split_documents_semantic
    folder = Path(folder)
    status = json.loads((folder/'status.json').read_text())
    def update(stage):
        status['stage'] = stage; atomic_json(folder/'status.json', status)
    try:
        with (ROOT/'data/webui/import.lock').open('a') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('已有导入正在进行，请等待完成后重试。') from None
            state = current()
            processed = ROOT/'data/processed'
            if state['version'] is None:
                index, old_chunks, hashes = None, [], {}
            else:
                index, old_chunks, _ = load_knowledge_base(processed, state['version'])
                manifest = json.loads((processed/'versions'/state['version']/'manifest.json').read_text())
                if manifest['build'].get('embedding_model') != EMBEDDING:
                    raise ValueError('当前库的向量模型不兼容，未修改知识库。')
                hashes = dict(manifest['build'].get('source_pdfs', {}))
            sources = {c['source'] for c in old_chunks}
            request = json.loads((folder/'request.json').read_text())
            documents, added, skipped = [], [], []
            for item in request['files']:
                if item['sha256'] in hashes.values():
                    skipped.append(item['name']); continue
                update('解析PDF：'+item['name'])
                with pymupdf.open(item['path']) as pdf:
                    if pdf.needs_pass or not 1 <= len(pdf) <= 200:
                        raise ValueError('PDF加密、为空或超过200页：'+item['name'])
                    title=paper_title(pdf,Path(item['name']).stem)
                docs = load_pdf(item['path'], two_columns=request['two_columns'])
                if not docs or sum(len(d['text']) for d in docs)<40:
                    raise ValueError('没有足够可提取正文（扫描件暂不支持OCR）：'+item['name'])
                if sum(len(d['text']) for d in docs)>1_000_000:
                    raise ValueError('单篇正文过长：'+item['name'])
                source = item['name']
                if source in sources: source = Path(source).stem+'-'+item['sha256'][:12]+'.pdf'
                if source in sources: raise ValueError('论文文件名冲突，请重命名后导入。')
                for doc in docs:
                    doc['source']=source
                    doc['title']=title
                documents.extend(docs); sources.add(source); hashes[source]=item['sha256']; added.append(source)
            if not added:
                status.update(status='completed',stage='全部文件已存在，无需重复入库',added=[],skipped=skipped,version=state['version'])
                atomic_json(folder/'status.json',status); return
            update('加载本地向量模型')
            model = load_embedding_model()
            update('分段并生成向量')
            chunks = split_documents_semantic(documents, model, max_chunk_size=500, percentile=10)
            if any(not any(c['source']==source for c in chunks) for source in added):
                raise ValueError('部分论文未生成有效片段，本批未入库。')
            vectors = embed_chunks(model, chunks)
            if index is None: index = faiss.IndexFlatIP(vectors.shape[1])
            if vectors.shape[1] != index.d: raise ValueError('向量维度不一致，本批未入库。')
            for i, chunk in enumerate(chunks, len(old_chunks)): chunk['chunk_id']=i
            index.add(vectors)
            update('校验并发布新版本')
            version='webui-'+folder.name
            processed.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=processed) as tmp:
                ip, cp = Path(tmp)/'faiss.index', Path(tmp)/'chunks.json'
                faiss.write_index(index,str(ip)); atomic_json(cp,old_chunks+chunks)
                create_version(processed,version,ip,cp,{'kind':'webui_append','parent_version':state['version'],
                    'embedding_model':EMBEDDING,'normalized_embeddings':True,'source_pdfs':hashes})
            # 唯一提交点；此前任何异常都不会影响旧指针和旧文件。
            atomic_json(ROOT/'data/webui/library.json',{'version':version,'previous_version':state['version']})
            status.update(status='completed',stage='入库完成',added=added,skipped=skipped,version=version)
            atomic_json(folder/'status.json',status)
    except Exception as exc:
        status.update(status='failed',stage='入库失败，当前论文库未切换',error=str(exc) if isinstance(exc,ValueError) else '解析或构建失败，请检查本机导入日志。')
        atomic_json(folder/'status.json',status)
        raise
