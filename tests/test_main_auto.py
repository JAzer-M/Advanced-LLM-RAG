# RAG优先Auto：简单题保持RAG成本，明确缺口才调用既有Agent，失败可见降级。
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import agent
import main as pipeline
from src import agent_tools,api_llm as api
import test_main_agent as fixtures
from test_agent_answer import ANSWER,response as answer_response,review
from test_agent_feedback import supported,tool_result
from test_agent_step1 import assessment,missing,plan,response

PARTIAL='A采用第一种做法[1]；现有证据未说明所问的其他条件。'


class MainAutoTests(unittest.TestCase):
    def setUp(self):fixtures.MainAgentTests.setUp(self)

    def invoke(self,out,replies):
        with patch.object(api,'chat_completion',side_effect=replies) as call:
            result=pipeline.main('Describe A.',mode='auto',output_dir=out)
        return result,call

    def test_complete_rag_answer_has_no_extra_gate_or_agent_calls(self):
        with TemporaryDirectory() as temporary,patch.object(agent,'run_diagnostics') as decisions:
            out=Path(temporary)/'run'
            result,call=self.invoke(out,[response(fixtures.DECOMPOSE),answer_response(ANSWER)])
            protocol=json.loads((out/'protocol.json').read_text())
            self.assertFalse((out/'loop').exists())
        self.assertEqual(result['status'],'completed');self.assertEqual(result['answer'],ANSWER)
        self.assertEqual(result['routing']['route'],'direct');self.assertEqual(result['routing']['gate_decision_calls'],0)
        self.assertFalse(result['agent']['invoked']);decisions.assert_not_called()
        self.assertEqual(call.call_count,2);self.assertEqual(protocol['max_actual_attempts'],13)

    def test_explicit_gap_upgrades_and_real_tool_feedback_can_complete_answer(self):
        answer='A报告第二种条件。[2]';checked=review(answer)
        checked['requirements'][0]['citations']=[{'number':2,'quote':'the second condition'}]
        replies=[response(fixtures.DECOMPOSE),answer_response(PARTIAL),response(plan()),
                 response(missing(assessment())),response(supported(1)),answer_response(answer),answer_response(checked)]
        with TemporaryDirectory() as temporary:
            out=Path(temporary)/'run'
            def search(query,resources,source=None):
                self.assertEqual(json.loads((out/'routing.json').read_text())['route'],'agent')
                return tool_result(self.fixture,ids=(1,))
            with patch.object(agent_tools,'search_local_kb',side_effect=search) as fetch:
                result,call=self.invoke(out,replies)
            inputs=json.loads((out/'loop/inputs.json').read_text())['question']
        self.assertEqual(result['status'],'completed');self.assertEqual(result['answer'],answer)
        self.assertEqual(result['selected_ids'],[0,1]);self.assertEqual(call.call_count,7)
        self.assertEqual(result['routing']['trigger_signals'],['explicit_evidence_gap'])
        self.assertNotIn(PARTIAL,json.dumps(inputs,ensure_ascii=False));self.assertNotIn('answer',inputs)
        self.assertEqual(fetch.call_count,1)

    def test_stop_keeps_zero_agent_answer_calls_after_the_rag_probe(self):
        stop=missing(assessment());stop['next_action'].update(type='stop',query=None,source=None)
        replies=[response(fixtures.DECOMPOSE),answer_response('当前证据不足，无法回答。'),response(plan()),response(stop)]
        with TemporaryDirectory() as temporary:result,call=self.invoke(Path(temporary)/'run',replies)
        self.assertEqual(result['status'],'completed');self.assertIn('Insufficient evidence',result['answer'])
        self.assertEqual(result['agent']['answer_summary']['api_attempts'],0)
        self.assertEqual(result['agent']['halt_reason'],'model_stop');self.assertEqual(call.call_count,4)

    def test_existing_citation_repair_can_finish_without_agent(self):
        replies=[response(fixtures.DECOMPOSE),answer_response('A使用第一种做法。[99]'),answer_response({'B1':[1]})]
        with TemporaryDirectory() as temporary,patch.object(agent,'run_diagnostics') as decisions:
            result,call=self.invoke(Path(temporary)/'run',replies)
        self.assertEqual(result['status'],'completed');self.assertIn('[1]',result['answer'])
        self.assertTrue(result['citation_validation']['repair_attempted']);self.assertEqual(call.call_count,3)
        decisions.assert_not_called()

    def test_invalid_probe_citations_cannot_be_used_as_a_fallback(self):
        bad=plan();bad['requirements'][0]['question_quote']='invented unasked fact'
        replies=[response(fixtures.DECOMPOSE),answer_response('A使用第一种做法。[99]'),answer_response({'B1':[]}),
                 response(bad),response(bad)]
        with TemporaryDirectory() as temporary:
            out=Path(temporary)/'run';result,call=self.invoke(out,replies)
            self.assertFalse((out/'fallback.md').exists())
        self.assertEqual(result['status'],'failed');self.assertIn('did not finish',result['answer'])
        self.assertNotIn('[99]', result['answer'])
        self.assertIn('citation_repair_failed',result['routing']['trigger_signals']);self.assertEqual(call.call_count,5)

    def test_decision_failure_exposes_degraded_initial_answer_and_retains_failed_record(self):
        bad=plan();bad['requirements'][0]['question_quote']='invented unasked fact'
        replies=[response(fixtures.DECOMPOSE),answer_response(PARTIAL),response(bad),response(bad)]
        with TemporaryDirectory() as temporary:
            out=Path(temporary)/'run';result,call=self.invoke(out,replies)
            self.assertEqual(json.loads((out/'loop/question.json').read_text())['status'],'failed')
            self.assertTrue((out/'fallback.md').exists())
        self.assertEqual(result['status'],'degraded');self.assertIn('did not finish',result['answer'])
        self.assertIn(PARTIAL,result['answer']);self.assertEqual(result['fallback']['agent_status'],'failed')
        self.assertEqual(call.call_count,4)

    def test_decision_correction_and_feedback_keep_the_original_shared_budget(self):
        bad=missing(assessment());bad['requirements'][0].update(status='partial',supported_part='A已有部分',gap='')
        replies=[response(fixtures.DECOMPOSE),answer_response(PARTIAL),response(plan()),response(bad),
                 response(missing(assessment())),response(bad)]
        with TemporaryDirectory() as temporary,patch.object(agent_tools,'search_local_kb',return_value=tool_result(self.fixture,ids=(1,))):
            result,call=self.invoke(Path(temporary)/'run',replies)
        self.assertEqual(result['status'],'degraded');self.assertEqual(call.call_count,6)
        self.assertEqual(result['agent']['decision_summary']['validation_repair_attempts'],1)

    def test_factual_negative_statement_does_not_trigger_escalation(self):
        with TemporaryDirectory() as temporary,patch.object(agent,'run_diagnostics') as decisions:
            result,_=self.invoke(Path(temporary)/'run',[response(fixtures.DECOMPOSE),answer_response('A不要求严格匹配。[1]')])
        self.assertEqual(result['routing']['route'],'direct');decisions.assert_not_called()

    def test_probe_transport_failure_does_not_retry_or_invent_a_fallback(self):
        with TemporaryDirectory() as temporary,patch.object(api,'chat_completion',side_effect=[response(fixtures.DECOMPOSE),RuntimeError('HTTP 503')]) as call:
            out=Path(temporary)/'run'
            result=pipeline.main('Describe A.',mode='auto',output_dir=out)
            self.assertEqual(result['status'],'failed');self.assertIn('HTTP 503',result['error'])
            self.assertIn('did not finish',result['answer'])
            self.assertEqual(json.loads((out/'result.json').read_text())['status'],'failed')
        self.assertEqual(call.call_count,2)

    def test_cli_marks_degraded_runs_as_unsuccessful(self):
        with patch('sys.argv',['main.py','Describe A.']),patch.object(pipeline,'main',return_value={'status':'degraded'}),self.assertRaises(SystemExit) as stopped:
            pipeline.cli()
        self.assertEqual(stopped.exception.code,1)

    def test_cli_defaults_to_auto_while_python_api_keeps_rag(self):
        with patch('sys.argv',['main.py','Describe A.']),patch.object(pipeline,'main',return_value={}) as entry:pipeline.cli()
        self.assertEqual(entry.call_args.kwargs['mode'],'auto')


if __name__=='__main__':unittest.main()
