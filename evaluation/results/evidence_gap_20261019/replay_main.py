"""Real main retrieval, fixed decomposition and stubbed generation: zero API calls."""
from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    import src.api_llm as api

    def forbidden(*args, **kwargs):
        raise AssertionError('API forbidden: this run validates main retrieval, not generation')
    api.chat_completion = forbidden
    pipeline.generate_final_answer = lambda prompt: 'Generation is stubbed for this integration check [1].'
    embedding = pipeline.load_embedding_model()
    reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device='cpu')
    pipeline.load_embedding_model = lambda: embedding
    pipeline.CrossEncoder = lambda *args, **kwargs: reranker
    cache = json.loads((ROOT / 'evaluation/results/independent_validation_20261019/auxiliary.json').read_text())
    report = json.loads((OUT / 'new/results.json').read_text())
    records = []
    for qid in ('n06', 'n07'):
        expected = next(q for q in report['questions'] if q['id'] == qid)
        query = cache[qid]['query']
        pipeline.decompose_query = lambda query: cache[qid]['decomposition']
        with (OUT / f'main_{qid}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
            result = pipeline.main(query, kb_version='arxiv-pilot-5-20261019', complete_evidence=True)
        assert result['selected_ids'] == expected['metrics_by_k']['10']['Evidence Completion (one round)']['retrieved_ids']
        trace = result['retrieval_diagnostics']['evidence_completion']
        assert trace['rounds'] == (1 if qid == 'n07' else 0)
        assert result['knowledge_base']['version'] == 'arxiv-pilot-5-20261019'
        records.append({'id': qid, 'selected_ids': result['selected_ids'],
                        'retrieval_diagnostics': result['retrieval_diagnostics'],
                        'generation': 'stubbed; no real answer or semantic acceptance',
                        'context': result['context'], 'prompt': result['prompt']})
        print(qid, 'actual main retrieval matches evaluation; rounds', trace['rounds'], flush=True)
    (OUT / 'main_replay.json').write_text(json.dumps(
        {'status': 'passed', 'api_calls': 0, 'generation': 'stubbed', 'cases': records},
        ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
