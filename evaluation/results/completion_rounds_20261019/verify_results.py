"""Independent metric, checkpoint, query-budget and preservation verification."""
import ast
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def compute(ids, gold):
    gold = set(gold)
    hits = 0
    total = 0
    first = 0
    seen = set()
    for rank, cid in enumerate(ids[:10], 1):
        if cid in gold and cid not in seen:
            hits += 1
            total += hits / rank
            first = first or rank
        seen.add(cid)
    return dict(precision=hits / 10, recall=hits / len(gold),
                ap=total / len(gold), rr=1 / first if first else 0)


def main():
    rows = 0
    completed = 0
    audit = []
    expected_main_ids = None
    for name in ('new', 'old_core', 'old_validation', 'old_three_papers'):
        report = json.loads((OUT / name / 'results.json').read_text())
        assert report['status'] == 'completed' and report['inputs_unchanged']
        assert report['api_call_count'] == 0 and report['api_calls'] == []
        frozen = {q['id']: q for q in json.loads((ROOT / 'evaluation/results/evidence_gap_20261019' / name / 'results.json').read_text())['questions']}
        methods = {}
        for q in report['questions']:
            if q['status'] != 'completed':
                assert q['status'] == 'skipped_no_gold'
                continue
            completed += 1
            for method, row in frozen[q['id']]['metrics_by_k']['10'].items():
                assert row == q['metrics_by_k']['10'][method]
            trace = q['evidence_completion']
            history = trace['round_history']
            assert trace['max_rounds'] == 3 and len(history) == trace['completed_passes'] <= 3
            assert trace['rounds'] == sum(bool(r['supplement_queries']) for r in history)
            assert trace['supplement_queries'] == sum(r['supplement_queries'] for r in history) <= 12
            previous = set(q['stage_ids'].get('decomposition_global', q['stage_ids']['global_reranker']))
            signatures = set()
            for item in history:
                assert item['candidate_depth'] == 60 * item['round']
                assert len(item['tasks']) <= 4
                current = set(item['merged_candidate_ids'])
                assert previous <= current
                assert set(item['new_candidate_ids']) == current - previous
                previous = current
                ids = item['selected_ids']
                assert len(ids) == len(set(ids)) <= 10 and set(ids) <= current
                ranks = [item['merged_candidate_ids'].index(cid) for cid in ids]
                assert ranks == sorted(ranks)
                performed = [t for t in item['tasks'] if t['search_performed']]
                assert len(performed) == item['supplement_queries'] <= 4
                for task in performed:
                    key = task['query'], task['source'], task['effective_depth']
                    assert key not in signatures
                    signatures.add(key)
            for method, row in q['metrics_by_k']['10'].items():
                expected = compute(row['retrieved_ids'], q['gold_ids'])
                assert all(math.isclose(row[k], v, abs_tol=1e-12) for k, v in expected.items())
                methods.setdefault(method, []).append(expected)
                rows += 1
            one = q['metrics_by_k']['10']['Evidence Completion (one round)']['retrieved_ids']
            three = q['metrics_by_k']['10']['Evidence Completion (up to 3 rounds)']['retrieved_ids']
            assert one == (history[0]['selected_ids'] if history else trace['selected_ids_after'])
            assert three == trace['selected_ids_after']
            if name == 'new' and q['id'] == 'n07':
                expected_main_ids = three
            if history:
                audit.append({'set': name, 'id': q['id'], 'gold_ids': q['gold_ids'],
                    'audit_only_gold_not_used_in_runtime': True,
                    'stop_reason': trace['stop_reason'],
                    'passes': [{'round': r['round'],
                        'gold_in_pool': [g for g in q['gold_ids'] if g in r['merged_candidate_ids']],
                        'selected_gold_ranks': {str(g): r['selected_ids'].index(g) + 1 if g in r['selected_ids'] else None
                                                for g in q['gold_ids']},
                        'new_candidates': len(r['new_candidate_ids']),
                        'queries': r['supplement_queries']} for r in history]})
        for method, values in methods.items():
            for target, source in [('precision', 'precision'), ('recall', 'recall'), ('map', 'ap'), ('mrr', 'rr')]:
                assert math.isclose(report['metrics']['10'][method][target],
                                    sum(v[source] for v in values) / len(values), abs_tol=1e-12)
    hashes = json.loads((OUT / 'baseline_hashes.json').read_text())
    changed = [name for name, digest in hashes.items()
               if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    allowed = {'main.py', 'evaluation/run_evaluation.py', 'src/evidence_gap.py',
               'tests/test_evidence_gap.py', 'README.md', 'PROGRESS.md'}
    assert set(changed) <= allowed
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
               for name, digest in json.loads((OUT / 'candidate_hashes.json').read_text()).items())
    baseline = ast.parse((OUT / 'baseline/main.py').read_text())
    current = ast.parse((ROOT / 'main.py').read_text())
    for name in ('build_context', 'build_prompt', 'build_evidence_context'):
        find = lambda tree: next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        assert ast.dump(find(baseline)) == ast.dump(find(current))
    source = (ROOT / 'main.py').read_text()
    assert all(flag + ' = False' in source for flag in ('USE_MULTI_QUERY', 'USE_HYDE', 'USE_EVIDENCE_COMPLETION'))
    tests = (OUT / 'tests_final.log').read_text()
    assert 'Ran 62 tests' in tests and tests.strip().endswith('OK')
    replay = json.loads((OUT / 'main_replay.json').read_text())
    assert replay['status'] == 'passed' and replay['api_calls'] == 0 and replay['generation'] == 'stubbed'
    assert replay['selected_ids'] == expected_main_ids
    (OUT / 'round_gold_review.json').write_text(json.dumps(audit, indent=2) + '\n')
    secret = json.loads((ROOT / 'api.local.json').read_text()).get('api_key')
    paths = [p for p in OUT.rglob('*') if p.is_file() and p.suffix in ('.json', '.py', '.log', '.md')]
    document = ROOT / 'docs/COMPLETION_ROUNDS_2026-10-19.md'
    paths.append(document)
    assert secret and all(secret not in p.read_text(errors='replace') for p in paths)
    links = re.findall(r'\]\(([^)]+)\)', document.read_text())
    for link in links:
        assert (document.parent / link.split('#')[0]).resolve().exists(), link
    result = {'status': 'passed', 'metric_rows_recomputed': rows, 'questions': completed,
              'api_calls': 0, 'changed_files': changed, 'preserved_registered_files': len(hashes) - len(changed),
              'default_flags_unchanged': True, 'prompt_context_ledger_unchanged': True,
              'configured_key_absent': True, 'report_links_valid': len(links),
              'tests': 62, 'main_three_pass_retrieval_matches_evaluation': True,
              'real_generation_runs': 0}
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
