"""Diagnostic only: inspect sub-query ranks on the captured four-query plan."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent

import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

import main as pipeline
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.embedding import load_embedding_model
from src.hybrid_retriever import reciprocal_rank_fusion
from src.knowledge_base import load_knowledge_base
from src.reranker import rerank_results
from src.retriever import retrieve

index, chunks, metadata = load_knowledge_base(ROOT / 'data/processed', 'arxiv-pilot-5-20261019')
embedding = load_embedding_model()
reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device=pipeline.RERANKER_DEVICE)
bm25 = build_bm25_index(chunks)
capture = json.loads((OUT / 'captured_p6_decomposition.json').read_text(encoding='utf-8'))
queries = json.loads(capture['response'])['sub_queries']
rows = []
pool = set()
for query in [capture['query'], *queries]:
    dense = retrieve(embedding, index, chunks, query, pipeline.RETRIEVAL_TOP_K)
    sparse = retrieve_bm25(bm25, chunks, query, pipeline.RETRIEVAL_TOP_K)
    fused = reciprocal_rank_fusion(dense, sparse, k=pipeline.RRF_K, top_k=pipeline.RRF_TOP_K)
    pool.update(c['chunk_id'] for c in fused)
    local = rerank_results(query, fused, reranker, top_k=3, include_source=True)
    rows.append({'query': query, 'candidate_ids': [c['chunk_id'] for c in fused], 'top3': local})
    print(query, [(c['chunk_id'], c['page'], round(c['rerank_score'], 3)) for c in local], flush=True)
report = {'purpose': __doc__, 'api_calls': 0, 'knowledge_base': metadata,
          'combined_candidate_ids': sorted(pool), 'queries': rows}
(OUT / 'subquery_probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                         encoding='utf-8')
