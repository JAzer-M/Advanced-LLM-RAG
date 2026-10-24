"""只验证评测执行层的模型留档与反代故障暂停，不调用模型服务。"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('qasper_supervisor', HERE / 'run_supervised.py')
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


class SupervisorTests(unittest.TestCase):
    def test_judge_matches_each_saved_answer_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            (out / 'frozen_sample.json').write_text(json.dumps({'questions': [{'question_id': 'q1'}]}))
            models = ['fixture-a', 'fixture-b', 'fixture-b']
            for mode, model in zip(supervisor.evaluation.MODES, models):
                path = out / 'runs' / 'q1' / f'{mode}.json'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({'execution': {'settings': {'model': model}}}))

            def fake_main():
                for mode in supervisor.evaluation.MODES:
                    supervisor.api_llm.chat_completion('test')
                    supervisor.evaluation.dump(out / 'judge' / 'q1' / f'{mode}.json', {'status': 'completed'})

            with patch.object(supervisor.evaluation, 'OUT', out), \
                    patch.object(supervisor.evaluation, 'main', side_effect=fake_main), \
                    patch.object(supervisor.api_llm, 'chat_completion', return_value={'finish_reason': 'stop'}) as call, \
                    patch.object(supervisor.api_llm, 'load_settings', return_value={'model': 'default'}), \
                    patch.object(sys, 'argv', ['supervisor', 'judge']):
                supervisor.main()
            self.assertEqual([c.kwargs['model'] for c in call.call_args_list], models)
            for mode, model in zip(supervisor.evaluation.MODES, models):
                record = json.loads((out / 'judge' / 'q1' / f'{mode}.json').read_text())
                self.assertEqual(record['judge_requested_model'], model)

    def test_model_usage_is_attached_and_calls_do_not_leak(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)

            def fake_main():
                for mode in ('rag', 'agent'):
                    supervisor.api_llm.chat_completion('test')
                    supervisor.evaluation.dump(out / 'runs' / 'q1' / f'{mode}.json', {'status': 'completed'})

            reply = {'reported_model': 'fixture-reported', 'usage': {'total_tokens': 7}, 'finish_reason': 'stop'}
            with patch.object(supervisor.evaluation, 'OUT', out), \
                    patch.object(supervisor.evaluation, 'main', side_effect=fake_main), \
                    patch.object(supervisor.api_llm, 'chat_completion', return_value=reply), \
                    patch.object(supervisor.api_llm, 'load_settings', return_value={'model': 'fixture', 'api_key': 'not-written'}), \
                    patch.object(sys, 'argv', ['supervisor', 'run']):
                supervisor.main()
            for mode in ('rag', 'agent'):
                text = (out / 'runs' / 'q1' / f'{mode}.json').read_text()
                record = json.loads(text)
                self.assertEqual(len(record['eval_api_calls']), 1)
                self.assertEqual(record['eval_api_calls'][0]['requested_model'], 'fixture')
                self.assertEqual(record['eval_api_calls'][0]['usage']['total_tokens'], 7)
                self.assertNotIn('not-written', text)

    def test_quota_failure_is_saved_before_queue_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            out, visited = Path(temporary), []

            def fake_main():
                for mode in ('rag', 'agent'):
                    visited.append(mode)
                    try:
                        supervisor.api_llm.chat_completion('test')
                    except RuntimeError:
                        pass
                    supervisor.evaluation.dump(out / 'runs' / 'q1' / f'{mode}.json', {'status': 'failed'})

            with patch.object(supervisor.evaluation, 'OUT', out), \
                    patch.object(supervisor.evaluation, 'main', side_effect=fake_main), \
                    patch.object(supervisor.api_llm, 'chat_completion', side_effect=RuntimeError('反代 API 请求失败：HTTP 429。未自动重试。')), \
                    patch.object(supervisor.api_llm, 'load_settings', return_value={'model': 'fixture'}), \
                    patch.object(sys, 'argv', ['supervisor', 'run']):
                with self.assertRaises(SystemExit) as stopped:
                    supervisor.main()
            self.assertEqual(stopped.exception.code, 75)
            self.assertEqual(visited, ['rag'])
            self.assertTrue((out / 'runs' / 'q1' / 'rag.json').is_file())
            self.assertEqual(len(list((out / 'sessions').glob('*proxy_stop.json'))), 1)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SupervisorTests))
    (HERE / 'execution_preflight.json').write_text(json.dumps({
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'success': result.wasSuccessful()}, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
