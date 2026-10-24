# 单条已知n06开发回归：真实main/模型/CPU/HTTP，失败保留，不重跑、不传Gold。
from contextlib import redirect_stdout, redirect_stderr
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    protocol = json.loads((OUT / 'smoke_protocol.json').read_text())
    for name, expected in protocol['source_and_input_hashes'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    folder = OUT / 'live'
    folder.mkdir()  # 已有运行不能覆盖或自动续跑。
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    from src import api_llm as api, arxiv_tools
    public = lambda: {k: api.load_settings().get(k) for k in ('base_url', 'model', 'chat_options')}
    assert public() == protocol['api_public_settings']
    model_http, tool_http = [], []
    original_model_http, original_tool_http = api.urlopen, arxiv_tools.urlopen

    def observe(request, original, entries, limit, *args, **kwargs):
        if len(entries) >= limit:
            raise RuntimeError('Frozen HTTP budget exhausted; no retry.')
        assert public() == protocol['api_public_settings']
        entry = {'method': request.get_method(), 'url': request.full_url, 'status': 'running',
                 'started_at_utc': datetime.now(timezone.utc).isoformat()}
        entries.append(entry)
        save(folder / 'model_http.json', model_http)
        save(folder / 'tool_http.json', tool_http)
        try:
            response = original(request, *args, **kwargs)
            entry.update(status='completed', http_status=response.status)
            return response
        except Exception as exc:
            entry.update(status='failed', http_status=getattr(exc, 'code', None),
                         error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            save(folder / 'model_http.json', model_http)
            save(folder / 'tool_http.json', tool_http)

    # 只观察真实HTTP，不替换模型响应、CPU资源、工具结果或任何生产判断。
    def observed_model(request, *args, **kwargs):
        return observe(request, original_model_http, model_http, protocol['max_model_requests'], *args, **kwargs)

    def observed_tool(request, *args, **kwargs):
        return observe(request, original_tool_http, tool_http, protocol['max_arxiv_gets'], *args, **kwargs)

    started = time.perf_counter()
    with (folder / 'console.log').open('w') as log, redirect_stdout(log), redirect_stderr(log), \
            patch.object(api, 'urlopen', side_effect=observed_model), \
            patch.object(arxiv_tools, 'urlopen', side_effect=observed_tool):
        result = pipeline.main(protocol['question'], mode='agent', allow_network=True, output_dir=folder/'main')
    calls = json.loads((folder/'main/actual_chat_calls.json').read_text())
    source_unchanged = all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected
                           for name, expected in protocol['source_and_input_hashes'].items())
    summary = {'question_id': 'n06', 'known_case_development_regression': True,
        'status': result['status'], 'answer_status': result['answer_status'], 'stop_reason': result['stop_reason'],
        'answer': result['answer'], 'model_http_attempts': len(model_http), 'arxiv_get_attempts': len(tool_http),
        'api_summary': result['api_summary'], 'network': result['network'],
        'finish_reasons': [c.get('response', {}).get('finish_reason') for c in calls],
        'source_and_inputs_unchanged': source_unchanged, 'seconds': round(time.perf_counter()-started, 3),
        'automatic_retries': 0, 'new_independent_quality_score': False}
    save(folder/'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
