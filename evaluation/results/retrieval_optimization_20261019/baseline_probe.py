"""Pre-change English retrieval probe, no auxiliary or answer API calls."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

import evaluation.run_evaluation as e

out = Path(__file__).resolve().parent
questions = json.loads((ROOT / 'evaluation/arxiv_pilot_questions_en.json').read_text())
index, chunks, kb = e.load_knowledge_base(ROOT / 'data/processed', 'arxiv-pilot-5-20261019')
embedding = e.load_embedding_model()
bm25 = e.build_bm25_index(chunks)
reranker = e.CrossEncoder(e.RERANKER_NAME, device='cpu')
report = {'mode': __doc__, 'api_calls': 0, 'knowledge_base': kb, 'cases': []}
for question in questions:
    if not question.get('gold_evidence'):
        continue
    gold, unmatched = e.get_gold_chunk_ids(question, chunks)
    assert gold and not unmatched
    for budget in (20, 60):
        started = time.perf_counter()
        e.CANDIDATE_K = e.RRF_TOP_K = budget
        e.FINAL_K = budget
        dense, sparse = e.retrieve_two_ways(question['question'], embedding, index, chunks, bm25)
        fused, ranking = e.fuse_and_rerank(question['question'], dense, sparse, reranker)
        methods = {'Dense': dense, 'BM25': sparse, 'Hybrid': fused, 'Hybrid + Reranker': ranking}
        entry = {'id': question['id'], 'query': question['question'], 'candidate_budget': budget,
                 'gold_ids': sorted(gold), 'elapsed_seconds': round(time.perf_counter()-started, 3),
                 'stages': {name: {'ids': e.get_result_ids(items),
                                   'gold_ranks': {str(g): next((i for i,c in enumerate(items,1) if c['chunk_id']==g), None) for g in gold}}
                            for name,items in methods.items()},
                 'metrics': {}}
        for k in (5,10,20):
            e.FINAL_K = k
            entry['metrics'][str(k)] = {name: e.evaluate_retrieval(e.get_result_ids(items),gold)
                                        for name,items in methods.items()}
        report['cases'].append(entry)
        (out / 'english_before.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(question['id'], 'budget', budget, 'Gold ranks',entry['stages']['Hybrid + Reranker']['gold_ranks'], flush=True)

for budget in (20,60):
    for k in (5,10,20):
        cases=[c for c in report['cases'] if c['candidate_budget']==budget]
        print('budget',budget,'k',k,{name:round(sum(c['metrics'][str(k)][name]['recall'] for c in cases)/len(cases),4) for name in methods})
if '--assert-complete' in sys.argv:
    assert all(c['metrics']['10']['Hybrid + Reranker']['recall']==1
               for c in report['cases'] if c['candidate_budget']==60), 'Pre-change Top-10 misses required Gold evidence.'
