"""Run the actual evaluation entry point on four fixed sets, with zero API calls."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import evaluation.run_evaluation as evaluation
    import src.api_llm as api

    def forbidden(*args, **kwargs):
        raise AssertionError('Generation API forbidden throughout fixed-query comparison')
    api.chat_completion = forbidden
    embedding = evaluation.load_embedding_model()
    reranker = evaluation.CrossEncoder(evaluation.RERANKER_NAME, device='cpu')
    evaluation.load_embedding_model = lambda: embedding
    evaluation.CrossEncoder = lambda *args, **kwargs: reranker
    prior = ROOT / 'evaluation/results/retrieval_optimization_20261019'
    independent = ROOT / 'evaluation/results/independent_validation_20261019'
    sets = [
        ('new', 'arxiv_next_questions_en.json', 'arxiv-pilot-5-20261019',
         independent / 'retrieval/results.json', independent / 'auxiliary.json'),
        ('old_core', 'arxiv_pilot_questions_en.json', 'arxiv-pilot-5-20261019',
         prior / 'verified_english_60/results.json', prior / 'auxiliary_final.json'),
        ('old_validation', 'arxiv_validation_questions_en.json', 'arxiv-pilot-5-20261019',
         prior / 'validation_60/results.json', None),
        ('old_three_papers', 'questions.json', 'semantic-mac-20261019',
         prior / 'legacy_60/results.json', None),
    ]
    reports = {}
    for name, questions, kb, frozen_path, cache in sets:
        output = OUT / name
        assert not (output / 'results.json').exists(), 'Preserve existing run; never silently rerun.'
        sys.argv = ['evaluation.run_evaluation', '--questions', str(ROOT / 'evaluation' / questions),
                    '--kb-version', kb, '--candidate-k', '60', '--top-k', '10',
                    '--complete-evidence', '--output-dir', str(output)]
        sys.argv += ['--auxiliary-cache', str(cache)] if cache else ['--no-auxiliary']
        print('Starting', name, 'using actual evaluation.main()', flush=True)
        with (OUT / f'{name}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
            evaluation.main()
        report = json.loads((output / 'results.json').read_text())
        frozen = json.loads(frozen_path.read_text())
        assert report['status'] == 'completed' and report['api_call_count'] == 0
        previous = {q['id']: q for q in frozen['questions']}
        for q in report['questions']:
            if q['status'] != 'completed':
                continue
            for method, row in previous[q['id']]['metrics_by_k']['10'].items():
                assert q['metrics_by_k']['10'][method] == row, (name, q['id'], method)
            trace = q['evidence_completion']
            assert trace['rounds'] <= 1 and trace['supplement_queries'] <= 4
            selected = trace['selected_ids_after']
            assert len(set(selected)) == len(selected) <= 10
        reports[name] = report
        print(name, json.dumps(report['metrics']['10']['Evidence Completion (one round)']), flush=True)

    baseline_name = 'Decomposition + Hybrid + Reranker'
    method = 'Evidence Completion (one round)'
    table = {}
    for name, report in reports.items():
        base = baseline_name if name in ('new', 'old_core') else 'Hybrid + Reranker + RRF Anchor'
        table[name] = {'baseline': report['metrics']['10'][base], 'completion': report['metrics']['10'][method]}
    types = {q['id']: q['type'] for q in json.loads((ROOT / 'evaluation/arxiv_next_questions_en.json').read_text())}
    cross = [q for q in reports['new']['questions'] if q['status'] == 'completed' and types[q['id']] == 'cross_document']
    table['new_cross'] = {label: evaluation.summarize_results([
        (q['metrics_by_k']['10'][name]['retrieved_ids'], q['gold_ids']) for q in cross], 10)
        for label, name in [('baseline', baseline_name), ('completion', method)]}
    timing = []
    for report in reports.values():
        for q in report['questions']:
            if q['status'] == 'completed':
                extra = q['evidence_completion']['elapsed_seconds']
                base = max(.000001, q['retrieval_seconds'] - extra)
                timing.append({'id': q['id'], 'baseline_proxy_seconds': base,
                               'completion_extra_seconds': extra, 'ratio': (base + extra) / base})
    ratios = [q['ratio'] for q in timing]
    gates = {
        'cross_recall_gain': table['new_cross']['completion']['recall'] - table['new_cross']['baseline']['recall'] >= .10,
        'new_map_mrr': all(table['new']['completion'][k] >= table['new']['baseline'][k] - .01 for k in ('map', 'mrr')),
        'old_recall': all(table[s]['completion']['recall'] >= table[s]['baseline']['recall'] for s in ('old_core', 'old_validation', 'old_three_papers')),
        'old_map_mrr': all(table[s]['completion'][k] >= table[s]['baseline'][k] - .01 for s in ('old_core', 'old_validation', 'old_three_papers') for k in ('map', 'mrr')),
        'evaluation_median_cost_ratio': statistics.median(ratios) <= 2.0,
    }
    result = {'metrics': table, 'gates': gates,
              'decision': 'eligible_for_small_generation_check' if all(gates.values()) else 'retain_baseline_opt_in_only',
              'api_calls': 0, 'baseline_all_method_rows_identical': True,
              'timing': timing, 'median_evaluation_cost_ratio': statistics.median(ratios),
              'baseline_input_hashes': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                      for _, _, _, path, _ in sets}}
    save(OUT / 'comparison.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
