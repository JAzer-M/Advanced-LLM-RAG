"""Run the real evaluation CLI in resumable question shards with shared CPU models."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
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
    import src.api_llm as api
    api.chat_completion = lambda *a, **k: (_ for _ in ()).throw(AssertionError('API forbidden in retrieval evaluation'))
    embedding = evaluation.load_embedding_model()
    reranker = evaluation.CrossEncoder(evaluation.RERANKER_NAME, device='cpu')
    evaluation.load_embedding_model = lambda: embedding
    evaluation.CrossEncoder = lambda *a, **k: reranker
    original_predict = reranker.predict
    score_cache, stats = {}, {'unique_pairs': 0, 'reused_pairs': 0}

    def cached_predict(pairs):
        missing = list(dict.fromkeys(tuple(pair) for pair in pairs if tuple(pair) not in score_cache))
        if missing:
            scores = original_predict(missing)
            score_cache.update((pair, float(score)) for pair, score in zip(missing, scores))
        stats['unique_pairs'] += len(missing)
        stats['reused_pairs'] += len(pairs) - len(missing)
        return np.array([score_cache[tuple(pair)] for pair in pairs], dtype=np.float32)

    reranker.predict = cached_predict
    questions = json.loads((ROOT / 'evaluation/all_papers_questions_en.json').read_text())
    reports, timings = [], {}
    started = time.perf_counter()
    for question in questions:
        qid = question['id']
        if not question.get('gold_evidence'):
            continue
        target = OUT / 'retrieval' / qid
        if (target / 'results.json').exists():
            previous = json.loads((target / 'results.json').read_text())
            assert previous['status'] == 'completed', f'Preserve failed shard {qid} for review.'
            reports.append(previous)
            print('Reusing completed shard', qid, flush=True)
            continue
        while True:
            if (OUT / 'auxiliary.json').exists():
                try:
                    all_auxiliary = json.loads((OUT / 'auxiliary.json').read_text())
                    entry = all_auxiliary.get(qid, {})
                    if all(key in entry for key in ('decomposition', 'rewritten_query', 'hypothetical_document')):
                        break
                except json.JSONDecodeError:
                    pass  # A single writer is replacing this small checkpoint.
            time.sleep(2)
        qpath, apath = OUT / 'inputs' / f'{qid}.json', OUT / 'inputs' / f'{qid}_auxiliary.json'
        save(qpath, [question])
        save(apath, {qid: entry})
        sys.argv = ['evaluation.run_evaluation', '--questions', str(qpath), '--kb-version', 'all-papers-8-20261020',
                    '--candidate-k', '60', '--top-k', '10', '--complete-evidence', '--completion-rounds', '1', '2',
                    '--query-ablation', '--auxiliary-cache', str(apath), '--output-dir', str(target)]
        score_cache.clear()
        stats.update(unique_pairs=0, reused_pairs=0)
        print('Starting actual evaluation.main()', qid, flush=True)
        with (OUT / f'{qid}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
            evaluation.main()
        report = json.loads((target / 'results.json').read_text())
        assert report['status'] == 'completed' and report['api_call_count'] == 0 and report['inputs_unchanged']
        row = report['questions'][0]
        assert row['metrics_by_k']['10']['Pipeline base (0 rounds)'] == row['metrics_by_k']['10']['Decomposition + Hybrid + Reranker']
        for mode in row['query_modes'].values():
            assert mode['evidence_completion']['completed_passes'] <= 2
        reports.append(report)
        timings[qid] = {**stats, 'elapsed_seconds': report['elapsed_seconds']}
        save(OUT / 'processing_cost.json', timings)
        print('Completed', qid, json.dumps(timings[qid]), flush=True)
    rows = [report['questions'][0] for report in reports]
    methods = list(rows[0]['metrics_by_k']['10'])
    cohorts = {q['id']: q['cohort'] for q in questions}
    types = {q['id']: q['type'] for q in questions}
    groups = {'all': rows,
              'old': [q for q in rows if cohorts[q['id']] != 'new_all_papers'],
              'new': [q for q in rows if cohorts[q['id']] == 'new_all_papers'],
              'single': [q for q in rows if types[q['id']] == 'single_document'],
              'cross': [q for q in rows if types[q['id']] != 'single_document'],
              'new_cross': [q for q in rows if cohorts[q['id']] == 'new_all_papers' and types[q['id']] != 'single_document']}
    groups.update({cohort: [q for q in rows if cohorts[q['id']] == cohort]
                   for cohort in dict.fromkeys(cohorts.values())})
    table = {}
    for group, members in groups.items():
        table[group] = {}
        for method in methods:
            cases = [(q['metrics_by_k']['10'][method]['retrieved_ids'], q['gold_ids']) for q in members]
            table[group][method] = {**evaluation.summarize_results(cases, 10),
                                    'full_gold': sum(set(g) <= set(r) for r, g in cases)}
    result = {'status': 'completed', 'knowledge_base': reports[0]['knowledge_base'],
              'metrics': table, 'questions': rows,
              'skipped_no_gold': [q['id'] for q in questions if not q.get('gold_evidence')],
              'api_call_count': 0,
              'input_sha256': {name: digest for report in reports for name, digest in report['input_sha256'].items()},
              'elapsed_including_auxiliary_wait_seconds': round(time.perf_counter() - started, 3),
              'sum_shard_processing_seconds': sum(report['elapsed_seconds'] for report in reports),
              'timing_limit': 'Shared inference cache and models; not per-mode service latency.'}
    save(OUT / 'comparison.json', result)
    print('Complete all 42 questions; API calls in evaluation: 0', flush=True)
    for method, score in table['all'].items():
        if method.startswith('Pipeline '):
            print(method, json.dumps(score), flush=True)


if __name__ == '__main__':
    main()
