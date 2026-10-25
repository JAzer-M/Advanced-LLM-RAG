"""六道已知缺陷题的离线检索诊断，独立Top10/20，不生成答案或调参。"""
from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evaluation/results/qasper_improvement_20261025'
PREVIOUS = ROOT / 'evaluation/results/qasper_20261024'


def load(path):
    return json.loads(path.read_text())


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def main(version):
    source = OUT / 'baseline_source' if version == 'baseline' else ROOT
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(source))
    from src import runtime_paths
    runtime_paths.data_root = lambda: ROOT
    import main as pipeline
    from src import api_llm
    from evaluation import qasper_eval as old
    from evaluation.metrics import (precision_at_k, normalized_precision_at_k, recall_at_k,
                                    average_precision_at_k, reciprocal_rank_at_k)
    assert Path(pipeline.__file__).resolve().parent == source
    api_llm.chat_completion = lambda *a, **k: (_ for _ in ()).throw(AssertionError('Offline: no model API calls allowed.'))
    pipeline.generate_final_answer = lambda *a, **k: 'Offline diagnostic [1].'
    old.cached_models(pipeline)
    sample = load(PREVIOUS / 'frozen_sample.json')
    data = load(ROOT / 'evaluation/qasper_cache/qasper-test-v0.3.json')
    chunks = load(ROOT / 'data/processed/versions/qasper-test50-20261024/chunks.json')
    selected_prefixes = ('fea9b4d136', 'b57ad10468', 'e8c3f59313', '256dfa501a', 'c626637ed1', 'fee4984577')
    rows, availability = [], []
    for q in sample['questions']:
        paragraphs = [p for s in data[q['paper_id']]['full_text'] for p in s['paragraphs'] if p.strip()]
        gold = {p for r in q['references'] for p in r['evidence']}
        if not gold:
            continue
        normalized_gold = {normalized(p) for p in gold}
        matched = {c['chunk_id']: old.align(c['text'], paragraphs) for c in chunks
                   if Path(c['source']).stem == q['paper_id']}
        gold_ids = {cid for cid, ps in matched.items() if any(normalized(p) in normalized_gold for p in ps)}
        availability.append({'question_id': q['question_id'],
            'canonical_raw_available': any(set(ps) & gold for ps in matched.values()),
            'canonical_normalized_available': bool(gold_ids), 'gold_chunk_ids': sorted(gold_ids)})
        if not q['question_id'].startswith(selected_prefixes):
            continue
        original = load(PREVIOUS / 'paper_bound_deepseek_v41_flash/runs' / q['question_id'] / 'rag.json')
        pipeline.decompose_query = lambda *a, **k: original['decomposition']
        query = f'For the paper "{q["paper_title"]}" (arXiv: {q["paper_id"]}), answer this question: {q["question"]}'
        for k in (10, 20):
            pipeline.RERANK_TOP_K = k
            with (OUT / 'diagnostics' / f'{version}_{q["question_id"]}_{k}.log').open('w') as log, \
                    redirect_stdout(log), redirect_stderr(log):
                result = pipeline.main(query, kb_version='qasper-test50-20261024', complete_evidence=True,
                                       completion_rounds=2)
            if result['status'] == 'failed':
                raise RuntimeError(result.get('error'))
            ids = result['selected_ids']
            diagnostic = result['retrieval_diagnostics']
            rows.append({'version': version, 'question_id': q['question_id'], 'k': k,
                'cached_original_decomposition': original['decomposition'], 'gold_ids': sorted(gold_ids),
                'selected_ids': ids, 'gold_hit': bool(set(ids) & gold_ids),
                'precision': precision_at_k(ids, gold_ids, k),
                'normalized_precision': normalized_precision_at_k(ids, gold_ids, k),
                'recall': recall_at_k(ids, gold_ids, k), 'ap': average_precision_at_k(ids, gold_ids, k),
                'rr': reciprocal_rank_at_k(ids, gold_ids, k), 'retrieval_diagnostics': diagnostic,
                'generation_api_attempts': result['api_summary']['attempts']})
            print(version, q['question_id'][:10], k, 'gold_hit', rows[-1]['gold_hit'], flush=True)
    (OUT / 'diagnostics' / f'{version}.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    (OUT / 'diagnostics' / f'{version}_old_gold_availability.json').write_text(
        json.dumps(availability, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    (OUT / 'diagnostics').mkdir(parents=True, exist_ok=True)
    main(sys.argv[1])
