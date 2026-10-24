"""Real cached CPU models, frozen auxiliary queries, no answer or auxiliary API calls."""
from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
import evaluation.run_evaluation as evaluation
import main as pipeline
import src.api_llm as api

embedding = evaluation.load_embedding_model()
reranker = evaluation.CrossEncoder(evaluation.RERANKER_NAME, device='cpu')
configs = [
    ('final_english_60', 'evaluation/arxiv_pilot_questions_en.json', 'arxiv-pilot-5-20261019', 60, False),
    ('final_english_20', 'evaluation/arxiv_pilot_questions_en.json', 'arxiv-pilot-5-20261019', 20, False),
    ('validation_60', 'evaluation/arxiv_validation_questions_en.json', 'arxiv-pilot-5-20261019', 60, True),
    ('legacy_60', 'evaluation/questions.json', 'semantic-mac-20261019', 60, True),
]
summary = {'mode': __doc__, 'api_calls': 0, 'runs': {}}
with patch.object(evaluation, 'load_embedding_model', return_value=embedding), \
        patch.object(evaluation, 'CrossEncoder', return_value=reranker), \
        patch.object(api, 'chat_completion', side_effect=AssertionError('API forbidden in offline sweep')):
    for name,questions,version,budget,no_auxiliary in configs:
        sys.argv = ['evaluation.run_evaluation', '--questions', str(ROOT / questions),
                    '--kb-version', version, '--candidate-k', str(budget),
                    '--top-k', '5', '10', '20', '--output-dir', str(OUT / name)]
        sys.argv += ['--no-auxiliary'] if no_auxiliary else [
            '--auxiliary-cache', str(OUT / 'auxiliary_revised.json')]
        print(name, 'started', flush=True)
        with (OUT / f'{name}.log').open('w', encoding='utf-8') as log, \
                redirect_stdout(log), redirect_stderr(log):
            evaluation.main()
        result = json.loads((OUT / name / 'results.json').read_text())
        assert result['status'] == 'completed' and result['inputs_unchanged']
        assert result['api_call_count'] == 0
        summary['runs'][name] = {'metrics': result['metrics'], 'elapsed_seconds': result['elapsed_seconds']}
        (OUT / 'offline_sweep.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(name, 'completed', result['elapsed_seconds'], 'seconds', flush=True)

    cache = json.loads((OUT / 'auxiliary_revised.json').read_text())
    q = cache['p6']
    with (OUT / 'main_p6_replay.log').open('w', encoding='utf-8') as log, \
            redirect_stdout(log), redirect_stderr(log), \
            patch.object(pipeline, 'load_embedding_model', return_value=embedding), \
            patch.object(pipeline, 'CrossEncoder', return_value=reranker), \
            patch.object(pipeline, 'decompose_query', return_value=q['decomposition']), \
            patch.object(pipeline, 'generate_final_answer', return_value='Offline retrieval audit [1].'):
        result = pipeline.main(q['query'], kb_version='arxiv-pilot-5-20261019')
    saved = json.loads((OUT / 'final_english_60/results.json').read_text())
    expected = next(q for q in saved['questions'] if q['id']=='p6')['metrics_by_k']['10'][
        'Decomposition + Hybrid + Reranker']['retrieved_ids']
    assert result['selected_ids'] == expected
    audit = {key: result[key] for key in ('query', 'decomposition', 'selected_ids', 'retrieval_diagnostics')}
    audit.update(mode='Real main retrieval with frozen decomposition; generation explicitly skipped.',
                 api_calls=0, matches_evaluation_top10=True)
    (OUT / 'main_p6_replay.json').write_text(json.dumps(audit, indent=2) + '\n')
    print('Real main p6 selected IDs match evaluation:', result['selected_ids'], flush=True)
