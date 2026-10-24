# P2.2 第一个本地工具：搜索知识库。这里只执行检索，不规划需求或生成回答。
# 调用顺序：load_search_resources() 加载一次，再多次调用 search_local_kb()。
# 返回真实原文、版本和检索轨迹，后续由 Agent 执行入口决定怎样使用结果。

from pathlib import Path
import time

from sentence_transformers import CrossEncoder

from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.embedding import load_embedding_model
from src.hybrid_retriever import reciprocal_rank_fusion
from src.knowledge_base import load_knowledge_base
from src.reranker import rerank_results
from src.retriever import retrieve


# 固定实验库和预算；加载八篇库不会修改当前仍指向三篇库的激活指针。
SEARCH_KB_VERSION = 'all-papers-8-20261020'
CANDIDATE_K = 120
RESULT_K = 10
RRF_K = 60


def load_search_resources():
    """加载校验后的八篇配对库和 CPU 模型，供同一进程中的多次搜索复用。"""
    processed = Path(__file__).resolve().parents[1] / 'data' / 'processed'
    index, chunks, knowledge_base = load_knowledge_base(processed, SEARCH_KB_VERSION)
    return {
        'index': index,
        'chunks': chunks,
        'knowledge_base': knowledge_base,
        'embedding_model': load_embedding_model(),
        'bm25': build_bm25_index(chunks),
        'reranker_model': CrossEncoder('BAAI/bge-reranker-base', device='cpu'),
    }


def search_local_kb(query, resources, source=None):
    """按查询及可选的精确论文文件名搜索，返回最多十条带出处的原文。"""
    if not isinstance(query, str) or not query.strip():
        raise ValueError('搜索查询必须是非空字符串。')
    query = query.strip()
    chunks = resources['chunks']
    sources = {chunk['source'] for chunk in chunks}
    if source is not None and (not isinstance(source, str) or source not in sources):
        raise ValueError('source 必须是当前知识库中的精确论文文件名，或为 None。')

    started = time.perf_counter()
    # 小语料的定向搜索先取完整排名，再按论文过滤，最后截断到每路 120。
    # 若先取全库 Top-120，目标论文可能被其他论文挤掉，之后再过滤也找不回来。
    depth = len(chunks) if source is not None else CANDIDATE_K
    dense = retrieve(resources['embedding_model'], resources['index'], chunks, query, top_k=depth)
    sparse = retrieve_bm25(resources['bm25'], chunks, query, top_k=depth)
    dense = [item for item in dense if source is None or item['source'] == source][:CANDIDATE_K]
    sparse = [item for item in sparse if source is None or item['source'] == source][:CANDIDATE_K]

    candidates = reciprocal_rank_fusion(dense, sparse, k=RRF_K, top_k=CANDIDATE_K)
    ranked = rerank_results(query, candidates, resources['reranker_model'],
                            top_k=RESULT_K, include_source=True)
    knowledge_base = resources['knowledge_base']
    # 保留原库的 chunk_id，不因来源过滤重新编号；分数仅表示相关性排序。
    results = [{**item, 'kb_version': knowledge_base['version']} for item in ranked]
    return {
        'query': query,
        'source': source,
        'knowledge_base': knowledge_base.copy(),
        'results': results,
        'trace': {
            'retrieval_depth': depth,
            'candidate_k': CANDIDATE_K,
            'rrf_k': RRF_K,
            'result_k': RESULT_K,
            'dense_ids': [item['chunk_id'] for item in dense],
            'bm25_ids': [item['chunk_id'] for item in sparse],
            'candidate_ids': [item['chunk_id'] for item in candidates],
            'selected_ids': [item['chunk_id'] for item in results],
            'elapsed_seconds': round(time.perf_counter() - started, 6),
            'generation_api_calls': 0,
        },
    }
