"""Diagnostic only: compare reranker input with verified paper titles added."""
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
from src.knowledge_base import load_knowledge_base

_, chunks, kb = load_knowledge_base(ROOT / 'data/processed', 'arxiv-pilot-5-20261019')
probe = json.loads((OUT / 'subquery_probe.json').read_text(encoding='utf-8'))
model = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device=pipeline.RERANKER_DEVICE)
cases = [(probe['queries'][0]['query'], probe['combined_candidate_ids']),
         *[(row['query'], row['candidate_ids']) for row in probe['queries'][-2:]]]
rows = []
for query, ids in cases:
    candidates = [chunks[i] for i in ids]
    pairs = [(query, f"Source: {c['source']}\nTitle: {c['title']}\n{c['text']}") for c in candidates]
    scores = model.predict(pairs)
    ranked = sorted([{**c, 'rerank_score': float(s)} for c, s in zip(candidates, scores)],
                    key=lambda c: c['rerank_score'], reverse=True)
    row = {'query': query, 'candidate_ids': ids, 'top10': ranked[:10],
           'diagnostic_mechanism_ranks': {str(cid): next((i for i,c in enumerate(ranked,1)
                                                          if c['chunk_id']==cid),None)
                                          for cid in (195,218,219,222,244)}}
    rows.append(row)
    print(query, [(c['chunk_id'], round(c['rerank_score'],3)) for c in ranked[:5]],
          row['diagnostic_mechanism_ranks'], flush=True)
(OUT / 'title_probe.json').write_text(json.dumps({'purpose':__doc__,'api_calls':0,
                                                   'knowledge_base':kb,'cases':rows},
                                                  ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
