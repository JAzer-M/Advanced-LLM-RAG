"""Offline paired retrieval audit: captured API response, real models, no generation."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent

import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

import main as pipeline
import src.api_llm as api
from evaluation.run_arxiv_pilot import normalized
from src.embedding import load_embedding_model
from src.knowledge_base import load_knowledge_base
from src.query_decomposer import decompose_query


def main():
    captured = json.loads((OUT / 'captured_p6_decomposition.json').read_text(encoding='utf-8'))
    old = {'__name__': 'captured_before_decomposer'}
    exec(compile((OUT / 'before_query_decomposer.py').read_text(),
                 str(OUT / 'before_query_decomposer.py'), 'exec'), old)
    old_reranker = {'__name__': 'captured_before_reranker'}
    exec(compile((OUT / 'before_reranker.py').read_text(),
                 str(OUT / 'before_reranker.py'), 'exec'), old_reranker)
    current_rerank = pipeline.rerank_results
    model = load_embedding_model()
    reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device=pipeline.RERANKER_DEVICE)
    _, chunks, kb = load_knowledge_base(ROOT / 'data/processed', 'arxiv-pilot-5-20261019')
    question = next(q for q in json.loads((ROOT / 'evaluation/arxiv_pilot_questions.json')
                                         .read_text(encoding='utf-8')) if q['id'] == 'p6')
    summary = {'provenance': __doc__, 'api_calls': 0, 'generation_run': False,
               'knowledge_base': kb, 'cases': {}}
    for label, decompose in [('before', old['decompose_query']), ('after', decompose_query)]:
        started = time.perf_counter()
        with (OUT / f'replay_{label}.log').open('w', encoding='utf-8') as log, \
                redirect_stdout(log), redirect_stderr(log), \
                patch('llm.generate_answer', return_value=captured['response']) as replay, \
                patch.object(api, 'chat_completion', side_effect=AssertionError('API forbidden in offline replay')), \
                patch.object(pipeline, 'decompose_query', side_effect=decompose), \
                patch.object(pipeline, 'rerank_results', side_effect=(
                    old_reranker['rerank_results'] if label == 'before' else current_rerank)), \
                patch.object(pipeline, 'load_embedding_model', return_value=model), \
                patch.object(pipeline, 'CrossEncoder', return_value=reranker), \
                patch.object(pipeline, 'generate_final_answer', return_value='离线回放，仅核对检索证据 [1]。'):
            result = pipeline.main(captured['query'], kb_version=kb['version'])
            replay.assert_called_once()
        selected = result['ledger']['citation_registry'][:len(result['selected_ids'])]
        gold = []
        for item in question['gold_evidence']:
            matches = {c['chunk_id'] for c in chunks
                       if c['source'] == item['source'] and c['page'] == item['page']
                       and normalized(item['quote']) in normalized(c['text'])}
            gold.append({**item, 'matching_ids': sorted(matches),
                         'ranks': [i for i, c in enumerate(selected, 1) if c['chunk_id'] in matches]})
        audited = {key: result[key] for key in ('query', 'decomposition', 'knowledge_base',
                                               'selected_ids', 'context', 'ledger', 'retrieval_diagnostics')}
        audited.update(run_provenance=__doc__, api_calls=0, generation_run=False,
                       gold=gold, top10=selected,
                       elapsed_seconds=round(time.perf_counter() - started, 2))
        (OUT / f'replay_{label}.json').write_text(
            json.dumps(audited, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        summary['cases'][label] = {'sub_queries': result['decomposition']['sub_queries'],
                                   'selected_ids': result['selected_ids'],
                                   'gold_ranks': [g['ranks'] for g in gold],
                                   'all_gold_top10': all(g['ranks'] for g in gold),
                                   'elapsed_seconds': audited['elapsed_seconds']}
        print(label, 'subqueries', len(result['decomposition']['sub_queries']),
              'gold ranks', [g['ranks'] for g in gold], flush=True)
    summary['source_code_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                     for name in ('src/query_decomposer.py', 'main.py',
                                                  'evaluation/arxiv_pilot_questions.json')}
    (OUT / 'replay_comparison.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
