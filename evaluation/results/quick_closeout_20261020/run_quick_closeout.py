"""Five real answers with fixed budgets; cached decomposition where available."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlsplit
from unittest.mock import patch


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.project_dir, args.output_dir
    if out.exists() and any(out.iterdir()):
        parser.error('Use a new output directory; completed API calls must not be repeated.')
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root))
    import src.api_llm as api
    settings = api.load_settings()
    endpoint = urlsplit(settings['base_url'])
    with socket.create_connection((endpoint.hostname, endpoint.port or 80), timeout=3):
        pass
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    import evaluation.run_answer_evaluation as evaluation
    assert (pipeline.RETRIEVAL_TOP_K, pipeline.RRF_TOP_K, pipeline.RERANK_TOP_K) == (120, 120, 10)
    assert pipeline.USE_EVIDENCE_COMPLETION and not pipeline.USE_MULTI_QUERY and not pipeline.USE_HYDE
    qids = ['q2', 'p3', 'n07', 'a12', 'n11']
    questions = {q['id']: q for q in json.loads((root / 'evaluation/all_papers_questions_en.json').read_text())}
    auxiliary = json.loads((root / 'evaluation/results/all_papers_20261020/auxiliary.json').read_text())
    cached = {questions[qid]['question']: auxiliary[qid]['decomposition']
              for qid in qids if qid in auxiliary}
    original_decompose = pipeline.decompose_query
    original_chat = api.chat_completion
    calls = []

    def counted_chat(prompt, *call_args, **kwargs):
        if len(calls) >= 11:
            raise RuntimeError('Quick closeout API budget exhausted; no retry.')
        call = {'status': 'running'}
        calls.append(call)
        started = time.perf_counter()
        try:
            response = original_chat(prompt, *call_args, **kwargs)
            call.update(status='completed', response=response)
            return response
        except Exception as exc:
            call.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            if isinstance(exc, api.IncompleteResponseError):
                call['response'] = exc.response
            raise
        finally:
            call['elapsed_seconds'] = round(time.perf_counter() - started, 3)
            save(out / 'actual_chat_calls.json', calls)

    def decompose(query):
        return cached[query] if query in cached else original_decompose(query)

    protocol = {'question_ids': qids, 'kb_version': 'all-papers-8-20261020',
                'candidate_k': 120, 'final_k': 10, 'completion_rounds': 2,
                'rewrite': False, 'hyde': False, 'real_final_answers': True,
                'decomposition_origin': {qid: 'replayed saved API output' if qid in auxiliary
                                         else 'fresh API' for qid in qids},
                'max_chat_calls': 11, 'automatic_retries': 0,
                'shared_models': True, 'latency_scope': 'Validation run with shared CPU models; not P95',
                'semantic_review': 'Assistant checks actual claims against selected evidence; not blind evaluation',
                'defect_policy': 'Record and retain defects; do not change production retrieval or generation.'}
    save(out / 'protocol.json', protocol)
    print('Loading cached CPU models once; five fresh retrieval/answer runs.', flush=True)
    embedding = pipeline.load_embedding_model()
    reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device='cpu')
    argv = ['run_answer_evaluation', '--questions', str(root / 'evaluation/all_papers_questions_en.json'),
            '--question-id', *qids, '--kb-version', 'all-papers-8-20261020', '--output-dir', str(out)]
    started = time.perf_counter()
    with patch.object(pipeline, 'load_embedding_model', return_value=embedding), \
            patch.object(pipeline, 'CrossEncoder', return_value=reranker), \
            patch.object(pipeline, 'decompose_query', side_effect=decompose), \
            patch.object(api, 'chat_completion', side_effect=counted_chat), \
            patch.object(sys, 'argv', argv):
        try:
            evaluation.main()
        except SystemExit as exc:
            if exc.code not in (0, 1):
                raise
    records = {qid: json.loads((out / f'{qid}.json').read_text()) for qid in qids}
    summary = {'status': 'completed', 'question_count': len(records),
               'pipeline_completed': sum(r['status'] == 'completed' for r in records.values()),
               'api_calls': len(calls), 'failed_api_calls': sum(c['status'] != 'completed' for c in calls),
               'usage': {key: sum((c.get('response', {}).get('usage') or {}).get(key, 0) for c in calls)
                         for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
               'citation_repairs': sum(r.get('citation_validation', {}).get('repair_attempted', False)
                                       for r in records.values()),
               'elapsed_seconds_shared_models': round(time.perf_counter() - started, 3)}
    save(out / 'run_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
