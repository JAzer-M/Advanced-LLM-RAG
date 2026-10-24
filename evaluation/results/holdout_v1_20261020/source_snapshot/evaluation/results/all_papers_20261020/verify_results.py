"""Independently recompute every stored score, validate provenance and adoption gates."""
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(path.read_text())


def scores(retrieved, gold):
    gold, seen, hits, accumulated, rr = set(gold), set(), 0, 0, 0
    for rank, cid in enumerate(retrieved[:10], 1):
        if cid in seen:
            continue
        seen.add(cid)
        if cid in gold:
            hits += 1
            accumulated += hits / rank
            rr = rr or 1 / rank
    return {'precision': hits / 10, 'recall': hits / len(gold), 'ap': accumulated / len(gold), 'rr': rr}


def main():
    import numpy as np
    from src.knowledge_base import load_knowledge_base
    result = read(OUT / 'comparison.json')
    assert result['status'] == 'completed' and result['api_call_count'] == 0
    questions = read(ROOT / 'evaluation/all_papers_questions_en.json')
    qmap = {q['id']: q for q in questions}
    normalize = lambda value: re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value)).lower().strip()
    index, chunks, _ = load_knowledge_base(ROOT / 'data/processed', 'all-papers-8-20261020')
    assert len(chunks) == 1397 and index.d == 384
    offset = 0
    for version in ('semantic-mac-20261019', 'arxiv-pilot-5-20261019'):
        original_index, originals, _ = load_knowledge_base(ROOT / 'data/processed', version)
        assert np.array_equal(index.reconstruct_n(offset, len(originals)), original_index.reconstruct_n(0, len(originals)))
        assert [{**c, 'chunk_id': offset + c['chunk_id']} for c in originals] == chunks[offset:offset + len(originals)]
        offset += len(originals)
    for cohort in ['questions', 'arxiv_pilot_questions_en', 'arxiv_validation_questions_en', 'arxiv_next_questions_en']:
        assert [{k: v for k, v in q.items() if k != 'cohort'} for q in questions if q['cohort'] == cohort] == read(ROOT / f'evaluation/{cohort}.json')
    row_count = 0
    for q in result['questions']:
        question = qmap[q['id']]
        mapped = set()
        for evidence in question['gold_evidence']:
            matches = {c['chunk_id'] for c in chunks if c['source'] == evidence['source']
                       and c['page'] == evidence['page'] and normalize(evidence['quote']) in normalize(c['text'])}
            assert matches, (q['id'], evidence)
            mapped.update(matches)
        assert mapped == set(q['gold_ids'])
        for method, row in q['metrics_by_k']['10'].items():
            ids = row['retrieved_ids']
            assert len(ids) == len(set(ids)) == 10 and all(0 <= cid < len(chunks) for cid in ids)
            for key, value in scores(ids, q['gold_ids']).items():
                assert math.isclose(value, row[key], abs_tol=1e-12), (q['id'], method, key)
            row_count += 1
        for mode, trace in q['query_modes'].items():
            comp = trace['evidence_completion']
            assert comp['completed_passes'] <= 2 and comp['supplement_queries'] <= 8
            assert comp['completed_passes'] == len(comp['round_history'])
            assert comp['rounds'] == sum(bool(r['supplement_queries']) for r in comp['round_history'])
            assert set(trace['candidate_ids']) <= set(range(len(chunks)))
            for round_info in comp['round_history']:
                for task in round_info['tasks']:
                    assert all(chunks[cid]['source'] == task['source'] for cid in task.get('retrieved_ids', []))
            for cap in (0, 1, 2):
                history = [r for r in comp['round_history'] if r['round'] <= cap]
                expected = history[-1]['selected_ids'] if history else trace['selected_ids_before']
                assert q['metrics_by_k']['10'][f'Pipeline {mode} ({cap} rounds)']['retrieved_ids'] == expected
    def members(group):
        if group == 'all': return result['questions']
        return [q for q in result['questions'] if (
            (group == 'old' and qmap[q['id']]['cohort'] != 'new_all_papers') or
            (group == 'new' and qmap[q['id']]['cohort'] == 'new_all_papers') or
            (group == 'single' and qmap[q['id']]['type'] == 'single_document') or
            (group == 'cross' and qmap[q['id']]['type'] != 'single_document') or
            (group == 'new_cross' and qmap[q['id']]['cohort'] == 'new_all_papers' and qmap[q['id']]['type'] != 'single_document') or
            qmap[q['id']]['cohort'] == group)]
    for group, table in result['metrics'].items():
        group_rows = members(group)
        for method, summary in table.items():
            values = [scores(q['metrics_by_k']['10'][method]['retrieved_ids'], q['gold_ids']) for q in group_rows]
            assert summary['questions'] == len(values)
            for output, source in [('precision','precision'), ('recall','recall'), ('map','ap'), ('mrr','rr')]:
                assert math.isclose(summary[output], sum(v[source] for v in values) / len(values), abs_tol=1e-12)
            assert summary['full_gold'] == sum(set(q['gold_ids']) <= set(q['metrics_by_k']['10'][method]['retrieved_ids']) for q in group_rows)
    preserved, changed = [], []
    for name, digest in read(OUT / 'baseline_hashes.json').items():
        (preserved if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest else changed).append(name)
    allowed = {'evaluation/run_evaluation.py', 'tests/test_evaluation_alignment.py', 'PROGRESS.md', 'README.md'}
    assert set(changed) <= allowed, changed
    migration = read(ROOT / 'data/migration_manifest.json')['files']
    assert all(hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest() == entry['sha256']
               for entry in migration)
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
               for name, digest in read(OUT / 'candidate_hashes.json').items())
    assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
               for name, digest in result['input_sha256'].items())
    calls = read(OUT / 'api_calls.json') + read(OUT / 'answer_probe/api_calls.json')
    assert len(calls) <= 126 and all(c['status'] == 'completed' and c['response']['finish_reason'] == 'stop' for c in calls)
    assert len([c for c in calls if c.get('stage') == 'rewrite']) == 42
    assert len([c for c in calls if c.get('stage') == 'hyde']) == 42
    assert len([c for c in calls if c.get('stage') == 'decomposition']) == 26
    key = read(ROOT / 'api.local.json').get('api_key', '')
    assert key and all(key.encode() not in p.read_bytes() for p in OUT.rglob('*') if p.is_file())
    probe = read(OUT / 'answer_probe/summary.json')
    assert probe['real_answers'] == 8 and probe['all_main_ids_match_evaluation']
    review = read(OUT / 'answer_probe/review.json')
    assert len(review['rows']) == 8 and all(row['evaluation_ids_match'] for row in review['rows'])
    base, candidate = 'Pipeline base (0 rounds)', 'Pipeline both (2 rounds)'
    table = result['metrics']
    old_groups = ['questions', 'arxiv_pilot_questions_en', 'arxiv_validation_questions_en', 'arxiv_next_questions_en']
    gates = {'overall_map_gain': table['all'][candidate]['map'] >= table['all'][base]['map'] + .01,
             'new_cross_recall_gain': table['new_cross'][candidate]['recall'] >= table['new_cross'][base]['recall'] + .10,
             'old_cohort_recall': all(table[g][candidate]['recall'] >= table[g][base]['recall'] for g in old_groups),
             'old_cohort_map_mrr': all(table[g][candidate][k] >= table[g][base][k] - .01 for g in old_groups for k in ('map','mrr'))}
    usage = {k: sum((c['response'].get('usage') or {}).get(k, 0) for c in calls)
             for k in ('prompt_tokens','completion_tokens','total_tokens')}
    summary = {'status': 'passed', 'metric_rows_independently_recomputed': row_count,
               'immutable_baseline_files_preserved': len(preserved), 'intentional_changed_files': changed,
               'vectors_and_chunks_preserved_exactly': True, 'all_42_gold_maps_valid': True,
               'legacy_migration_files_match': len(migration),
               'all_8_real_main_selections_match_evaluation': True,
               'api_calls': len(calls), 'usage': usage, 'secrets_absent': True,
               'retrieval_adoption_gates_for_both_two': gates,
               'retrieval_gates_passed': all(gates.values()),
               'manual_review_core_complete': review['core_complete_by_condition'],
               'semantic_nonregression_gate_passed': review['paired_strict_regressions'] == 0,
               'decision': 'retain_defaults' if not all(gates.values()) else 'see_semantic_gate'}
    (OUT / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
