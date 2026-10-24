"""Recompute metrics from saved IDs and check experiment provenance; no model calls."""
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.metrics import (precision_at_k, recall_at_k, average_precision_at_k,
                                reciprocal_rank_at_k, mean_average_precision_at_k,
                                mean_reciprocal_rank_at_k)

names = ['verified_english_60', 'verified_english_20', 'validation_60', 'legacy_60']
reports = {name: json.loads((OUT / name / 'results.json').read_text()) for name in names}
rows = 0
for name, report in reports.items():
    assert report['status'] == 'completed' and report['inputs_unchanged']
    assert report['api_call_count'] == 0
    for k_text, methods in report['metrics'].items():
        k = int(k_text)
        for method, scores in methods.items():
            cases = []
            for q in report['questions']:
                if q['status'] != 'completed':
                    continue
                m = q['metrics_by_k'][k_text][method]
                ids, gold = m['retrieved_ids'], q['gold_ids']
                assert len(ids) <= k and len(ids) == len(set(ids))
                for key, fn in [('precision', precision_at_k), ('recall', recall_at_k),
                                ('ap', average_precision_at_k), ('rr', reciprocal_rank_at_k)]:
                    assert math.isclose(m[key], fn(ids, gold, k), abs_tol=1e-12)
                cases.append((ids, gold))
                rows += 1
            expected = {'questions': len(cases),
                        'precision': sum(precision_at_k(r,g,k) for r,g in cases) / len(cases),
                        'recall': sum(recall_at_k(r,g,k) for r,g in cases) / len(cases),
                        'map': mean_average_precision_at_k(cases,k),
                        'mrr': mean_reciprocal_rank_at_k(cases,k)}
            assert all(math.isclose(scores[key], value, abs_tol=1e-12) for key,value in expected.items())

en = json.loads((ROOT / 'evaluation/arxiv_pilot_questions_en.json').read_text())
zh = json.loads((ROOT / 'evaluation/arxiv_pilot_questions.json').read_text())
assert all(a['id'] == b['id'] and a['gold_evidence'] == b['gold_evidence'] for a,b in zip(en,zh))
baseline = json.loads((OUT / 'baseline_hashes.json').read_text())
changed = [name for name, sha in baseline.items()
           if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha]
assert set(changed) == {'main.py', 'src/reranker.py', 'src/query_decomposer.py',
                        'evaluation/run_evaluation.py', 'tests/test_retrieval_coverage.py'}, changed
first = json.loads((OUT / 'english_60/results.json').read_text())
extra = [json.loads((OUT / filename).read_text())
         for filename in ('p6_revised_decomposition.json','p6_final_decomposition.json')]
calls = first['api_calls'] + extra
assert len(calls) == 14 and all(c['response']['finish_reason'] == 'stop' for c in calls)
quotes = [evidence['quote'] for q in en for evidence in q.get('gold_evidence', [])]
assert all(not any(quote in call['prompt'] for quote in quotes) for call in calls)
usage = {key: sum(c['response']['usage'][key] for c in calls)
         for key in ('prompt_tokens','completion_tokens','total_tokens')}
initial_cache = json.loads((OUT / 'english_60/auxiliary.json').read_text())
final_cache = json.loads((OUT / 'auxiliary_final.json').read_text())
assert all(initial_cache[qid] == final_cache[qid] for qid in initial_cache if qid != 'p6')
assert initial_cache['p6']['rewritten_query'] == final_cache['p6']['rewritten_query']
main_replay = json.loads((OUT / 'main_p6_final_replay.json').read_text())
assert main_replay['matches_evaluation_top10'] and main_replay['api_calls'] == 0
for name in ('validation_60', 'legacy_60'):
    assert all(q['metrics_by_k']['10']['Hybrid + Reranker'][metric] ==
               q['metrics_by_k']['10']['Hybrid + Reranker + RRF Anchor'][metric]
               for q in reports[name]['questions'] if q['status'] == 'completed'
               for metric in ('precision', 'recall', 'ap', 'rr'))
prefix = {}
current = reports['verified_english_60']
chunks = json.loads(Path(current['knowledge_base']['chunks_path']).read_text())
for budget in ('5','10','20'):
    cases = [(q['metrics_by_k'][budget]['Decomposition + Hybrid + Reranker']['retrieved_ids'],
              q['gold_ids']) for q in current['questions'] if q['status']=='completed']
    prefix[budget] = {'mean_passage_body_characters': sum(
        sum(len(chunks[cid]['text']) for cid in ids) for ids,_ in cases) / len(cases),
        'fixed_ranking_cutoffs': {}}
    for cutoff in (5,10,20):
        if cutoff > int(budget):
            continue
        prefix[budget]['fixed_ranking_cutoffs'][str(cutoff)] = {
            'precision':sum(precision_at_k(r,g,cutoff) for r,g in cases)/len(cases),
            'recall':sum(recall_at_k(r,g,cutoff) for r,g in cases)/len(cases),
            'map':mean_average_precision_at_k(cases,cutoff),
            'mrr':mean_reciprocal_rank_at_k(cases,cutoff)}
(OUT/'fixed_ranking_prefix_metrics.json').write_text(json.dumps(prefix,indent=2)+'\n')
for name in ('verified_english_60','verified_english_20'):
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha
               for p,sha in reports[name]['input_sha256'].items())
test_log = (OUT / 'tests_final.log').read_text()
assert 'Ran 47 tests' in test_log and '\nOK' in test_log
secret = json.loads((ROOT / 'api.local.json').read_text())['api_key'].encode()
assert secret and all(secret not in p.read_bytes() for p in OUT.rglob('*') if p.is_file())
verification = {'status':'passed', 'metric_rows_recomputed': rows,
    'all_four_metrics_match': True, 'original_gold_unchanged': True,
    'baseline_files_preserved': len(baseline)-len(changed), 'intentional_changes': changed,
    'offline_evaluation_api_calls':0, 'total_new_auxiliary_api_calls':14,
    'total_new_final_answer_calls':0, 'usage':usage, 'all_finish_reason_stop':True,
    'main_p6_matches_evaluation':True, 'tests':47, 'configured_key_absent':True,
    'validation_and_legacy_per_question_top10_metrics_unchanged':True,
    'active_kb':json.loads((ROOT/'data/processed/active_kb.json').read_text())['version']}
(OUT / 'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps(verification,indent=2))
