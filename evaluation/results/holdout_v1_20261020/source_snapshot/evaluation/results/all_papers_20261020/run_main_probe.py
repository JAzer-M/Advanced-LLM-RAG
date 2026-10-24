"""Eight real main.py answers with frozen API transformations and uncached CPU reranking."""
from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    assert json.loads((OUT / 'comparison.json').read_text())['status'] == 'completed'
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    import src.api_llm as api
    embedding = pipeline.load_embedding_model()
    reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device='cpu')
    questions = {q['id']: q for q in json.loads((ROOT / 'evaluation/all_papers_questions_en.json').read_text())}
    auxiliary = json.loads((OUT / 'auxiliary.json').read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    root = OUT / 'answer_probe'
    root.mkdir(exist_ok=True)
    calls = json.loads((root / 'api_calls.json').read_text()) if (root / 'api_calls.json').exists() else []
    original_chat, phase = api.chat_completion, {}

    def audited_chat(prompt, *args, **kwargs):
        assert len(json.loads((OUT / 'api_calls.json').read_text())) + len(calls) < protocol['total_api_call_cap']
        call = {**phase, 'prompt': prompt, 'status': 'running'}
        calls.append(call)
        save(root / 'api_calls.json', calls)
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
            save(root / 'api_calls.json', calls)

    api.chat_completion = audited_chat
    records = []
    for qid in protocol['answer_probe']['questions']:
        q, aux = questions[qid], auxiliary[qid]
        expected = json.loads((OUT / 'retrieval' / qid / 'results.json').read_text())['questions'][0]
        for mode, cap in [('base', 0), ('both', 2)]:
            path = root / f'{qid}_{mode}_{cap}.json'
            if path.exists():
                records.append(json.loads(path.read_text()))
                continue
            phase.update(question_id=qid, mode=mode, completion_cap=cap)
            started = time.perf_counter()
            with patch.object(pipeline, 'load_embedding_model', return_value=embedding), \
                    patch.object(pipeline, 'CrossEncoder', return_value=reranker), \
                    patch.object(pipeline, 'decompose_query', return_value=aux['decomposition']), \
                    patch.object(pipeline, 'rewrite_query', return_value=aux['rewritten_query']), \
                    patch.object(pipeline, 'generate_hypothetical_document', return_value=aux['hypothetical_document']), \
                    patch.multiple(pipeline, USE_MULTI_QUERY=mode == 'both', USE_HYDE=mode == 'both'), \
                    (root / f'{qid}_{mode}_{cap}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
                result = pipeline.main(q['question'], kb_version='all-papers-8-20261020',
                                       complete_evidence=bool(cap), completion_rounds=max(1, cap))
            result.update(id=qid, mode=mode, completion_cap=cap,
                          elapsed_with_shared_models_seconds=round(time.perf_counter() - started, 3),
                          auxiliary_calls_replayed=True)
            result['evaluation_ids_match'] = result['selected_ids'] == expected['metrics_by_k']['10'][f'Pipeline {mode} ({cap} rounds)']['retrieved_ids']
            save(path, result)
            assert result['evaluation_ids_match'], f'Real main and evaluation disagree: {qid}/{mode}'
            assert aux['hypothetical_document'] not in result['context']
            records.append(result)
            print('Saved real main answer', qid, mode, cap, 'seconds', result['elapsed_with_shared_models_seconds'], flush=True)
    usage = {key: sum((c.get('response', {}).get('usage') or {}).get(key, 0) for c in calls)
             for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    save(root / 'summary.json', {'status': 'completed', 'real_answers': len(records), 'api_calls': len(calls),
                               'usage': usage, 'all_main_ids_match_evaluation': all(r['evaluation_ids_match'] for r in records),
                               'all_citation_structures_passed': all(r['citation_validation']['final_check']['structure_passed'] for r in records),
                               'semantic_review': 'Manual review required; structure is not semantic correctness.'})


if __name__ == '__main__':
    main()
