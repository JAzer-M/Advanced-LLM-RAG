"""Replay the real selector on a frozen failure, without models or API calls."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.reranker import select_evidence

report = json.loads((ROOT / 'evaluation/results/independent_validation_20261019/retrieval/results.json').read_text())
q = next(q for q in report['questions'] if q['id'] == 'n07')
global_ids = q['stage_ids']['decomposition_global']
selected = [c['chunk_id'] for c in select_evidence(
    [{'chunk_id': cid} for cid in global_ids], q['sub_query_evidence'], 10,
    q['stage_ids']['rrf'][:1])]
assert selected == q['metrics_by_k']['10']['Decomposition + Hybrid + Reranker']['retrieved_ids']
missing = set(q['gold_ids']) - set(selected)
print('n07: required IDs', q['gold_ids'], 'selected', selected)
print('Not recalled:', sorted(set(q['gold_ids']) - set(global_ids)))
print('Recalled but excluded:', sorted(missing & set(global_ids)))
assert not missing, 'Cross-paper evidence incomplete after the actual select_evidence call.'
