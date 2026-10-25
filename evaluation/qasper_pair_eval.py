"""新论文上的原版/修正版配对评测；旧记录不覆盖，反代故障保留后切换模型。"""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'evaluation/results/qasper_improvement_20261025'
RAW = ROOT / 'data/raw/qasper-holdout-20261025'
KB_VERSION = 'qasper-holdout-20261025'
MODES = ('rag', 'agent', 'auto')
VERSIONS = ('baseline', 'revised')
PRIORITY = ['cn:glm-5.3-flash', 'cn:glm-5.3', 'cn:deepseek-v4.1-flash']


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def prepare():
    from evaluation import qasper_eval as old
    if (OUT / 'frozen_sample.json').exists():
        print('Already frozen; no resampling.', flush=True)
        return
    archive, dataset = old.fetch_dataset()
    data = load(dataset)
    previous = load(old.OUT / 'frozen_sample.json')
    excluded = sorted({q['paper_id'] for q in previous['questions']})
    ids = sorted(p for p in data if old.ARXIV_ID.fullmatch(p) and p not in excluded)
    random.Random(20261025).shuffle(ids)
    papers, questions = [], []
    downloads = load(OUT / 'downloads.json') if (OUT / 'downloads.json').exists() else {}
    old.RAW = RAW
    for pid in ids:
        if len(questions) >= 50:
            break
        qas = [q for q in data[pid]['qas'] if old.references(q)]
        if not qas:
            continue
        if pid not in downloads:
            downloads[pid] = old.download_pdf(pid)
            dump(OUT / 'downloads.json', downloads)
        print(pid, downloads[pid]['status'], len(qas), flush=True)
        if downloads[pid]['status'] == 'failed':
            continue
        papers.append({'arxiv_id': pid, 'title': data[pid]['title']})
        for q in qas:
            questions.append({'question_id': q['question_id'], 'paper_id': pid,
                'paper_title': data[pid]['title'], 'question': q['question'], 'references': old.references(q)})
    if len(questions) < 50:
        raise RuntimeError('Not enough downloadable papers; keep failures and inspect.')
    dump(OUT / 'paper_manifest.json', {'source': 'QASPER v0.3 test split (CC BY 4.0)', 'papers': papers})
    dump(OUT / 'frozen_sample.json', {'seed': 20261025, 'target_questions': 50,
        'sampling': 'shuffle sorted eligible paper IDs; all questions from each paper until at least 50',
        'excluded_previous_papers': excluded, 'eligible_new_papers': len(ids), 'papers': len(papers),
        'dataset': old.DATASET_URL, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'questions': questions, 'frozen_at_utc': now()})
    print(f'Frozen: {len(papers)} papers / {len(questions)} questions.', flush=True)


def build():
    sample = load(OUT / 'frozen_sample.json')
    expected = sorted({q['paper_id'] + '.pdf' for q in sample['questions']})
    if sorted(p.name for p in RAW.glob('*.pdf')) != expected:
        raise ValueError('PDF set differs from frozen sample.')
    folder = ROOT / 'data/processed/versions' / KB_VERSION
    if folder.exists():
        print('KB already exists; not overwritten.', flush=True)
        return
    subprocess.run([sys.executable, str(ROOT / 'build_semantic_index.py'), '--version', KB_VERSION,
        '--raw-dir', str(RAW), '--paper-manifest', str(OUT / 'paper_manifest.json'),
        '--two-column-files', *expected], cwd=ROOT, check=True)


def result_path(version, question, mode, stage='runs'):
    return OUT / stage / version / question['question_id'] / f'{mode}.json'


def proxy_failed(calls):
    return any(c['status'] == 'failed' and
        re.search(r'反代 API|HTTP (?:401|402|403|404|429|50\d)|quota|rate.limit', c.get('error', ''), re.I)
        for c in calls)


def tracked_api(api, path, model):
    original = api.chat_completion
    calls = []

    def call(prompt, **kwargs):
        record = {'number': len(calls) + 1, 'requested_model': kwargs.get('model') or model,
            'started_at_utc': now(), 'status': 'running', 'prompt_characters': len(prompt),
            'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()}
        calls.append(record)
        dump(path, calls)  # 落盘后才发送，崩溃也能审计已发起的调用。
        started = time.monotonic()
        try:
            response = original(prompt, **kwargs)
            record.update(status='completed', **{k: response.get(k) for k in
                ('reported_model', 'usage', 'finish_reason', 'request_parameters')})
            return response
        except Exception as exc:
            record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            if isinstance(exc, api.IncompleteResponseError):
                record.update(**{k: exc.response.get(k) for k in ('reported_model', 'usage', 'finish_reason')})
            raise
        finally:
            record['seconds'] = round(time.monotonic() - started, 3)
            dump(path, calls)
    return call, calls


def worker(version, model, question_id, stage='runs', sample_path=None, kb_version=KB_VERSION):
    """每个版本单独进程，确保绝对导入来自冻结源码；两版共用同一配对库。"""
    source = OUT / 'baseline_source' if version == 'baseline' else ROOT
    sys.path.insert(0, str(source))
    from src import runtime_paths
    runtime_paths.data_root = lambda: ROOT  # 数据共享；不切换当前库、不改写私有配置。
    from src import api_llm as api
    original_settings = api.load_settings
    api.load_settings = lambda: {**original_settings(), 'model': model}
    import main as pipeline
    from evaluation import qasper_eval as old
    from src.model_json import loads_model_json
    if Path(pipeline.__file__).resolve().parent != source or api.SETTINGS_PATH != ROOT / 'api.local.json':
        raise RuntimeError('Worker imported the wrong source tree or private settings location.')
    if stage in {'runs', 'judge'}:
        protocol = load(OUT / 'protocol.json')
        expected = protocol[version + '_source_hashes']
        for name, checksum in expected.items():
            if hashlib.sha256((source / name).read_bytes()).hexdigest() != checksum:
                raise RuntimeError(f'Frozen {version} source changed: {name}')
        if api.load_settings().get('chat_options') != protocol['chat_options']:
            raise RuntimeError('Chat options changed after freezing.')
    old.cached_models(pipeline)
    sample = load(sample_path or OUT / 'frozen_sample.json')
    question = next(q for q in sample['questions'] if q['question_id'] == question_id)
    query = f'For the paper "{question["paper_title"]}" (arXiv: {question["paper_id"]}), answer this question: {question["question"]}'
    original_call = api.chat_completion
    for mode in MODES:
        path = result_path(version, question, mode, stage)
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        journal = path.with_name(mode + '_calls.json')
        if journal.exists() and load(journal):
            raise RuntimeError('Existing call journal without result; inspect it before any new request.')
        api.chat_completion, calls = tracked_api(api, journal, model)
        began = time.monotonic()
        result = None
        with path.with_suffix('.log').open('w', encoding='utf-8') as log, redirect_stdout(log), redirect_stderr(log):
            try:
                if stage in {'runs', 'development'}:
                    result = pipeline.main(query, kb_version=kb_version, mode=mode,
                        output_dir=path.with_name(mode + '_run') if mode != 'rag' else None)
                else:
                    answer = load(result_path(version, question, mode))
                    if answer.get('status') == 'failed':
                        result = {'status': 'completed', 'verdict': 'incorrect', 'declined': False,
                            'reason': 'Failed generation counts as incorrect in the planned denominator.',
                            'judging_method': 'failed_generation_rule',
                            'generation_model': answer['evaluation']['requested_model']}
                        dump(path, {**result, 'eval_api_calls': [], 'eval_elapsed_seconds': 0,
                            'evaluation': {'version': version, 'requested_model': None, 'stage': stage}})
                        api.chat_completion = original_call
                        continue
                    prompt = old.JUDGE.format(question=question['question'],
                        references='\n'.join(f'- ({r["type"]}) {r["answer"]}' for r in question['references']),
                        answer=old.clean_answer(answer.get('answer')) or '(empty)')
                    reply = api.chat_completion(prompt)
                    verdict = loads_model_json(reply['answer'])
                    if (verdict.get('verdict') not in ('correct', 'partially_correct', 'incorrect')
                            or type(verdict.get('declined')) is not bool):
                        raise ValueError('Invalid judge JSON.')
                    result = {'status': 'completed', **verdict, 'response': reply,
                        'generation_model': answer['evaluation']['requested_model']}
            except Exception as exc:
                result = {'query': query, 'mode': mode, 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}
        result = result or {'query': query, 'mode': mode, 'status': 'failed', 'error': 'No result.'}
        result.update(original_question=question['question'], eval_api_calls=list(calls),
            eval_elapsed_seconds=round(time.monotonic() - began, 3),
            evaluation={'version': version, 'requested_model': model, 'stage': stage,
                'source_root': str(source),
                'started_at_utc': calls[0]['started_at_utc'] if calls else now(), 'kb_version': kb_version})
        dump(path, result)
        api.chat_completion = original_call
        print(version, question_id[:10], mode, stage, result['status'],
            sum((c.get('usage') or {}).get('total_tokens', 0) for c in calls), 'tokens',
            result['eval_elapsed_seconds'], 's', flush=True)
        if proxy_failed(calls):
            return 75
        if (OUT / 'STOP_AFTER_RESULT').exists():
            return 76
    return 0


def model_queue():
    available = load(OUT / 'model_inventory.json')['models']
    others = ['cn:minimax-m3.1-flash', 'cn:kimi-k3-1', 'cn:mimo-v2.6-pro', 'cn:step-5-preview',
        'cn:minimax-m3', 'cn:kimi-k2.8-preview', 'cn:deepseek-v4-flash', 'cn:hy4-preview-f',
        'cn:glm-5.2', 'cn:deepseek-v4-pro', 'cn:kimi-k3.1-pro', 'cn:hy4-preview', 'cn:hy3', 'cn:hy3-x', 'cn:glm-5.1']
    return [m for m in PRIORITY + others if m in available]


def supervise(stage='runs', sample_path=None, kb_version=KB_VERSION):
    sample = load(sample_path or OUT / 'frozen_sample.json')
    state_path = OUT / 'supervision.json'
    state = load(state_path) if state_path.exists() else {'started_at_utc': now(), 'retired_models': [], 'switches': []}
    queue = model_queue()
    for question in sample['questions']:
        for version in VERSIONS if stage != 'development' else ('revised',):
            while any(not result_path(version, question, m, stage).exists() for m in MODES):
                candidates = [m for m in queue if m not in state['retired_models']]
                if not candidates:
                    raise RuntimeError('All available model candidates failed; preserved records, no automatic cycle.')
                model = candidates[0]
                if stage == 'judge':
                    # 若作答模型仍可用，优先匹配；已限额的模型不逐题反复探测。
                    preferred = [load(result_path(version, question, m))['evaluation']['requested_model']
                                 for m in MODES if not result_path(version, question, m, stage).exists()]
                    if preferred and len(set(preferred)) == 1 and preferred[0] in candidates:
                        model = preferred[0]
                print('START', stage, question['question_id'][:10], version, model, flush=True)
                command = [sys.executable, str(Path(__file__)), 'worker', version, model, question['question_id'], stage,
                    str(sample_path or OUT / 'frozen_sample.json'), kb_version]
                done = subprocess.run(command, cwd=ROOT)
                if done.returncode == 75:
                    state['retired_models'].append(model)
                    state['switches'].append({'at_utc': now(), 'from': model, 'stage': stage,
                        'question_id': question['question_id'], 'version': version, 'cause': 'proxy failure; result preserved'})
                    dump(state_path, state)
                    print('ROTATE', model, 'proxy failure preserved.', flush=True)
                elif done.returncode == 76:
                    return
                elif done.returncode:
                    raise RuntimeError(f'Worker exited {done.returncode}; inspect call journals before resuming.')
    state['last_completed_stage'] = stage
    state['updated_at_utc'] = now()
    dump(state_path, state)


if __name__ == '__main__':
    step = sys.argv[1]
    if step == 'worker':
        raise SystemExit(worker(*sys.argv[2:6], sample_path=Path(sys.argv[6]), kb_version=sys.argv[7]))
    elif step in {'runs', 'judge', 'development'}:
        supervise(step, Path(sys.argv[2]) if len(sys.argv) > 2 else None,
                  sys.argv[3] if len(sys.argv) > 3 else KB_VERSION)
    else:
        {'prepare': prepare, 'build': build}[step]()
