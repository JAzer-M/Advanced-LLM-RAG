"""用用户已保存的分解结果测本地初检；不请求模型，不运行Agent。"""
from contextlib import ExitStack, redirect_stdout
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
import main as pipeline
from src import api_llm, reranker

HERE = Path(__file__).resolve().parent
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'after'
OLD = ROOT / 'logs/ui_prototype/20261023T030707Z_b3630fc4/pipeline'
calls = json.loads((OLD / 'actual_chat_calls.json').read_text())
response = calls[0]['response']
query = json.loads((OLD / 'result.json').read_text())['query']
measurements = []


def timed(name, function):
    def run(*args, **kwargs):
        started = time.perf_counter()
        result = function(*args, **kwargs)
        row = {'stage': name, 'seconds': round(time.perf_counter() - started, 3)}
        if name == 'rerank':
            row.update(query=args[0], pairs=len(args[1]))
        measurements.append(row)
        return result
    return run


started = time.perf_counter()
with ExitStack() as stack, (HERE / f'local_profile_{LABEL}_console.log').open('w') as log, redirect_stdout(log):
    stack.enter_context(patch.object(api_llm, 'chat_completion', side_effect=AssertionError('No model calls.')))
    stack.enter_context(patch.object(pipeline, '_answer_with_agent', side_effect=lambda initial, *a, **k: initial))
    for name in ['load_embedding_model', 'CrossEncoder', 'build_bm25_index', 'supplement_evidence']:
        stack.enter_context(patch.object(pipeline, name, timed(name, getattr(pipeline, name))))
    stack.enter_context(patch.object(reranker, 'rerank_results', timed('rerank', reranker.rerank_results)))
    result = pipeline._run_pipeline(query, kb_version='all-papers-8-20261020',
                                    agent_output=HERE / 'unused', agent_call=lambda prompt, phase: response)
summary = {'seconds': round(time.perf_counter() - started, 3), 'measurements': measurements,
           'selected_ids': result['selected_ids'], 'new_model_calls': 0, 'arxiv_gets': 0}
(HERE / f'local_profile_{LABEL}.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
