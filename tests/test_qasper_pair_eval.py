"""评测监督器必须保留失败和实际用量，不能因续跑再次计费同一结果。"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from evaluation import qasper_pair_eval as evaluation
from src import api_llm


class PairSupervisorTests(unittest.TestCase):
    def test_call_is_journaled_before_dispatch_and_usage_survives_truncation(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'calls.json'
            response = {'answer': 'partial', 'finish_reason': 'length', 'usage': {'total_tokens': 73},
                        'reported_model': 'fixture'}
            def dispatch(prompt):
                self.assertEqual(json.loads(path.read_text())[0]['status'], 'running')
                raise api_llm.IncompleteResponseError(response)
            api = SimpleNamespace(chat_completion=dispatch, IncompleteResponseError=api_llm.IncompleteResponseError)
            call, calls = evaluation.tracked_api(api, path, 'fixture')
            with self.assertRaises(api_llm.IncompleteResponseError):
                call('Question?')
            saved = json.loads(path.read_text())
        self.assertEqual(saved, calls)
        self.assertEqual(saved[0]['usage']['total_tokens'], 73)
        self.assertEqual(saved[0]['status'], 'failed')

    def test_only_transport_or_quota_failure_triggers_rotation(self):
        self.assertTrue(evaluation.proxy_failed([{'status': 'failed', 'error': '反代 API 请求失败：HTTP 429。'}]))
        self.assertFalse(evaluation.proxy_failed([{'status': 'failed', 'error': 'Invalid quoted text.'}]))
        self.assertFalse(evaluation.proxy_failed([{'status': 'completed'}]))

    def test_failed_results_are_not_regenerated_on_resume(self):
        with TemporaryDirectory() as folder, patch.object(evaluation, 'OUT', Path(folder)), \
                patch.object(evaluation, 'model_queue', return_value=['fixture']), \
                patch.object(evaluation.subprocess, 'run') as run:
            q = {'question_id': 'q1'}
            evaluation.dump(Path(folder) / 'frozen_sample.json', {'questions': [q]})
            for v in evaluation.VERSIONS:
                for m in evaluation.MODES:
                    evaluation.dump(evaluation.result_path(v, q, m), {'status': 'failed'})
            evaluation.supervise()
        run.assert_not_called()

    def test_proxy_error_retires_model_and_continues_unattempted_modes(self):
        with TemporaryDirectory() as folder, patch.object(evaluation, 'OUT', Path(folder)), \
                patch.object(evaluation, 'model_queue', return_value=['first', 'second']):
            q = {'question_id': 'q1'}
            evaluation.dump(Path(folder) / 'frozen_sample.json', {'questions': [q]})
            used = []
            def dispatch(command, **kwargs):
                version, model = command[3:5]
                used.append(model)
                modes = ('rag',) if model == 'first' else evaluation.MODES
                for mode in modes:
                    path = evaluation.result_path(version, q, mode)
                    if not path.exists():
                        evaluation.dump(path, {'status': 'failed' if model == 'first' else 'completed'})
                return SimpleNamespace(returncode=75 if model == 'first' else 0)
            with patch.object(evaluation.subprocess, 'run', side_effect=dispatch):
                evaluation.supervise()
            state = evaluation.load(Path(folder) / 'supervision.json')
            preserved = evaluation.load(evaluation.result_path('baseline', q, 'rag'))
        self.assertEqual(used, ['first', 'second', 'second'])
        self.assertEqual(state['retired_models'], ['first'])
        self.assertEqual(preserved['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
