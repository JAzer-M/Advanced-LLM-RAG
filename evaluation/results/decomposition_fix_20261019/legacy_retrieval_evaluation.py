"""Old three-paper original-query retrieval regression, zero API calls."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent

import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

import main as pipeline
import src.api_llm as api
from evaluation import run_arxiv_pilot as evaluation
from src.embedding import load_embedding_model

old = {'__name__': 'captured_before_reranker'}
exec(compile((OUT / 'before_reranker.py').read_text(), str(OUT / 'before_reranker.py'), 'exec'), old)
current = evaluation.rerank_results
embedding = load_embedding_model()
reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device=pipeline.RERANKER_DEVICE)
cases = [('after', current)] if '--after-only' in sys.argv else [('before', old['rerank_results']), ('after', current)]
for label, rank in cases:
    output = OUT / 'legacy_retrieval' / label
    output.mkdir(parents=True, exist_ok=True)
    argv = ['legacy_retrieval', '--kb-version', 'semantic-mac-20261019',
            '--questions', str(ROOT / 'evaluation/questions.json'), '--output-dir', str(output)]
    with (output / 'run.log').open('w', encoding='utf-8') as log, \
            redirect_stdout(log), redirect_stderr(log), patch('sys.argv', argv), \
            patch.object(api, 'chat_completion', side_effect=AssertionError('API forbidden')), \
            patch.object(evaluation, 'load_embedding_model', return_value=embedding), \
            patch.object(evaluation, 'CrossEncoder', return_value=reranker), \
            patch.object(evaluation, 'rerank_results', side_effect=rank):
        evaluation.main()
    report_path = output / 'retrieval.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    source = OUT / 'before_reranker.py' if label == 'before' else ROOT / 'src/reranker.py'
    report['reranker_override'] = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    report['provenance'] = __doc__
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(label, [(q['id'], q['all_gold_in_top10']) for q in report['questions']], flush=True)
