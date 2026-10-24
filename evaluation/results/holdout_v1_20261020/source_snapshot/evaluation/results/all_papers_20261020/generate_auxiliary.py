"""Use current API-backed transformations once per question; save every actual call."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    import src.api_llm as api
    from src.query_decomposer import decompose_query
    from src.query_rewriter import rewrite_query
    from src.hyde import generate_hypothetical_document
    protocol = json.loads((OUT / 'protocol.json').read_text())
    questions = json.loads((ROOT / 'evaluation/all_papers_questions_en.json').read_text())
    cache = json.loads((OUT / 'auxiliary.json').read_text()) if (OUT / 'auxiliary.json').exists() else {}
    calls = json.loads((OUT / 'api_calls.json').read_text()) if (OUT / 'api_calls.json').exists() else []
    reused = {}
    for path in ['evaluation/results/retrieval_optimization_20261019/auxiliary_final.json',
                 'evaluation/results/independent_validation_20261019/auxiliary.json']:
        for qid, value in json.loads((ROOT / path).read_text()).items():
            reused[qid] = (value, path)
    original_chat = api.chat_completion
    phase = {}

    def audited_chat(prompt, *args, **kwargs):
        assert len(calls) < protocol['auxiliary_calls']['total_max'], 'Frozen auxiliary call cap reached.'
        call = {**phase, 'prompt': prompt, 'status': 'running'}
        calls.append(call)
        save('api_calls.json', calls)
        started = time.perf_counter()
        try:
            response = original_chat(prompt, *args, **kwargs)
            call.update(status='completed', response=response)
            return response
        except Exception as exc:
            call.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            if isinstance(exc, api.IncompleteResponseError):
                call['response'] = exc.response
            raise
        finally:
            call['elapsed_seconds'] = round(time.perf_counter() - started, 3)
            save('api_calls.json', calls)

    api.chat_completion = audited_chat
    tracked = [ROOT / 'evaluation/all_papers_questions_en.json', OUT / 'protocol.json',
               ROOT / 'llm.py', ROOT / 'src/query_decomposer.py', ROOT / 'src/query_rewriter.py',
               ROOT / 'src/hyde.py', ROOT / 'src/api_llm.py']
    save('auxiliary_input_hashes.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in tracked})
    for q in questions:
        if not q.get('gold_evidence'):
            continue
        qid, query = q['id'], q['question']
        entry = cache.setdefault(qid, {'query': query})
        assert entry['query'] == query
        if 'decomposition' not in entry:
            if qid in reused:
                saved, path = reused[qid]
                assert saved['query'] == query
                entry.update(decomposition=saved['decomposition'], decomposition_origin=path)
            else:
                phase.update(question_id=qid, stage='decomposition')
                entry['decomposition'] = decompose_query(query)
                entry['decomposition_origin'] = 'fresh API, current prompt'
            save('auxiliary.json', cache)
        for stage, key, function in [('rewrite', 'rewritten_query', rewrite_query),
                                     ('hyde', 'hypothetical_document', generate_hypothetical_document)]:
            if key in entry:
                continue
            phase.update(question_id=qid, stage=stage)
            value = function(query).strip()
            assert value, f'Empty {stage} for {qid}; no silent fallback.'
            entry[key] = value
            save('auxiliary.json', cache)
            print(qid, stage, 'saved', 'calls', len(calls), flush=True)
    assert len(cache) == 42
    usage = {key: sum((c.get('response', {}).get('usage') or {}).get(key, 0) for c in calls)
             for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    save('auxiliary_summary.json', {'status': 'completed', 'api_calls': len(calls), 'usage': usage,
                                   'reused_decomposition': 16, 'automatic_retries': 0})
    print('Completed auxiliary', len(calls), usage, flush=True)


if __name__ == '__main__':
    main()
