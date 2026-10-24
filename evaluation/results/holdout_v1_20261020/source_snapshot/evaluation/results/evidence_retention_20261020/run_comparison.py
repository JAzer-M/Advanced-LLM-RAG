"""Actual evaluation CLI: before/after retention, candidate 60/120, independent k10/k20."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    import numpy as np
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import evaluation.run_evaluation as evaluation
    import main as pipeline
    import src.api_llm as api
    from src.knowledge_base import load_knowledge_base
    api.chat_completion = lambda *a, **k: (_ for _ in ()).throw(AssertionError('No API in this experiment'))
    spec = importlib.util.spec_from_file_location('before_retention_gap', OUT / 'baseline/src/evidence_gap.py')
    old_gap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_gap)
    fixed_completion = evaluation.complete_evidence
    embedding = evaluation.load_embedding_model()
    reranker = evaluation.CrossEncoder(evaluation.RERANKER_NAME, device='cpu')
    evaluation.load_embedding_model = lambda: embedding
    evaluation.CrossEncoder = lambda *a, **k: reranker
    original_predict, cache = reranker.predict, {}
    stats = {'unique_pairs': 0, 'reused_pairs': 0}

    def cached_predict(pairs):
        missing = list(dict.fromkeys(tuple(pair) for pair in pairs if tuple(pair) not in cache))
        if missing:
            cache.update((pair, float(score)) for pair, score in zip(missing, original_predict(missing)))
        stats['unique_pairs'] += len(missing)
        stats['reused_pairs'] += len(pairs) - len(missing)
        return np.array([cache[tuple(pair)] for pair in pairs], dtype=np.float32)

    reranker.predict = cached_predict
    _, chunks, _ = load_knowledge_base(ROOT / 'data/processed', 'all-papers-8-20261020')
    questions = json.loads((ROOT / 'evaluation/all_papers_questions_en.json').read_text())
    auxiliary = json.loads((ROOT / 'evaluation/results/all_papers_20261020/auxiliary.json').read_text())
    previous = {q['id']: q for q in json.loads((ROOT / 'evaluation/results/all_papers_20261020/comparison.json').read_text())['questions']}
    variants = [('old_selection_candidate120', 120, old_gap.complete_evidence),
                ('fixed_selection_candidate120', 120, fixed_completion),
                ('old_selection_candidate60', 60, old_gap.complete_evidence),
                ('fixed_selection_candidate60', 60, fixed_completion)]
    reports = {name: [] for name, _, _ in variants}
    processing = {}
    started = time.perf_counter()
    for question in questions:
        if not question.get('gold_evidence'):
            continue
        qid = question['id']
        cache.clear()
        stats.update(unique_pairs=0, reused_pairs=0)
        qpath, apath = OUT / 'inputs' / f'{qid}.json', OUT / 'inputs' / f'{qid}_auxiliary.json'
        save(qpath, [question])
        save(apath, {qid: auxiliary[qid]})
        for name, candidate_k, completion in variants:
            target = OUT / name / qid
            if (target / 'results.json').exists():
                report = json.loads((target / 'results.json').read_text())
                assert report['status'] == 'completed'
            else:
                evaluation.complete_evidence = completion
                sys.argv = ['evaluation.run_evaluation', '--questions', str(qpath),
                            '--kb-version', 'all-papers-8-20261020', '--candidate-k', str(candidate_k),
                            '--top-k', '10', '20', '--complete-evidence', '--completion-rounds', '2',
                            '--auxiliary-cache', str(apath), '--output-dir', str(target)]
                print('Starting actual evaluation.main()', qid, name, flush=True)
                with (OUT / f'{qid}_{name}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
                    evaluation.main()
                report = json.loads((target / 'results.json').read_text())
            assert report['status'] == 'completed' and report['api_call_count'] == 0 and report['inputs_unchanged']
            row = report['questions'][0]
            if name == 'old_selection_candidate60':
                for method, scores in row['metrics_by_k']['10'].items():
                    assert scores == previous[qid]['metrics_by_k']['10'][method], (qid, method, 'old control changed')
            if name.startswith('fixed'):
                for k, trace in row['evidence_completion_by_k'].items():
                    assert trace['completed_passes'] <= 2
                    for step in trace['round_history']:
                        assert set(trace['retained_local_ids']) <= set(step['selected_ids'])
                        assert len(step['selected_ids']) == len(set(step['selected_ids'])) == int(k)
            reports[name].append(report)
        processing[qid] = dict(stats)
        save(OUT / 'processing_cost.json', processing)
        print('Completed question', qid, json.dumps(stats), flush=True)
    method = 'Evidence Completion (up to 2 rounds)'
    qmap = {q['id']: q for q in questions}
    result = {'status': 'completed', 'api_calls': 0, 'variants': {},
              'skipped_no_gold': [q['id'] for q in questions if not q.get('gold_evidence')],
              'elapsed_seconds': round(time.perf_counter() - started, 3),
              'old60_k10_previous_rows_identical': True,
              'timing_limit': 'Shared model/score cache; elapsed is not per-mode production latency.'}
    contexts = {}
    for name, group in reports.items():
        rows = [r['questions'][0] for r in group]
        groups = {'all': rows,
                  'old': [q for q in rows if qmap[q['id']]['cohort'] != 'new_all_papers'],
                  'new': [q for q in rows if qmap[q['id']]['cohort'] == 'new_all_papers'],
                  'single': [q for q in rows if qmap[q['id']]['type'] == 'single_document'],
                  'cross': [q for q in rows if qmap[q['id']]['type'] != 'single_document']}
        groups.update({cohort: [q for q in rows if qmap[q['id']]['cohort'] == cohort]
                       for cohort in dict.fromkeys(qmap[q['id']]['cohort'] for q in rows)})
        table = {}
        for k in [10, 20]:
            table[str(k)] = {}
            for label, members in groups.items():
                table[str(k)][label] = {}
                for m in rows[0]['metrics_by_k'][str(k)]:
                    cases = [(q['metrics_by_k'][str(k)][m]['retrieved_ids'], q['gold_ids']) for q in members]
                    table[str(k)][label][m] = {**evaluation.summarize_results(cases, k),
                                              'full_gold': sum(set(g) <= set(r) for r, g in cases)}
        contexts[name] = {}
        for k in [10, 20]:
            contexts[name][str(k)] = {}
            for q in rows:
                selected = [chunks[cid] for cid in q['metrics_by_k'][str(k)][method]['retrieved_ids']]
                context, ledger = pipeline.build_evidence_context(chunks, selected)
                contexts[name][str(k)][q['id']] = {'context_characters': len(context),
                                                  'citation_registry_count': len(ledger['citation_registry'])}
        result['variants'][name] = {'metrics': table, 'questions': rows,
            'sum_evaluation_seconds': sum(r['elapsed_seconds'] for r in group),
            'input_sha256': {p: h for r in group for p, h in r['input_sha256'].items()}}
    save(OUT / 'context_cost.json', contexts)
    save(OUT / 'comparison.json', result)
    print('Completed all 42 questions; API calls 0', flush=True)
    for name, variant in result['variants'].items():
        for k in ['10', '20']:
            print(name, 'k='+k, json.dumps(variant['metrics'][k]['all'][method]), flush=True)


if __name__ == '__main__':
    main()
