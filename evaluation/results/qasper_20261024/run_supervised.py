"""沿用冻结评测脚本，只增加逐次模型记录，并在反代故障落盘后暂停。"""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from evaluation import qasper_eval as evaluation
from src import api_llm


def main():
    if os.environ.get('QASPER_OUTPUT_DIR'):
        evaluation.OUT = Path(os.environ['QASPER_OUTPUT_DIR']).resolve()
    original_call, original_dump = api_llm.chat_completion, evaluation.dump
    calls = []
    public = {k: api_llm.load_settings().get(k) for k in ('base_url', 'model', 'chat_options')}
    judge_models = []
    if sys.argv[1] == 'judge':
        for question in evaluation.load(evaluation.OUT / 'frozen_sample.json')['questions']:
            for mode in evaluation.MODES:
                source = evaluation.OUT / 'runs' / question['question_id'] / f'{mode}.json'
                target = evaluation.OUT / 'judge' / question['question_id'] / f'{mode}.json'
                if source.exists() and not target.exists():
                    judge_models.append(evaluation.load(source).get('execution', {}).get('settings', {}).get('model', public['model']))
    judge_models = iter(judge_models)
    started = datetime.now(timezone.utc).isoformat()
    session = {'started_at_utc': started, 'step': sys.argv[1], 'settings': public,
               'evaluation_script_sha256': hashlib.sha256(Path(evaluation.__file__).read_bytes()).hexdigest(),
               'supervisor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if sys.argv[1] == 'judge':
        session['judge_model_policy'] = os.environ.get('QASPER_JUDGE_MODEL') or 'match_answer_requested_model'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    original_dump(evaluation.OUT / 'sessions' / f'{stamp}_{sys.argv[1]}.json', session)

    def recorded_call(prompt, model=None, options=None):
        if sys.argv[1] == 'judge':
            model = os.environ.get('QASPER_JUDGE_MODEL') or next(judge_models)
        record = {'requested_model': model or api_llm.load_settings().get('model'),
                  'started_at_utc': datetime.now(timezone.utc).isoformat()}
        began = time.monotonic()
        try:
            response = original_call(prompt, model=model, options=options)
            record.update(status='completed', reported_model=response.get('reported_model'),
                          usage=response.get('usage'), finish_reason=response.get('finish_reason'))
            return response
        except Exception as exc:
            record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            if isinstance(exc, api_llm.IncompleteResponseError):
                record.update(reported_model=exc.response.get('reported_model'),
                              usage=exc.response.get('usage'), finish_reason=exc.response.get('finish_reason'))
            raise
        finally:
            record['seconds'] = round(time.monotonic() - began, 3)
            calls.append(record)

    def recorded_dump(path, value):
        is_run = path.name in {f'{mode}.json' for mode in evaluation.MODES} and path.parent.parent.name in {'runs', 'judge'}
        if not is_run:
            return original_dump(path, value)
        value['execution'] = session
        value['eval_api_calls'] = list(calls)
        if path.parent.parent.name == 'judge' and calls:
            value['judge_requested_model'] = calls[0]['requested_model']
        original_dump(path, value)
        proxy_errors = [c for c in calls if c['status'] == 'failed' and
                        ('反代 API' in c.get('error', '') or 'quota' in c.get('error', '').lower())]
        calls.clear()
        if proxy_errors:
            original_dump(evaluation.OUT / 'sessions' / f'{stamp}_proxy_stop.json',
                          {'result_path': str(path.relative_to(evaluation.OUT)), 'errors': proxy_errors, **session})
            print(f'反代故障已保留，暂停后续请求：{path.relative_to(evaluation.OUT)}', flush=True)
            raise SystemExit(75)
        if (evaluation.OUT / 'STOP_AFTER_RESULT').exists():
            print('当前结果已保存，按停止标记暂停。', flush=True)
            raise SystemExit(76)

    api_llm.chat_completion, evaluation.dump = recorded_call, recorded_dump
    try:
        evaluation.main()
    finally:
        api_llm.chat_completion, evaluation.dump = original_call, original_dump


if __name__ == '__main__':
    main()
