"""Recompute retrieval metrics from the very same saved main runs, without APIs."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path('/Users/j/Desktop/Advanced-LLM-RAG')
STAGE = Path(__file__).resolve().parent
OUT = STAGE if (STAGE / 'questions_frozen.json').exists() else STAGE / 'results'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_metrics(ids, gold, k=10):
    seen = set()
    hits = 0
    accumulated = 0.0
    first = None
    for rank, cid in enumerate(ids[:k], 1):
        if cid in seen:
            continue
        seen.add(cid)
        if cid in gold:
            hits += 1
            accumulated += hits / rank
            if first is None:
                first = rank
    return {'precision': hits / k, 'normalized_precision': hits / min(k, len(gold)),
            'recall': hits / len(gold), 'average_precision': accumulated / len(gold),
            'reciprocal_rank': 1 / first if first else 0.0}


def main():
    questions = json.loads((OUT / 'questions_frozen.json').read_text())
    chunks = json.loads((ROOT / 'data/processed/versions/all-papers-8-20261020/chunks.json').read_text())
    traces = json.loads((OUT / 'retrieval_stage_traces.json').read_text())
    spec = importlib.util.spec_from_file_location('metrics', ROOT / 'evaluation/metrics.py')
    metrics = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metrics)
    # Execute just the repository's pure Gold-mapping helpers: no evaluator/model imports.
    tree = ast.parse((ROOT / 'evaluation/run_evaluation.py').read_text())
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name in {'normalize_text', 'get_gold_chunk_ids'}]
    namespace = {'re': re, 'unicodedata': unicodedata}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), '<pure repository Gold helpers>', 'exec'), namespace)
    cases = []
    for q in questions:
        qid = q['id']
        result = json.loads((OUT / f'{qid}.json').read_text())
        gold, unmatched = namespace['get_gold_chunk_ids'](q, chunks)
        assert not unmatched and sorted(gold) == q['gold_chunk_ids_at_freeze']
        case = {'id': qid, 'type': q['type'], 'pipeline_status': result['status'],
                'gold_ids': sorted(gold), 'gold_count': len(gold),
                'retrieval_scored': bool(gold) and result['status'] == 'completed'}
        if result['status'] == 'completed':
            selected = result['selected_ids']
            registry_ids = [c['chunk_id'] for c in result['ledger']['citation_registry']]
            assert len(selected) == len(set(selected)) == 10
            assert registry_ids[:10] == selected
            initial = traces[qid]
            pool = initial['candidate_ids_before_global_rerank']
            ranking = initial['global_ranking_ids_before_completion']
            assert len(pool) == len(set(pool)) and set(pool) == set(ranking)
            case.update(selected_ids=selected, context_registry_ids=registry_ids,
                        gold_hit_ids=sorted(set(selected) & gold),
                        gold_missing_ids=sorted(gold - set(selected)),
                        gold_in_context_ids=sorted(gold & set(registry_ids)),
                        gold_in_initial_candidate_ids=sorted(gold & set(pool)),
                        gold_missing_initial_candidate_ids=sorted(gold - set(pool)),
                        gold_initial_global_ranks={str(cid): ranking.index(cid) + 1 for cid in sorted(gold) if cid in ranking},
                        candidate_count=len(pool), context_chars=len(result['context']),
                        citation_structure_passed=result['citation_structure']['structure_passed'],
                        decomposition=result.get('decomposition'),
                        completion=result.get('retrieval_diagnostics', {}).get('evidence_completion'))
            if gold:
                calculated = {'precision': metrics.precision_at_k(selected, gold, 10),
                              'normalized_precision': metrics.normalized_precision_at_k(selected, gold, 10),
                              'recall': metrics.recall_at_k(selected, gold, 10),
                              'average_precision': metrics.average_precision_at_k(selected, gold, 10),
                              'reciprocal_rank': metrics.reciprocal_rank_at_k(selected, gold, 10)}
                independent = independent_metrics(selected, gold)
                assert all(abs(calculated[k] - independent[k]) < 1e-12 for k in calculated)
                case['metrics'] = calculated
        else:
            case['error'] = result['error']
        cases.append(case)
    groups = {}
    for name, members in [('all_answerable', [c for c in cases if c['type'] != 'unanswerable']),
                          ('single_document', [c for c in cases if c['type'] == 'single_document']),
                          ('cross_document', [c for c in cases if c['type'] == 'cross_document'])]:
        scored = [c for c in members if c['retrieval_scored']]
        count = len(scored)
        hits = sum(len(c['gold_hit_ids']) for c in scored)
        denominator = sum(min(10, c['gold_count']) for c in scored)
        overall_np = metrics.overall_normalized_precision_at_k([(c['selected_ids'], c['gold_ids']) for c in scored], 10)
        assert overall_np == (hits / denominator if denominator else None)
        groups[name] = {'planned_questions': len(members), 'scored_questions': count,
                        'gold_hits': hits, 'attainable_gold': denominator,
                        'precision_ceiling': denominator / (10 * count) if count else None,
                        'all_gold_selected': sum(not c['gold_missing_ids'] for c in scored),
                        'metrics': {'precision': sum(c['metrics']['precision'] for c in scored) / count if count else None,
                                    'normalized_precision': overall_np,
                                    'recall': sum(c['metrics']['recall'] for c in scored) / count if count else None,
                                    'map': sum(c['metrics']['average_precision'] for c in scored) / count if count else None,
                                    'mrr': sum(c['metrics']['reciprocal_rank'] for c in scored) / count if count else None}}
    baseline = json.loads((OUT / 'baseline_hashes.json').read_text())
    changed = [name for name, digest in baseline.items() if sha(ROOT / name) != digest]
    unexpected_changes = [name for name in changed if name not in {'PROGRESS.md', 'README.md'}]
    assert not unexpected_changes
    payload = {'top_k': 10, 'method': 'actual main selected_ids; no second retrieval/generation',
               'unanswerable_skipped': [c['id'] for c in cases if not c['gold_count']],
               'groups': groups, 'cases': cases}
    save(OUT / 'retrieval_metrics.json', payload)
    save(OUT / 'verification_after_run.json', {'baseline_files_checked': len(baseline),
         'baseline_changed': changed, 'unexpected_production_or_data_changes': unexpected_changes,
         'gold_mapping_matches_freeze': True,
         'metric_records_independently_recomputed': sum(c['retrieval_scored'] for c in cases),
         'metrics_per_record': 5, 'initial_pool_trace_matches_ranking': True,
         'selected_registry_alignment': True, 'production_tests': 'Not rerun: no production changes; historical 79 tests are not a new result.'})
    print(json.dumps({'groups': groups, 'unchanged_baseline_files': len(baseline)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
