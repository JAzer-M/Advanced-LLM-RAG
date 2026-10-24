"""Independently recount normalized metrics and check preservation of old assets."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, default=OUT.parents[2])
    parser.add_argument('--output', type=Path, default=OUT / 'verification.json')
    args = parser.parse_args()
    root = args.project_dir
    report = read(OUT / 'report.json')
    original = read(root / 'evaluation/results/evidence_retention_20261020/comparison.json')
    qmap = {q['id']: q for q in read(root / 'evaluation/all_papers_questions_en.json')}
    chunks = read(root / 'data/processed/versions/all-papers-8-20261020/chunks.json')
    norm = lambda text: re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).lower().strip()
    mapped = {}
    for qid, question in qmap.items():
        if not question.get('gold_evidence'):
            continue
        ids = set()
        for evidence in question['gold_evidence']:
            matches = {c['chunk_id'] for c in chunks if c['source'] == evidence['source']
                       and c['page'] == evidence['page'] and norm(evidence['quote']) in norm(c['text'])}
            assert matches, (qid, 'unmatched Gold quote')
            ids.update(matches)
        mapped[qid] = ids
    row_count = group_count = 0
    assert set(report['variants']) == set(original['variants'])
    for variant, old in original['variants'].items():
        new = report['variants'][variant]
        assert [q['id'] for q in new['questions']] == [q['id'] for q in old['questions']]
        rows = {q['id']: q for q in new['questions']}
        for q in old['questions']:
            gold = mapped[q['id']]
            assert set(q['gold_ids']) == set(rows[q['id']]['gold_ids']) == gold
            for key, methods in q['metrics_by_k'].items():
                k = int(key)
                for method, scores in methods.items():
                    ids = scores['retrieved_ids'][:k]
                    hits = len(set(ids) & gold)
                    seen, cumulative, ap_sum, rr = set(), 0, 0, 0
                    for rank, cid in enumerate(ids, 1):
                        if cid in gold and cid not in seen:
                            cumulative += 1
                            ap_sum += cumulative / rank
                            rr = rr or 1 / rank
                        seen.add(cid)
                    computed = {'precision': hits / k, 'recall': hits / len(gold),
                                'ap': ap_sum / len(gold), 'rr': rr,
                                'normalized_precision': hits / min(k, len(gold))}
                    new_scores = rows[q['id']]['metrics_by_k'][key][method]
                    assert new_scores['retrieved_ids'] == scores['retrieved_ids']
                    for field, value in computed.items():
                        assert math.isclose(value, new_scores[field], abs_tol=1e-12)
                        if field != 'normalized_precision':
                            assert new_scores[field] == scores[field]
                    row_count += 1
        for key, groups in old['metrics'].items():
            k = int(key)
            for group, methods in groups.items():
                members = [q for q in old['questions'] if group == 'all'
                           or group == 'old' and qmap[q['id']]['cohort'] != 'new_all_papers'
                           or group == 'new' and qmap[q['id']]['cohort'] == 'new_all_papers'
                           or group == 'single' and qmap[q['id']]['type'] == 'single_document'
                           or group == 'cross' and qmap[q['id']]['type'] != 'single_document'
                           or group == qmap[q['id']]['cohort']]
                denominator = sum(min(k, len(mapped[q['id']])) for q in members)
                for method, scores in methods.items():
                    new_scores = new['metrics'][key][group][method]
                    for field, value in scores.items():
                        assert math.isclose(value, new_scores[field], abs_tol=1e-12)
                    hits = sum(len(set(q['metrics_by_k'][key][method]['retrieved_ids'][:k])
                                   & mapped[q['id']]) for q in members)
                    assert new_scores['hits'] == hits
                    assert new_scores['attainable_gold'] == denominator
                    assert math.isclose(new_scores['normalized_precision'], hits / denominator, abs_tol=1e-12)
                    assert math.isclose(new_scores['normalized_precision'],
                                        new_scores['precision'] / new_scores['precision_ceiling'], abs_tol=1e-12)
                    group_count += 1
    allowed = {'evaluation/metrics.py', 'evaluation/run_evaluation.py',
               'tests/test_evaluation_alignment.py', 'README.md', 'PROGRESS.md'}
    baseline = read(OUT / 'baseline_hashes.json')
    changed = [name for name, digest in baseline.items()
               if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest]
    assert set(changed) <= allowed, changed
    assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
               for name, digest in report['input_sha256'].items())
    summary = {'status': 'passed', 'independently_verified_question_rows': row_count,
               'independently_verified_aggregate_rows': group_count,
               'gold_maps_verified': len(mapped), 'original_metric_values_and_selected_ids_preserved': True,
               'baseline_files_checked': len(baseline), 'intentional_changed_baseline_files': changed,
               'baseline_files_preserved': len(baseline) - len(changed),
               'api_calls': 0, 'model_inference_calls': 0,
               'implementation_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                          for name in ['evaluation/metrics.py', 'evaluation/run_evaluation.py',
                                                       'evaluation/summarize_normalized_precision.py']
                                          if (root / name).exists()}}
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
