"""Run the existing evaluation main with audit-only observers; no retrieval overrides."""

import hashlib
import json
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import torch

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

import evaluation.run_evaluation as evaluation
import src.api_llm as api

QUESTIONS = ROOT / 'evaluation/arxiv_pilot_questions.json'
VERSION = 'arxiv-pilot-5-20261019'
if (OUTPUT / 'results.json').exists():
    raise SystemExit('Existing results preserved; use a new output directory for another run.')

_, chunks, knowledge_base = evaluation.load_knowledge_base(ROOT / 'data/processed', VERSION)
questions = json.loads(QUESTIONS.read_text(encoding='utf-8'))
gold_mapping = []
for question in questions:
    if not question.get('gold_evidence'):
        gold_mapping.append({'id': question['id'], 'status': 'no_gold; skipped'})
        continue
    ids, unmatched = evaluation.get_gold_chunk_ids(question, chunks)
    if unmatched or not ids:
        raise SystemExit(f"Incomplete Gold mapping: {question['id']}; no API calls made.")
    gold_mapping.append({'id': question['id'], 'gold_ids': sorted(ids), 'status': 'matched'})

paths = [ROOT / name for name in json.loads((OUTPUT / 'baseline_hashes.json').read_text())]
code_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in paths}
result = {
    'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
    'entry_point': 'evaluation.run_evaluation.main',
    'questions': str(QUESTIONS.relative_to(ROOT)), 'knowledge_base': knowledge_base,
    'configuration': {'final_k': evaluation.FINAL_K, 'candidate_k': evaluation.CANDIDATE_K,
                      'rrf_top_k': evaluation.RRF_TOP_K, 'rrf_k': evaluation.RRF_K,
                      'rewrite': evaluation.ENABLE_REWRITING,
                      'decomposition': evaluation.ENABLE_DECOMPOSITION,
                      'reranker': evaluation.RERANKER_NAME,
                      'reranker_device': evaluation.RERANKER_DEVICE,
                      'torch_threads': torch.get_num_threads(),
                      'strategy': 'original evaluation methods; original-query global rerank; no main.py local evidence protection'},
    'gold_mapping': gold_mapping, 'file_sha256': code_hashes,
    'per_question': [], 'metrics': {}, 'api_calls': [],
}


def save():
    (OUTPUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                       encoding='utf-8')


current = {}
original_gold = evaluation.get_gold_chunk_ids
original_record = evaluation.record_results
original_overall = evaluation.print_overall_metrics
original_chat = api.chat_completion
original_decompose = evaluation.decompose_query
original_rewrite = evaluation.rewrite_query


def observed_gold(question, all_chunks):
    current.clear()
    current.update(id=question['id'], question=question['question'])
    print(question['id'], 'retrieval evaluation started', file=sys.__stdout__, flush=True)
    return original_gold(question, all_chunks)


def observed_chat(prompt, *args, **kwargs):
    call = {'question_id': current['id'], 'prompt': prompt}
    result['api_calls'].append(call)
    started = time.perf_counter()
    try:
        response = original_chat(prompt, *args, **kwargs)
        call['response'] = response
        return response
    except Exception as exc:
        call['error'] = f'{type(exc).__name__}: {exc}'
        if isinstance(exc, api.IncompleteResponseError):
            call['response'] = exc.response
        raise
    finally:
        call['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        save()


def observed_decompose(query):
    decomposition = original_decompose(query)
    current['decomposition'] = decomposition
    return decomposition


def observed_rewrite(query):
    rewritten = original_rewrite(query)
    current['rewritten_query'] = rewritten
    return rewritten


def observed_record(methods, gold_ids, test_cases):
    original_record(methods, gold_ids, test_cases)
    result['per_question'].append({**current, 'gold_ids': sorted(gold_ids),
                                  'methods': {name: {'retrieved_ids': ids,
                                                     **evaluation.evaluate_retrieval(ids, gold_ids)}
                                              for name, ids in methods.items()}})
    save()
    print(current['id'], 'completed', file=sys.__stdout__, flush=True)


def observed_overall(name, cases):
    original_overall(name, cases)
    if not cases:
        result['metrics'][name] = {'questions': 0}
        return
    result['metrics'][name] = {
        'questions': len(cases),
        'precision_at_5': sum(evaluation.precision_at_k(r, g, evaluation.FINAL_K)
                              for r, g in cases) / len(cases),
        'recall_at_5': sum(evaluation.recall_at_k(r, g, evaluation.FINAL_K)
                           for r, g in cases) / len(cases),
        'map_at_5': evaluation.mean_average_precision_at_k(cases, evaluation.FINAL_K),
        'mrr_at_5': evaluation.mean_reciprocal_rank_at_k(cases, evaluation.FINAL_K),
    }
    save()


evaluation.get_gold_chunk_ids = observed_gold
evaluation.record_results = observed_record
evaluation.print_overall_metrics = observed_overall
evaluation.decompose_query = observed_decompose
evaluation.rewrite_query = observed_rewrite
api.chat_completion = observed_chat
sys.argv = ['evaluation.run_evaluation', '--questions', str(QUESTIONS), '--kb-version', VERSION]
save()
started = time.perf_counter()
try:
    with (OUTPUT / 'run_evaluation.log').open('w', encoding='utf-8') as log:
        with redirect_stdout(log), redirect_stderr(log):
            evaluation.main()
    result['status'] = 'completed'
except Exception as exc:
    result.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    raise
finally:
    api.chat_completion = original_chat
    result['elapsed_seconds'] = round(time.perf_counter() - started, 3)
    result['api_call_count'] = len(result['api_calls'])
    result['usage'] = {key: sum((call.get('response', {}).get('usage') or {}).get(key, 0)
                               for call in result['api_calls'])
                       for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    result['inputs_unchanged'] = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
                                     for name, sha in code_hashes.items())
    save()

print(json.dumps({'status': result['status'], 'metrics': result['metrics'],
                  'api_calls': result['api_call_count'], 'usage': result['usage'],
                  'elapsed_seconds': result['elapsed_seconds']}, ensure_ascii=False, indent=2))
