"""One frozen 12-question full-pipeline run; no retries or production changes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlsplit
from unittest.mock import patch


def save(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, required=True)
    parser.add_argument('--questions', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.project_dir.resolve(), args.output_dir.resolve()
    protocol = json.loads((out / 'frozen_protocol.json').read_text())
    assert sha(args.questions) == protocol['frozen_files']['questions_sha256']
    assert sha(Path(__file__)) == protocol['frozen_files']['driver_sha256']
    assert sha(args.questions.parent / 'holdout_v1_review_protocol.md') == protocol['frozen_files']['rubric_sha256']
    baseline = json.loads((out / 'baseline_hashes.json').read_text())
    assert all(sha(root / name) == digest for name, digest in baseline.items())
    questions = json.loads(args.questions.read_text())
    qids = [q['id'] for q in questions]
    ids_by_query = {q['question']: q['id'] for q in questions}
    calls_path = out / 'actual_chat_calls.json'
    calls = json.loads(calls_path.read_text()) if calls_path.exists() else []
    pending = [qid for qid in qids if not (out / f'{qid}.json').exists()]
    if not pending:
        print('All question records exist; no model or API work repeated.', flush=True)
        return
    sys.path.insert(0, str(root))
    import src.api_llm as api
    settings = api.load_settings()
    public_settings = {k: settings.get(k) for k in ('base_url', 'model', 'chat_options')}
    assert public_settings == protocol['api_public_settings'], 'API options changed after freeze.'
    endpoint = urlsplit(settings['base_url'])
    with socket.create_connection((endpoint.hostname, endpoint.port or 80), timeout=3):
        pass
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    import evaluation.run_answer_evaluation as evaluation
    assert (pipeline.RETRIEVAL_TOP_K, pipeline.RRF_TOP_K, pipeline.RERANK_TOP_K,
            pipeline.RRF_K, pipeline.SUB_QUERY_EVIDENCE_K) == (120, 120, 10, 60, 3)
    assert pipeline.USE_EVIDENCE_COMPLETION and not pipeline.USE_MULTI_QUERY and not pipeline.USE_HYDE
    original_chat = api.chat_completion
    original_request = api._request
    original_main = pipeline.main
    original_rank = pipeline.rank_evidence
    current = {}
    traces_path = out / 'retrieval_stage_traces.json'
    traces = json.loads(traces_path.read_text()) if traces_path.exists() else {}

    def observed_request(path, payload=None):
        if path == '/chat/completions':
            assert sum(c.get('http_posts', 0) for c in calls) < 36, '36-request limit reached.'
            calls[-1]['http_posts'] = calls[-1].get('http_posts', 0) + 1
            save(calls_path, calls)
        return original_request(path, payload)

    def counted_chat(prompt, *call_args, **kwargs):
        signature = hashlib.sha256(json.dumps([prompt, call_args, kwargs, public_settings],
                                            sort_keys=True).encode()).hexdigest()
        prior = next((c for c in calls if c['signature'] == signature), None)
        if prior:
            if prior['status'] == 'completed':
                current['cached_responses'] = current.get('cached_responses', 0) + 1
                return prior['response']
            raise RuntimeError('An identical request was previously attempted but not completed; no automatic retry.')
        if sum(c.get('http_posts', 0) for c in calls) >= 36:
            raise RuntimeError('Holdout API budget exhausted; no retry.')
        call = {'number': len(calls) + 1, 'question_id': current['question_id'],
                'signature': signature, 'prompt': prompt, 'status': 'running',
                'started_at_utc': datetime.now(timezone.utc).isoformat(), 'http_posts': 0}
        calls.append(call)
        save(calls_path, calls)
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
            save(calls_path, calls)
            print(f"{current['question_id']} chat {call['number']}: {call['status']} ({call['elapsed_seconds']}s)",
                  file=sys.__stdout__, flush=True)

    def observed_main(query, **kwargs):
        current.clear()
        current['question_id'] = ids_by_query[query]
        result = original_main(query, **kwargs)
        result['holdout_cached_chat_responses'] = current.get('cached_responses', 0)
        return result

    def observed_rank(query, candidates, sub_queries, reranker, top_k):
        result = original_rank(query, candidates, sub_queries, reranker, top_k)
        traces[current['question_id']] = {
            'candidate_ids_before_global_rerank': [c['chunk_id'] for c in candidates],
            'global_ranking_ids_before_completion': [c['chunk_id'] for c in result[0]],
            'sub_query_evidence': result[1],
            'capture_scope': 'Read-only observation of actual initial rank_evidence inputs/outputs; no candidate changes.'}
        save(traces_path, traces)
        return result

    print('Loading existing offline CPU models once; 12 fresh decompositions/answers, max 36 actual chat POSTs.', flush=True)
    embedding = pipeline.load_embedding_model()
    reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device='cpu')
    argv = ['run_answer_evaluation', '--questions', str(args.questions),
            '--question-id', *pending, '--kb-version', 'all-papers-8-20261020', '--output-dir', str(out)]
    started = time.perf_counter()
    with patch.object(pipeline, 'load_embedding_model', return_value=embedding), \
            patch.object(pipeline, 'CrossEncoder', return_value=reranker), \
            patch.object(pipeline, 'main', side_effect=observed_main), \
            patch.object(pipeline, 'rank_evidence', side_effect=observed_rank), \
            patch.object(api, '_request', side_effect=observed_request), \
            patch.object(api, 'chat_completion', side_effect=counted_chat), \
            patch.object(sys, 'argv', argv):
        try:
            evaluation.main()
        except SystemExit as exc:
            if exc.code not in (0, 1):
                raise
    records = {qid: json.loads((out / f'{qid}.json').read_text()) for qid in qids}
    summary = {'status': 'completed' if all(r['status'] == 'completed' for r in records.values()) else 'completed_with_failures',
               'question_count': len(records),
               'pipeline_completed': sum(r['status'] == 'completed' for r in records.values()),
               'api_calls': sum(c.get('http_posts', 0) for c in calls),
               'failed_api_calls': sum(c['status'] != 'completed' for c in calls),
               'automatic_retries': 0,
               'usage': {key: sum((c.get('response', {}).get('usage') or {}).get(key, 0) for c in calls)
                         for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
               'citation_repairs': sum(r.get('citation_validation', {}).get('repair_attempted', False)
                                       for r in records.values()),
               'elapsed_seconds_shared_models': round(time.perf_counter() - started, 3),
               'completed_at_utc': datetime.now(timezone.utc).isoformat()}
    save(out / 'run_summary.json', summary)
    assert all(sha(root / name) == digest for name, digest in baseline.items())
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
