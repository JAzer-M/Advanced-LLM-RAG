"""两个版本先同时派发、同模型，故障后只继续未尝试结果；无真实API。"""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import run_parallel as runner


class ParallelTests(unittest.TestCase):
    def prepare(self, folder):
        e = runner.evaluation
        e.dump(folder / 'protocol.json', {'harness_sha256': hashlib.sha256(
            (runner.ROOT / 'evaluation/qasper_pair_eval.py').read_bytes()).hexdigest()})
        e.dump(folder / 'supervision.json', {'retired_models': [], 'switches': []})
        e.dump(folder / 'frozen_sample.json', {'questions': [{'question_id': 'q1'}]})

    def test_both_versions_start_before_wait_and_switch_together(self):
        e = runner.evaluation
        with TemporaryDirectory() as temporary, patch.object(e, 'OUT', Path(temporary)), \
                patch.object(e, 'model_queue', return_value=['first', 'second']):
            self.prepare(Path(temporary))
            starts = []
            owner = self
            class Job:
                def __init__(self, command, **kwargs):
                    self.version, self.model = command[3:5]
                    starts.append((self.model, self.version))
                    for mode in ('rag',) if self.model == 'first' else e.MODES:
                        p = e.result_path(self.version, {'question_id': 'q1'}, mode)
                        if not p.exists():
                            e.dump(p, {'status': 'failed' if self.model == 'first' else 'completed'})
                def wait(self):
                    owner.assertEqual({v for m, v in starts if m == self.model}, set(e.VERSIONS))
                    return 75 if self.model == 'first' else 0
            with patch.object(runner.subprocess, 'Popen', side_effect=Job):
                runner.main()
            self.assertEqual(e.load(Path(temporary) / 'supervision.json')['retired_models'], ['first'])
            self.assertEqual(e.load(e.result_path('baseline', {'question_id': 'q1'}, 'rag'))['status'], 'failed')
        self.assertEqual(starts, [('first', 'baseline'), ('first', 'revised'), ('second', 'baseline'), ('second', 'revised')])

    def test_existing_failed_results_are_never_dispatched_again(self):
        e = runner.evaluation
        with TemporaryDirectory() as temporary, patch.object(e, 'OUT', Path(temporary)), \
                patch.object(e, 'model_queue', return_value=['first']), patch.object(runner.subprocess, 'Popen') as start:
            self.prepare(Path(temporary))
            for version in e.VERSIONS:
                for mode in e.MODES:
                    e.dump(e.result_path(version, {'question_id': 'q1'}, mode), {'status': 'failed'})
            runner.main()
        start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
