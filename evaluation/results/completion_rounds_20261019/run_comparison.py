"""Actual run_evaluation, shared 1/3-round trajectory, frozen 0/1 references, no API."""
from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import evaluation.run_evaluation as evaluation
    import src.api_llm as api
    def forbidden(*args, **kwargs):
        raise AssertionError('API forbidden throughout this experiment')
    api.chat_completion = forbidden
    embedding = evaluation.load_embedding_model()
    reranker = evaluation.CrossEncoder(evaluation.RERANKER_NAME, device='cpu')
    evaluation.load_embedding_model = lambda: embedding
    evaluation.CrossEncoder = lambda *args, **kwargs: reranker
    previous = ROOT / 'evaluation/results/evidence_gap_20261019'
    old = ROOT / 'evaluation/results/retrieval_optimization_20261019'
    independent = ROOT / 'evaluation/results/independent_validation_20261019'
    sets = [
        ('new', 'arxiv_next_questions_en.json', 'arxiv-pilot-5-20261019', independent / 'auxiliary.json'),
        ('old_core', 'arxiv_pilot_questions_en.json', 'arxiv-pilot-5-20261019', old / 'auxiliary_final.json'),
        ('old_validation', 'arxiv_validation_questions_en.json', 'arxiv-pilot-5-20261019', None),
        ('old_three_papers', 'questions.json', 'semantic-mac-20261019', None),
    ]
    reports = {}
    one = 'Evidence Completion (one round)'
    three = 'Evidence Completion (up to 3 rounds)'
    for name, questions, version, cache in sets:
        output = OUT / name
        assert not (output / 'results.json').exists(), 'Preserve an existing run rather than rerun.'
        sys.argv = ['evaluation.run_evaluation', '--questions', str(ROOT / 'evaluation' / questions),
                    '--kb-version', version, '--candidate-k', '60', '--top-k', '10',
                    '--complete-evidence', '--completion-rounds', '1', '3', '--output-dir', str(output)]
        sys.argv += ['--auxiliary-cache', str(cache)] if cache else ['--no-auxiliary']
        print('Starting', name, 'actual evaluation.main()', flush=True)
        with (OUT / f'{name}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
            evaluation.main()
        report = json.loads((output / 'results.json').read_text())
        assert report['status'] == 'completed' and report['api_call_count'] == 0
        frozen = {q['id']: q for q in json.loads((previous / name / 'results.json').read_text())['questions']}
        for q in report['questions']:
            if q['status'] != 'completed':
                continue
            # Every previous method, including the one-round candidate, must replay exactly.
            for method, row in frozen[q['id']]['metrics_by_k']['10'].items():
                assert q['metrics_by_k']['10'][method] == row, (name, q['id'], method)
            trace = q['evidence_completion']
            assert trace['rounds'] <= 3 and trace['supplement_queries'] <= 12
            assert trace['completed_passes'] <= 3
        reports[name] = report
        print(name, json.dumps(report['metrics']['10'][three]), flush=True)
    table = {}
    base_names = {}
    for name, report in reports.items():
        base = 'Decomposition + Hybrid + Reranker' if name in ('new', 'old_core') else 'Hybrid + Reranker + RRF Anchor'
        base_names[name] = base
        table[name] = {label: report['metrics']['10'][method] for label, method in [('zero', base), ('one', one), ('three', three)]}
    types = {q['id']: q['type'] for q in json.loads((ROOT / 'evaluation/arxiv_next_questions_en.json').read_text())}
    cross = [q for q in reports['new']['questions'] if q['status'] == 'completed' and types[q['id']] == 'cross_document']
    table['new_cross'] = {label: evaluation.summarize_results([
        (q['metrics_by_k']['10'][method]['retrieved_ids'], q['gold_ids']) for q in cross], 10)
        for label, method in [('zero', base_names['new']), ('one', one), ('three', three)]}
    gates = {
        'new_cross_recall': table['new_cross']['three']['recall'] >= table['new_cross']['zero']['recall'] + .10,
        'new_map_mrr': all(table['new']['three'][k] >= table['new']['zero'][k] - .01 for k in ('map', 'mrr')),
        'old_recall': all(table[s]['three']['recall'] >= table[s]['zero']['recall'] for s in ('old_core', 'old_validation', 'old_three_papers')),
        'old_map_mrr': all(table[s]['three'][k] >= table[s]['zero'][k] - .01 for s in ('old_core', 'old_validation', 'old_three_papers') for k in ('map', 'mrr')),
    }
    cases = []
    for name, report in reports.items():
        for q in report['questions']:
            if q['status'] != 'completed':
                continue
            trace = q['evidence_completion']
            if not trace['round_history']:
                continue
            history = trace['round_history']
            cases.append({'set': name, 'id': q['id'], 'passes': trace['completed_passes'],
                          'retrieval_rounds': trace['rounds'], 'queries': trace['supplement_queries'],
                          'stop_reason': trace['stop_reason'],
                          'new_candidates_by_pass': [len(r['new_candidate_ids']) for r in history],
                          'one_seconds': history[0]['elapsed_seconds'], 'three_seconds': trace['elapsed_seconds'],
                          'additional_pass_seconds': sum(r['elapsed_seconds'] for r in history[1:])})
    result = {'metrics': table, 'gates': gates,
              'decision': 'passes_retrieval_gates' if all(gates.values()) else 'retain_disabled_default',
              'api_calls': 0, 'previous_zero_one_rows_identical': True, 'affected_cases': cases,
              'median_additional_pass_seconds': statistics.median(c['additional_pass_seconds'] for c in cases),
              'elapsed_evaluation_seconds': sum(r['elapsed_seconds'] for r in reports.values())}
    (OUT / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
