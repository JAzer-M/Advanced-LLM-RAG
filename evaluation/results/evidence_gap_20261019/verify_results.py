"""Independent arithmetic, preservation and budget checks; no model/API calls."""
import ast
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def scores(ids, gold):
    gold = set(gold)
    hits = 0
    precision_sum = 0
    first = 0
    seen = set()
    for rank, cid in enumerate(ids[:10], 1):
        if cid in gold and cid not in seen:
            hits += 1
            precision_sum += hits / rank
            first = first or rank
        seen.add(cid)
    return dict(precision=hits / 10, recall=hits / len(gold),
                ap=precision_sum / len(gold), rr=1 / first if first else 0)


def main():
    rows = 0
    completed = 0
    triggered = []
    for name in ('new', 'old_core', 'old_validation', 'old_three_papers'):
        report = json.loads((OUT / name / 'results.json').read_text())
        assert report['status'] == 'completed' and report['inputs_unchanged']
        assert report['api_call_count'] == 0 and not report['api_calls']
        methods = {}
        for q in report['questions']:
            if q['status'] == 'skipped_no_gold':
                continue
            completed += 1
            trace = q['evidence_completion']
            assert trace['coverage'] == 'heuristic_only'
            assert trace['rounds'] <= 1 and trace['supplement_queries'] <= 4
            ids = trace['selected_ids_after']
            assert len(ids) == len(set(ids)) <= 10
            assert ids == q['metrics_by_k']['10']['Evidence Completion (one round)']['retrieved_ids']
            if 'merged_candidate_ids' in trace:
                assert set(q['stage_ids'].get('decomposition_global', q['stage_ids']['global_reranker'])) <= set(trace['merged_candidate_ids'])
                assert set(ids) <= set(trace['merged_candidate_ids'])
                for task in trace['tasks']:
                    assert len(task['scoped_top_ids']) <= 3
                triggered.append({'set': name, 'id': q['id'], 'queries': trace['supplement_queries']})
            else:
                assert trace['stop_reason'] in ('not_explicit_cross_paper', 'no_coverage_signal')
                assert trace['selected_ids_before'] == trace['selected_ids_after']
            for method, row in q['metrics_by_k']['10'].items():
                computed = scores(row['retrieved_ids'], q['gold_ids'])
                assert all(math.isclose(computed[k], row[k], abs_tol=1e-12) for k in computed)
                methods.setdefault(method, []).append(computed)
                rows += 1
        for method, values in methods.items():
            summary = report['metrics']['10'][method]
            for target, source in [('precision', 'precision'), ('recall', 'recall'), ('map', 'ap'), ('mrr', 'rr')]:
                assert math.isclose(summary[target], sum(v[source] for v in values) / len(values), abs_tol=1e-12)
    hashes = json.loads((OUT / 'baseline_hashes.json').read_text())
    changed = [name for name, digest in hashes.items()
               if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    assert set(changed) <= {'main.py', 'evaluation/run_evaluation.py', 'README.md', 'PROGRESS.md'}, changed
    baseline = ast.parse((OUT / 'baseline/main.py').read_text())
    current = ast.parse((ROOT / 'main.py').read_text())
    for name in ('build_context', 'build_prompt', 'build_evidence_context', 'deduplicate_candidates'):
        before = next(n for n in baseline.body if isinstance(n, ast.FunctionDef) and n.name == name)
        after = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == name)
        assert ast.dump(before) == ast.dump(after), name
    main_source = (ROOT / 'main.py').read_text()
    assert 'USE_EVIDENCE_COMPLETION = False' in main_source
    module_source = (ROOT / 'src/evidence_gap.py').read_text()
    assert not any(term in module_source for term in ('gold_ids', 'gold_evidence', 'reference_points', 'chat_completion'))
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
               for name, digest in json.loads((OUT / 'candidate_hashes.json').read_text()).items())
    replay = json.loads((OUT / 'main_replay.json').read_text())
    assert replay['status'] == 'passed' and replay['api_calls'] == 0 and replay['generation'] == 'stubbed'
    tests = (OUT / 'tests_final.log').read_text()
    assert 'Ran 58 tests' in tests and tests.strip().endswith('OK')
    secret = json.loads((ROOT / 'api.local.json').read_text()).get('api_key')
    paths = [p for p in OUT.rglob('*') if p.is_file() and p.suffix in ('.json', '.md', '.py', '.log')]
    paths.append(ROOT / 'docs/EVIDENCE_COMPLETION_2026-10-19.md')
    if secret:
        assert all(secret not in p.read_text(errors='replace') for p in paths)
    links = re.findall(r'\]\(([^)]+)\)', paths[-1].read_text())
    for link in links:
        if not link.startswith(('http:', 'https:', '#')):
            assert (paths[-1].parent / link.split('#')[0]).resolve().exists(), link
    result = {'status': 'passed', 'independently_recomputed_metric_rows': rows,
              'answerable_questions': completed, 'api_calls': 0, 'triggered': triggered,
              'preserved_registered_files': len(hashes) - len(changed),
              'intentional_changed_files': changed, 'prompt_context_ledger_unchanged': True,
              'default_completion_disabled': True, 'configured_key_absent': bool(secret),
              'report_links_valid': len(links), 'tests': 58,
              'main_retrieval_replays': len(replay['cases']), 'real_generation_runs': 0}
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
