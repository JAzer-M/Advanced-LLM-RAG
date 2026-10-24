"""一次本地定向搜索验收；固定输入、禁止网络/生成 API，不自动重跑。"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
for name, value in {
    'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
    'VECLIB_MAXIMUM_THREADS': '1', 'TOKENIZERS_PARALLELISM': 'false',
    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
}.items():
    os.environ[name] = value


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (OUTPUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    if (OUTPUT/'protocol.json').exists():
        raise RuntimeError('该验收已尝试运行；请直接查看现有记录，不自动重跑。')
    saved_path = ROOT/'evaluation/results/agent_p21_closeout_20261020/run/h10.json'
    saved = json.loads(saved_path.read_text())
    # 只复用已保存的绑定查询；来源是本次工具验收人工指定，不验证模型来源路由。
    query = saved['assessment']['next_action']['query']
    source = '2005.11401v4.pdf'
    version = 'all-papers-8-20261020'
    folder = ROOT/'data/processed/versions'/version
    pointer = ROOT/'data/processed/active_kb.json'
    tracked = [Path(__file__), saved_path, pointer,
               *(folder/name for name in ('manifest.json', 'faiss.index', 'chunks.json')),
               *sorted((ROOT/'src').glob('*.py'))]
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in tracked}
    protocol = {
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'purpose': 'P2.2 step 1: one source-scoped local search, not an Agent loop',
        'query': query, 'source': source, 'kb_version': version,
        'source_selection': 'manually supplied canonical filename; no automatic source routing',
        'candidate_k': 120, 'result_k': 10, 'search_calls_limit': 1,
        'generation_api_calls_limit': 0, 'automatic_retries': 0,
        'input_sha256': hashes,
    }
    save('protocol.json', protocol)
    for name in hashes:
        if name.endswith('.py'):
            target = OUTPUT/'source_snapshot'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)

    calls = {'search': 0, 'embedding_encode': 0, 'reranker_predict': 0,
             'generation_api': 0, 'network_attempts': 0}

    def deny_network(*args, **kwargs):
        calls['network_attempts'] += 1
        raise RuntimeError('Network disabled for local-search smoke check')

    def deny_generation(*args, **kwargs):
        calls['generation_api'] += 1
        raise RuntimeError('Generation API is outside this step')

    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network
    started = time.perf_counter()
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        from src import api_llm, agent_tools
        api_llm.chat_completion = deny_generation

        load_started = time.perf_counter()
        resources = agent_tools.load_search_resources()
        load_seconds = time.perf_counter() - load_started
        encode = resources['embedding_model'].encode
        predict = resources['reranker_model'].predict

        def audited_encode(*args, **kwargs):
            calls['embedding_encode'] += 1
            return encode(*args, **kwargs)

        def audited_predict(*args, **kwargs):
            calls['reranker_predict'] += 1
            return predict(*args, **kwargs)

        resources['embedding_model'].encode = audited_encode
        resources['reranker_model'].predict = audited_predict
        calls['search'] += 1
        result = agent_tools.search_local_kb(query, resources, source=source)
        save('search_result.json', result)

        chunks = resources['chunks']
        assert resources['knowledge_base']['version'] == version
        assert len(chunks) == 1397 and len({c['source'] for c in chunks}) == 8
        assert result['query'] == query and result['source'] == source
        assert 0 < len(result['results']) <= 10
        for item in result['results']:
            assert item['source'] == source and item['kb_version'] == version
            assert all(item[key] == chunks[item['chunk_id']][key]
                       for key in ('chunk_id', 'source', 'page', 'title', 'section', 'text'))
        for field in ('dense_ids', 'bm25_ids', 'candidate_ids'):
            ids = result['trace'][field]
            assert len(ids) <= 120 and len(set(ids)) == len(ids)
            assert all(chunks[cid]['source'] == source for cid in ids)
        assert all(digest(ROOT/name) == sha for name,sha in hashes.items())
        assert calls == {'search': 1, 'embedding_encode': 1, 'reranker_predict': 1,
                         'generation_api': 0, 'network_attempts': 0}
        summary = {'status': 'completed', 'calls': calls, 'kb_version': version,
                   'corpus_chunks': len(chunks), 'corpus_papers': 8,
                   'source': source, 'returned_chunks': len(result['results']),
                   'selected_ids': result['trace']['selected_ids'],
                   'load_seconds': round(load_seconds, 3),
                   'search_seconds': result['trace']['elapsed_seconds'],
                   'total_seconds': round(time.perf_counter()-started, 3),
                   'provenance_verified': True, 'tracked_inputs_unchanged': True,
                   'final_answer_generation': 0, 'agent_actions_executed': 0,
                   'boundary': 'manual tool smoke only; no evidence reassessment or h10 answer acceptance'}
        save('smoke_summary.json', summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    except Exception as exc:
        save('smoke_summary.json', {'status': 'failed', 'calls': calls,
                                  'error': f'{type(exc).__name__}: {exc}',
                                  'elapsed_seconds': round(time.perf_counter()-started, 3)})
        raise


if __name__ == '__main__':
    main()
