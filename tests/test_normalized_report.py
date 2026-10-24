# 用少量保存结果验证增补报表、历史指标一致性和输出目录防覆盖。

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import summarize_normalized_precision as reporting


def saved_fixture():
    rows = []
    for qid, gold in [('a', [1]), ('b', [2, 3, 4, 5])]:
        rows.append({'id': qid, 'status': 'completed', 'gold_ids': gold,
                     'metrics_by_k': {str(k): {reporting.METHOD: {
                         'retrieved_ids': [gold[0]], 'precision': 1 / k,
                         'recall': 1 / len(gold), 'ap': 1 / len(gold), 'rr': 1}}
                                      for k in (10, 20)}})
    metrics = {str(k): {'all': {reporting.METHOD: {
        'questions': 2, 'precision': 1 / k, 'recall': 0.625, 'map': 0.625,
        'mrr': 1, 'full_gold': 1}}} for k in (10, 20)}
    source = {'status': 'completed', 'skipped_no_gold': ['outside'], 'variants': {
        'fixed_selection_candidate120': {'questions': rows, 'metrics': metrics}}}
    questions = [{'id': 'a', 'type': 'single_document', 'cohort': 'fixture'},
                 {'id': 'b', 'type': 'cross_document', 'cohort': 'new_all_papers'}]
    return source, questions


class NormalizedReportTests(unittest.TestCase):
    def test_report_preserves_originals_and_weights_gold_in_each_group(self):
        source, questions = saved_fixture()
        before = json.dumps(source)
        report = reporting.build_report(source, questions)
        self.assertEqual(json.dumps(source), before)
        self.assertEqual(report['metric_rows_verified'], 4)
        self.assertEqual(report['aggregate_rows_verified'], 2)
        self.assertEqual(report['skipped_no_gold'], ['outside'])
        group = report['variants']['fixed_selection_candidate120']['metrics']['10']['all'][reporting.METHOD]
        self.assertEqual(group['normalized_precision'], 0.4)
        self.assertEqual(group['recall'], 0.625)
        self.assertEqual(group['hits'], 2)
        self.assertEqual(group['attainable_gold'], 5)
        self.assertEqual(group['precision_ceiling'], 0.25)

    def test_inconsistent_historical_metrics_are_rejected(self):
        source, questions = saved_fixture()
        source['variants']['fixed_selection_candidate120']['questions'][0]['metrics_by_k']['10'][reporting.METHOD]['precision'] = 1
        with self.assertRaisesRegex(ValueError, 'Original metric mismatch'):
            reporting.build_report(source, questions)

    def test_cli_writes_json_and_markdown_and_refuses_overwrite(self):
        source, questions = saved_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, qpath, output = root / 'source.json', root / 'questions.json', root / 'output'
            inputs.write_text(json.dumps(source))
            qpath.write_text(json.dumps(questions))
            argv = ['summarize_normalized_precision', '--input', str(inputs), '--questions', str(qpath),
                    '--output-dir', str(output)]
            with patch('sys.argv', argv), redirect_stdout(io.StringIO()):
                reporting.main()
            self.assertEqual(json.loads((output / 'report.json').read_text())['api_calls'], 0)
            original = (output / 'report.md').read_text()
            self.assertIn('0.4000', original)
            self.assertIn('总命中 2 / 可命中 5', original)
            with patch('sys.argv', argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                reporting.main()
            self.assertEqual((output / 'report.md').read_text(), original)


if __name__ == '__main__':
    unittest.main()
