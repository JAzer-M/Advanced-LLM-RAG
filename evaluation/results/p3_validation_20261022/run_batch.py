# 冻结六题的真实main对照；只读id/问题，Gold与评分文件不进入生产输入。
# 同进程复用真实CPU资源；各路径独立分解/生成，实际请求合计硬限96，不重试/不覆盖。
from contextlib import ExitStack, redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def main():
    protocol = json.loads((OUT / 'frozen_protocol.json').read_text())
    for name, expected in protocol['input_and_source_hashes'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen source/input changed: ' + name)
    questions = json.loads((OUT / 'run_inputs.json').read_text())
    assert all(set(q) == {'id', 'question'} for q in questions)
    by_id = {q['id']: q['question'] for q in questions}
    folder = OUT / 'live'
    if folder.exists():
        raise ValueError('Preserve prior evaluation; never rerun or overwrite this live directory.')
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    from src import agent_tools, api_llm as api
    public = lambda: {k: api.load_settings().get(k) for k in ('base_url', 'model', 'chat_options')}
    assert public() == protocol['api_public_settings']
    folder.mkdir()
    print('Loading real cached CPU resources once...', flush=True)
    started = time.perf_counter()
    resources = agent_tools.load_search_resources()
    assert resources['knowledge_base']['version'] == protocol['knowledge_base_version']
    save(folder / 'resource_loading.json', {'seconds': time.perf_counter() - started,
         'knowledge_base': resources['knowledge_base'], 'included_in_path_latency': False})
    wire, results, current = [], [], {}
    original_http = api.urlopen

    def observed_http(request, *args, **kwargs):
        if len(wire) >= protocol['max_actual_model_requests']:
            raise RuntimeError('Frozen global request budget exhausted before HTTP; no retry.')
        assert public() == protocol['api_public_settings']
        entry = {'question_id': current['id'], 'arm': current['arm'], 'method': request.get_method(),
                 'url': request.full_url, 'status': 'running',
                 'started_at_utc': datetime.now(timezone.utc).isoformat()}
        wire.append(entry)
        save(folder / 'model_http.json', wire)
        try:
            response = original_http(request, *args, **kwargs)
            entry.update(status='completed', http_status=response.status)
            return response
        except Exception as exc:
            entry.update(status='failed', error=f'{type(exc).__name__}: {exc}',
                         http_status=getattr(exc, 'code', None))
            raise
        finally:
            save(folder / 'model_http.json', wire)

    with ExitStack() as stack:
        for owner, name, value in [
            (pipeline, 'load_knowledge_base', (resources['index'], resources['chunks'], resources['knowledge_base'])),
            (pipeline, 'load_embedding_model', resources['embedding_model']),
            (pipeline, 'build_bm25_index', resources['bm25']),
            (pipeline, 'CrossEncoder', resources['reranker_model'])]:
            stack.enter_context(patch.object(owner, name, return_value=value))
        stack.enter_context(patch.object(api, 'urlopen', side_effect=observed_http))
        for run in protocol['run_order']:
            qid, arm = run['id'], run['arm']
            current.update(id=qid, arm=arm)
            row = {'id': qid, 'arm': arm, 'mode': run['mode'], 'allow_network': run['allow_network']}
            if len(wire) >= protocol['max_actual_model_requests']:
                row.update(status='not_run_budget', actual_model_requests=0)
            else:
                parent = folder / qid
                parent.mkdir(exist_ok=True)
                case_dir = parent / arm
                before, started = len(wire), time.perf_counter()
                print('Running', qid, arm, flush=True)
                with (parent / (arm + '_console.txt')).open('w') as log, redirect_stdout(log), redirect_stderr(log):
                    try:
                        result = pipeline.main(by_id[qid], mode=run['mode'],
                                               allow_network=run['allow_network'], output_dir=case_dir)
                    except Exception as exc:
                        path = case_dir / 'result.json'
                        result = json.loads(path.read_text()) if path.exists() else {'status': 'failed'}
                        result['driver_error'] = f'{type(exc).__name__}: {exc}'
                row.update(status=result['status'], seconds=time.perf_counter() - started,
                    actual_model_requests=len(wire) - before, api_summary=result.get('api_summary'),
                    answer_strategy=result.get('answer_strategy'), network=result.get('network'),
                    agent=result.get('agent'), error=result.get('error', result.get('driver_error')))
            results.append(row)
            save(folder / 'summary.json', {'planned_runs': len(protocol['run_order']), 'runs': results,
                 'actual_model_requests': len(wire), 'automatic_retries': 0,
                 'semantic_correctness': 'requires_manual_review'})
            print(qid, arm, row['status'], 'requests', row['actual_model_requests'], flush=True)
    print('Evaluation terminal; keep failures and manually inspect evidence before scoring.', flush=True)


if __name__ == '__main__':
    main()
