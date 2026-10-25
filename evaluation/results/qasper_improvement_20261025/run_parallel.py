"""同题两版本独立进程并行；使用原冻结worker，单一父进程管理模型切换。"""
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation import qasper_pair_eval as evaluation


def main(stage='runs'):
    out = evaluation.OUT
    protocol = evaluation.load(out / 'protocol.json')
    worker = ROOT / 'evaluation/qasper_pair_eval.py'
    if hashlib.sha256(worker.read_bytes()).hexdigest() != protocol['harness_sha256']:
        raise RuntimeError('Frozen worker changed; stop before dispatch.')
    state = evaluation.load(out / 'supervision.json')
    queue = evaluation.model_queue()
    sample = evaluation.load(out / 'frozen_sample.json')
    for question in sample['questions']:
        while True:
            pending = [v for v in evaluation.VERSIONS if any(
                not evaluation.result_path(v, question, m, stage).exists() for m in evaluation.MODES)]
            if not pending:
                break
            candidates = [m for m in queue if m not in state['retired_models']]
            if not candidates:
                raise RuntimeError('All candidates retired; keep results and stop.')
            model = candidates[0]
            if stage == 'judge':
                generation_models = {evaluation.load(evaluation.result_path(v, question, m))['evaluation']['requested_model']
                    for v in pending for m in evaluation.MODES
                    if not evaluation.result_path(v, question, m, stage).exists()}
                if len(generation_models) == 1 and next(iter(generation_models)) in candidates:
                    model = next(iter(generation_models))
            print('START PAIRED', stage, question['question_id'][:10], model, pending, flush=True)
            jobs = {v: subprocess.Popen([sys.executable, str(worker), 'worker', v, model,
                question['question_id'], stage, str(out / 'frozen_sample.json'), evaluation.KB_VERSION], cwd=ROOT)
                for v in pending}
            codes = {v: job.wait() for v, job in jobs.items()}
            evaluation.dump(out / 'last_parallel_job.json', {'at_utc': evaluation.now(), 'stage': stage,
                'question_id': question['question_id'], 'model': model, 'exit_codes': codes})
            if any(code not in (0, 75, 76) for code in codes.values()):
                raise RuntimeError(f'Worker crashed: {codes}; inspect journals before resuming.')
            if 75 in codes.values():
                state['retired_models'].append(model)
                state['switches'].append({'at_utc': evaluation.now(), 'from': model, 'stage': stage,
                    'question_id': question['question_id'], 'versions': [v for v in codes if codes[v] == 75],
                    'cause': 'proxy failure; both workers finished before rotation; failures preserved'})
                evaluation.dump(out / 'supervision.json', state)
                print('ROTATE', model, codes, flush=True)
            if 76 in codes.values() or (out / 'STOP_AFTER_RESULT').exists():
                return
    state.update(last_completed_stage=stage, updated_at_utc=evaluation.now(), parallel_version_workers=2)
    evaluation.dump(out / 'supervision.json', state)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'runs')
