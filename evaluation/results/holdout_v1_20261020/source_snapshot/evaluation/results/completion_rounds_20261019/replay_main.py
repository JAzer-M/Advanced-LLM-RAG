"""Three-pass main retrieval integration; generation stubbed and API prohibited."""
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
        raise AssertionError('API forbidden during retrieval integration')
    api.chat_completion = forbidden
    cache = json.loads((ROOT / 'evaluation/results/independent_validation_20261019/auxiliary.json').read_text())
    qid = 'n07'
    pipeline.decompose_query = lambda query: cache[qid]['decomposition']
    pipeline.generate_final_answer = lambda prompt: 'Retrieval integration uses stubbed generation [1].'
    report = json.loads((OUT / 'new/results.json').read_text())
    expected = next(q for q in report['questions'] if q['id'] == qid)
    with (OUT / 'main_n07.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
        result = pipeline.main(cache[qid]['query'], kb_version='arxiv-pilot-5-20261019',
                               complete_evidence=True, completion_rounds=3)
    assert result['selected_ids'] == expected['metrics_by_k']['10']['Evidence Completion (up to 3 rounds)']['retrieved_ids']
    trace = result['retrieval_diagnostics']['evidence_completion']
    assert trace['max_rounds'] == 3 and trace['completed_passes'] <= 3
    saved = {'status': 'passed', 'api_calls': 0, 'generation': 'stubbed', 'id': qid,
             'selected_ids': result['selected_ids'], 'trace': trace, 'context': result['context']}
    (OUT / 'main_replay.json').write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
    print('Actual main n07 three-pass retrieval matches evaluation; generation stubbed.', flush=True)


if __name__ == '__main__':
    main()
