# 回答阶段行为验收：真实小型原文、模型替身、零网络；不把替身的语义标签当模型效果。
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import agent
from src import agent_answer as answering
from test_agent_feedback import resources, cases, supported
from test_agent_step1 import plan, missing


def response(value):
    return {'answer': value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
            'finish_reason': 'stop', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


ANSWER = 'A使用第一种做法。[1]'


def review(answer=ANSWER):
    return {'requirements': [{'id': 'r1', 'verdict': 'pass', 'answer_quote': answer,
                             'reason': '主体、做法和原文一致。',
                             'citations': [{'number': 1, 'quote': 'the first procedure'}]}],
            'checks': dict.fromkeys(answering.REVIEW_CHECKS, True), 'issues': []}


def payload():
    return {'question': 'Describe A.', 'requirements': plan()['requirements'],
            'assessment': supported(0)['requirements'], 'halt_reason': 'answer_ready',
            'passages': [{'citation': 1, **resources()['chunks'][0]}]}


def saved_case(folder, check=None, halt='answer_ready'):
    """保存与生产结构一致的小型上游记录；旧答案/Gold哨兵用于检查输入白名单。"""
    fixture = resources()
    inputs = cases(fixture)
    inputs['c0']['old_answer'] = 'OLD_ANSWER_SENTINEL'
    check = check or supported(0)
    record = {'id': 'c0', 'query': inputs['c0']['query'], 'kb_version': fixture['knowledge_base']['version'],
              'status': 'completed', 'plan': plan(), 'assessment': check, 'final_assessment': check,
              'halt_reason': halt, 'evidence_after': inputs['c0']['evidence'],
              'gold': 'GOLD_SENTINEL', 'private_trace': 'TRACE_SENTINEL'}
    protocol = {'whitelisted_inputs_sha256': hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(),
                'knowledge_base': fixture['knowledge_base']}
    folder.mkdir()
    for name, value in (('inputs.json', inputs), ('protocol.json', protocol), ('c0.json', record)):
        (folder / name).write_text(json.dumps(value, ensure_ascii=False))
    return folder / 'c0.json', fixture


class AnswerReviewTests(unittest.TestCase):
    def test_supported_answer_uses_two_calls_and_preserves_registry_numbers(self):
        call = Mock(side_effect=[response(ANSWER), response(review())])
        result = answering.answer_with_review(payload(), call)
        self.assertEqual(result['status'], 'review_passed')
        self.assertEqual(result['answer'], ANSWER)
        self.assertEqual([item.args[1] for item in call.call_args_list], ['draft', 'draft_review'])
        self.assertFalse(result['repair_attempted'])
        self.assertEqual(result['citation_check']['cited_sources'][0]['chunk_id'], 0)
        self.assertEqual(result['semantic_correctness'], 'requires_manual_review')

    def test_bad_number_is_repaired_once_and_rechecked(self):
        bad = 'A使用第一种做法。[99]'
        failed = review(bad)
        failed['requirements'][0]['verdict'] = 'fail'
        failed['requirements'][0]['citations'] = []
        failed['checks']['citations'] = False
        failed['issues'] = ['引用99不存在。']
        call = Mock(side_effect=[response(bad), response(failed), response(ANSWER), response(review())])
        result = answering.answer_with_review(payload(), call)
        self.assertEqual(result['status'], 'review_passed')
        self.assertTrue(result['repair_attempted'])
        self.assertEqual(result['drafts'], [bad, ANSWER])
        self.assertEqual(call.call_count, 4)
        self.assertIn('引用99不存在', call.call_args_list[2].args[0])

    def test_subject_numeric_condition_and_coverage_defects_cannot_be_overridden_by_valid_citations(self):
        for defect in ('subjects', 'numbers', 'conditions', 'coverage', 'unsupported_claims', 'gaps'):
            failed = review()
            failed['checks'][defect] = False
            failed['issues'] = ['存在未修复的内容问题。']
            call = Mock(side_effect=[response(ANSWER), response(failed)] * 2)
            with self.subTest(defect=defect):
                result = answering.answer_with_review(payload(), call)
                self.assertEqual(result['status'], 'review_failed')
                self.assertNotIn('A使用第一种做法', result['answer'])
                self.assertEqual(result['rejected_answer'], ANSWER)
                self.assertEqual(call.call_count, 4)

    def test_invalid_json_gets_only_one_revision_and_cannot_count_as_review_pass(self):
        call = Mock(side_effect=[response(ANSWER), response('not json')] * 2)
        result = answering.answer_with_review(payload(), call)
        self.assertEqual(result['status'], 'review_failed')
        self.assertIn('review_error', result['reviews'][0])
        self.assertEqual(call.call_count, 4)

    def test_all_missing_refuses_without_any_model_call(self):
        data = payload()
        data['assessment'] = missing(supported(0))['requirements']
        data['halt_reason'] = 'model_stop'
        call = Mock()
        result = answering.answer_with_review(data, call)
        call.assert_not_called()
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertIn('缺少A的具体做法', result['answer'])
        self.assertFalse(result['repair_attempted'])

    def test_partial_and_missing_requirements_remain_visible_in_generation_and_review(self):
        data = payload()
        data['requirements'].append({'id': 'r2', 'subject': 'B', 'need': 'B', 'question_quote': 'B'})
        data['assessment'][0].update(status='partial', gap='缺少A的条件。')
        data['assessment'].append({'id': 'r2', 'status': 'missing', 'supported_part': '',
                                   'gap': '缺少B的原文。', 'evidence': []})
        data['halt_reason'] = 'action_budget'
        answer = 'A使用第一种做法，但缺少其适用条件。[1]\nB的现有证据不足，无法确定。'
        value = review(answer.splitlines()[0])
        value['requirements'].append({'id': 'r2', 'verdict': 'pass', 'answer_quote': answer.splitlines()[1],
                                      'reason': '明确拒答缺失部分。', 'citations': []})
        call = Mock(side_effect=[response(answer), response(value)])
        result = answering.answer_with_review(data, call)
        self.assertEqual(result['status'], 'review_passed')
        for invocation in call.call_args_list:
            self.assertIn('缺少A的条件', invocation.args[0])
            self.assertIn('缺少B的原文', invocation.args[0])
            self.assertIn('action_budget', invocation.args[0])

    def test_conflicting_does_not_take_the_all_missing_shortcut(self):
        data = payload()
        data['assessment'][0].update(status='conflicting', supported_part='', gap='两段说法冲突。')
        call = Mock(side_effect=RuntimeError('fixture transport failure'))
        with self.assertRaisesRegex(RuntimeError, 'transport'):
            answering.answer_with_review(data, call)
        self.assertEqual(call.call_count, 1)

    def test_review_requires_exact_answer_and_original_quotes(self):
        for mutate in (
            lambda value: value['requirements'][0].update(answer_quote='回答中没有这句话。'),
            lambda value: value['requirements'][0]['citations'][0].update(quote='fabricated quotation'),
            lambda value: value['requirements'][0]['citations'][0].update(number=True),
            lambda value: value['requirements'][0].update(citations=[]),
            lambda value: value['checks'].update(numbers='true'),
            lambda value: value.update(requirements=[]),
            lambda value: value.update(issues=['通过却报告问题。']),
        ):
            value = review()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                answering.validate_review(value, payload(), ANSWER)

    def test_review_cannot_add_a_source_not_cited_in_answer_quote(self):
        data = payload()
        data['passages'].append({'citation': 2, **resources()['chunks'][0]})
        value = review()
        value['requirements'][0]['citations'][0]['number'] = 2
        with self.assertRaisesRegex(ValueError, 'not cited'):
            answering.validate_review(value, data, ANSWER)


class AnswerAuditTests(unittest.TestCase):
    def setUp(self):
        settings = patch.object(agent.api, 'load_settings', return_value={'model': 'fixture'})
        settings.start()
        self.addCleanup(settings.stop)

    def run_saved(self, temporary, call, check=None, halt='answer_ready'):
        root = Path(temporary)
        upstream, fixture = saved_case(root / 'upstream', check, halt)
        loader = patch('src.knowledge_base.load_knowledge_base',
                       return_value=(None, fixture['chunks'], fixture['knowledge_base']))
        return root, upstream, loader

    def test_completed_resume_does_not_call_model_again_and_no_gold_or_old_answer_leaks(self):
        call = Mock(side_effect=[response(ANSWER), response(review())])
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call)
            before = upstream.read_bytes()
            with loader:
                first = agent.run_answer(root, upstream, root / 'answer', call)
                second = agent.run_answer(root, upstream, root / 'answer', call)
            self.assertEqual(upstream.read_bytes(), before)
            for name in ('inputs.json', 'actual_chat_calls.json'):
                text = (root / 'answer' / name).read_text()
                for sentinel in ('GOLD_SENTINEL', 'OLD_ANSWER_SENTINEL', 'TRACE_SENTINEL'):
                    self.assertNotIn(sentinel, text)
            self.assertEqual((root / 'answer/answer.md').read_text().strip(), ANSWER)
        self.assertEqual(first, second)
        self.assertEqual(first['reported_usage']['total_tokens'], 30)
        self.assertEqual(call.call_count, 2)

    def test_transport_failure_keeps_draft_log_and_does_not_retry_on_resume(self):
        call = Mock(side_effect=[response(ANSWER), RuntimeError('HTTP 503')])
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call)
            with loader:
                first = agent.run_answer(root, upstream, root / 'answer', call)
                agent.run_answer(root, upstream, root / 'answer', call)
            calls = json.loads((root / 'answer/actual_chat_calls.json').read_text())
            self.assertEqual(calls[0]['response']['answer'], ANSWER)
            self.assertEqual(calls[1]['status'], 'failed')
            self.assertFalse((root / 'answer/answer.md').exists())
        self.assertEqual(first['status'], 'failed')
        self.assertEqual(first['usage_missing_calls'], [2])
        self.assertEqual(call.call_count, 2)

    def test_truncated_output_is_retained_and_not_delivered(self):
        partial = response(ANSWER)
        partial['finish_reason'] = 'length'
        call = Mock(return_value=partial)
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call)
            with loader:
                summary = agent.run_answer(root, upstream, root / 'answer', call)
            calls = json.loads((root / 'answer/actual_chat_calls.json').read_text())
            self.assertEqual(calls[0]['response']['finish_reason'], 'length')
            self.assertFalse((root / 'answer/answer.md').exists())
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(call.call_count, 1)

    def test_interruption_before_review_reuses_completed_draft(self):
        original = answering.review_prompt
        call = Mock(side_effect=[response(ANSWER), response(review())])
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call)
            with loader:
                with patch.object(answering, 'review_prompt', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                    agent.run_answer(root, upstream, root / 'answer', call)
                with patch.object(answering, 'review_prompt', original):
                    summary = agent.run_answer(root, upstream, root / 'answer', call)
        self.assertEqual(summary['answer_status'], 'review_passed')
        self.assertEqual(call.call_count, 2)

    def test_interruption_during_request_is_not_automatically_retried(self):
        call = Mock(side_effect=KeyboardInterrupt)
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call)
            with loader:
                with self.assertRaises(KeyboardInterrupt):
                    agent.run_answer(root, upstream, root / 'answer', call)
                summary = agent.run_answer(root, upstream, root / 'answer', call)
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(call.call_count, 1)

    def test_answer_budget_stops_before_a_fifth_or_unbudgeted_request(self):
        failed = review()
        failed['checks']['numbers'] = False
        failed['issues'] = ['数字错误。']
        call = Mock(side_effect=[response(ANSWER), response(failed)])
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call)
            with loader, patch.object(agent, 'MAX_ANSWER_CALLS', 2):
                summary = agent.run_answer(root, upstream, root / 'answer', call)
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(call.call_count, 2)

    def test_missing_boundary_is_zero_call_and_saved_as_answer(self):
        call = Mock()
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call, missing(supported(0)), 'model_stop')
            with loader:
                summary = agent.run_answer(root, upstream, root / 'answer', call)
            self.assertIn('证据不足', (root / 'answer/answer.md').read_text())
        call.assert_not_called()
        self.assertEqual(summary['api_attempts'], 0)
        self.assertEqual(summary['answer_status'], 'insufficient_evidence')

    def test_changed_canonical_text_or_version_is_rejected_before_any_model_call(self):
        for field, value in (('text', 'tampered text'), ('kb_version', 'wrong-version')):
            call = Mock()
            with self.subTest(field=field), TemporaryDirectory() as temporary:
                root, upstream, loader = self.run_saved(temporary, call)
                record = json.loads(upstream.read_text())
                record['evidence_after'][0][field] = value
                upstream.write_text(json.dumps(record))
                with loader, self.assertRaises(ValueError):
                    agent.run_answer(root, upstream, root / 'answer', call)
                call.assert_not_called()

    def test_changed_upstream_input_and_failed_record_are_rejected(self):
        for change in ('input', 'failed'):
            call = Mock()
            with self.subTest(change=change), TemporaryDirectory() as temporary:
                root, upstream, loader = self.run_saved(temporary, call)
                if change == 'input':
                    path = upstream.parent / 'inputs.json'
                    value = json.loads(path.read_text()); value['c0']['query'] = 'changed question'
                else:
                    path = upstream
                    value = json.loads(path.read_text()); value['status'] = 'failed'
                path.write_text(json.dumps(value))
                with loader, self.assertRaises(ValueError):
                    agent.run_answer(root, upstream, root / 'answer', call)
                call.assert_not_called()

    def test_answer_ready_requires_supported_evidence(self):
        call = Mock()
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call, missing(supported(0)))
            with loader, self.assertRaisesRegex(ValueError, 'answer_ready'):
                agent.run_answer(root, upstream, root / 'answer', call)
        call.assert_not_called()

    def test_changed_settings_block_resume(self):
        call = Mock(side_effect=[response(ANSWER), response(review())])
        with TemporaryDirectory() as temporary:
            root, upstream, loader = self.run_saved(temporary, call)
            with loader:
                agent.run_answer(root, upstream, root / 'answer', call)
                with patch.object(agent.api, 'load_settings', return_value={'model': 'changed'}), \
                        self.assertRaisesRegex(ValueError, 'changed'):
                    agent.run_answer(root, upstream, root / 'answer', call)
        self.assertEqual(call.call_count, 2)

    def test_cli_saved_answer_mode_needs_no_retrieval(self):
        args = ['agent.py', '--answer-from', '/tmp/loop/h10.json', '--output-dir', '/tmp/answer']
        with patch('sys.argv', args), patch.object(agent, 'run_answer', return_value={
                'status': 'completed', 'answer_status': 'review_passed'}) as finish, \
                patch.object(agent, 'load_replay_cases') as replay:
            agent.main()
        replay.assert_not_called()
        finish.assert_called_once()

    def test_cli_finalize_connects_loop_and_answer_in_separate_directories(self):
        args = ['agent.py', '--replay-dir', '/tmp/replay', '--question-id', 'c0',
                '--max-actions', '3', '--finalize', '--output-dir', '/tmp/combined']
        with patch('sys.argv', args), patch.object(agent, 'load_replay_cases', return_value=({'c0': {}}, {})), \
                patch.object(agent, 'run_diagnostics', return_value={'completed_cases': 1}) as loop, \
                patch.object(agent, 'run_answer', return_value={
                    'status': 'completed', 'answer_status': 'review_passed'}) as finish:
            agent.main()
        self.assertEqual(loop.call_args.args[1], Path('/tmp/combined').resolve() / 'loop')
        self.assertEqual(finish.call_args.args[1:], (Path('/tmp/combined/loop/c0.json').resolve(),
                                                    Path('/tmp/combined/answer').resolve()))
