"""下载版首次准备固定版本检索模型；进度落盘，成功校验后才标记可用。"""
import json
from pathlib import Path

from src.platform_compat import pid_alive, try_lock
from src.runtime_paths import MODEL_REVISIONS, data_root, managed_models, model_location

MODEL_FILES = {
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2':{
        'config.json':645, 'config_sentence_transformers.json':122, 'modules.json':229,
        'sentence_bert_config.json':53, '1_Pooling/config.json':190,
        'tokenizer_config.json':526, 'special_tokens_map.json':239, 'tokenizer.json':9081518,
        'model.safetensors':470641600, 'README.md':3888,
    },
    'BAAI/bge-reranker-base':{
        'config.json':799, 'tokenizer_config.json':443, 'special_tokens_map.json':279,
        'tokenizer.json':17098107, 'sentencepiece.bpe.model':5069051,
        'model.safetensors':1112206140, 'README.md':34111,
    },
}
TOTAL_BYTES = sum(sum(files.values()) for files in MODEL_FILES.values())


def status():
    base = {'enabled':managed_models(), 'total_bytes':TOTAL_BYTES, 'completed_bytes':0}
    if not base['enabled']: return {**base, 'status':'ready'}
    folder = data_root()/'models'
    try:
        ready = json.loads((folder/'ready.json').read_text()) == MODEL_REVISIONS
        ready = ready and all((Path(model_location(repo))/name).stat().st_size == size
                              for repo, files in MODEL_FILES.items() for name, size in files.items())
        if ready: return {**base, 'status':'ready', 'completed_bytes':TOTAL_BYTES}
    except (OSError, ValueError): pass
    try: state = json.loads((folder/'setup.json').read_text())
    except (OSError, ValueError): return {**base, 'status':'missing'}
    if state.get('status') == 'ready': return {**base, 'status':'missing'}
    if state.get('status') == 'running':
        try:
            pid = json.loads((folder/'process.json').read_text())['pid']
            if not pid_alive(pid): raise ValueError('process is not running')
        except (OSError, ValueError, KeyError):
            state.update(status='failed', error='模型准备已中断，可以重新下载；已完成文件会复用。')
        if state.get('repo') in MODEL_FILES:
            cache = Path(model_location(state['repo']))/'.cache/huggingface/download'
            try: partial = sum(p.stat().st_size for p in cache.rglob('*.incomplete') if p.is_file())
            except FileNotFoundError: partial = 0  # 下载完成重命名时，下次轮询读取最终大小。
            state['completed_bytes'] = min(TOTAL_BYTES, state.get('completed_bytes',0)
                                           + min(partial, state.get('file_size',0)))
    return {**base, **state}


def prepare():
    from huggingface_hub import hf_hub_download
    from webui.library import atomic_json
    folder = data_root()/'models'; folder.mkdir(parents=True, exist_ok=True)
    with (folder/'download.lock').open('a') as lock:
        try: try_lock(lock)
        except BlockingIOError: raise ValueError('已有模型准备正在进行。') from None
        if status()['status'] == 'ready': return
        (folder/'ready.json').unlink(missing_ok=True)
        state = {'status':'running','phase':'download','completed_bytes':0,'total_bytes':TOTAL_BYTES}
        try:
            for repo, files in MODEL_FILES.items():
                destination = Path(model_location(repo))
                for name, size in files.items():
                    state.update(repo=repo, file=name, file_size=size)
                    atomic_json(folder/'setup.json', state)
                    path = hf_hub_download(repo, name, revision=MODEL_REVISIONS[repo],
                                           local_dir=destination, token=False)
                    if Path(path).stat().st_size != size:
                        raise ValueError('模型文件不完整：'+name)
                    state['completed_bytes'] += size
            state.update(phase='verify', file_size=0)
            atomic_json(folder/'setup.json', state)
            import torch
            torch.set_num_threads(1); torch.set_num_interop_threads(1)
            from sentence_transformers import SentenceTransformer, CrossEncoder
            model = SentenceTransformer(model_location(next(iter(MODEL_FILES))), device='cpu')
            if model.get_embedding_dimension() != 384: raise ValueError('向量模型维度不匹配。')
            CrossEncoder(model_location('BAAI/bge-reranker-base'), device='cpu')
            atomic_json(folder/'ready.json', MODEL_REVISIONS)
            state.update(status='ready', phase='done')
            atomic_json(folder/'setup.json', state)
        except Exception:
            state.update(status='failed', error='下载或校验未完成，请检查网络后重试；已完成文件会复用。')
            atomic_json(folder/'setup.json', state)
            raise
