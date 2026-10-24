# Auto复用既有需求/证据判断：验证直答、暂停后补查、停止、修正额度和真实记账。
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import agent
import main as pipeline
from src import agent_tools, api_llm as api
import test_main_agent as fixtures
from test_agent_answer import ANSWER, response as answer_response, review
from test_agent_feedback import supported, tool_result
from test_agent_step1 import assessment, missing, plan, response


def gate(check):
    extracted=json.loads(response(plan())["answer"])
    return response({"plan":extracted,"assessment":check})


class MainAutoTests(unittest.TestCase):
    def setUp(self):
        fixtures.MainAgentTests.setUp(self)

    def invoke(self, output, replies):
        with patch.object(api,'chat_completion',side_effect=replies) as call:
            result=pipeline.main('Describe A.',mode='auto',output_dir=output)
        return result,call

    def test_sufficient_evidence_uses_one_direct_answer_without_agent_review(self):
        replies=[response(fixtures.DECOMPOSE),gate(supported(0)),answer_response(ANSWER)]
        with TemporaryDirectory() as temporary,patch.object(agent,'run_answer') as reviewed:
            out=Path(temporary)/'run';result,call=self.invoke(out,replies)
            routing=json.loads((out/'routing.json').read_text())
            logs=json.loads((out/'loop/actual_chat_calls.json').read_text())
        self.assertEqual(result['mode'],'auto')
        self.assertEqual(result['routing']['route'],'direct')
        self.assertEqual(routing['gate_decision_calls'],1)
        self.assertEqual(result['answer'],ANSWER)
        self.assertEqual(result['status'],'completed')
        self.assertEqual([c['phase'] for c in logs],['gate'])
        self.assertEqual(call.call_count,3)
        reviewed.assert_not_called()

    def test_tool_route_reuses_the_gate_and_does_not_repeat_model_planning(self):
        answer='A报告第二种条件。[2]';checked=review(answer)
        checked['requirements'][0]['citations']=[{'number':2,'quote':'the second condition'}]
        replies=[response(fixtures.DECOMPOSE),gate(missing(assessment())),
                 response(supported(1)),answer_response(answer),answer_response(checked)]
        with TemporaryDirectory() as temporary:
            out=Path(temporary)/'run'
            def search(query,resources,source=None):
                route=json.loads((out/'routing.json').read_text())
                self.assertEqual(route['route'],'agent')
                return tool_result(self.fixture,ids=(1,))
            with patch.object(agent_tools,'search_local_kb',side_effect=search) as fetch:
                result,call=self.invoke(out,replies)
            logs=json.loads((out/'loop/actual_chat_calls.json').read_text())
        self.assertEqual(result['routing']['route'],'agent')
        self.assertEqual(result['routing']['gate_decision_calls'],1)
        self.assertEqual([c['phase'] for c in logs],['gate','reassess_1'])
        self.assertEqual(result['selected_ids'],[0,1])
        self.assertEqual(result['answer'],answer)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(call.call_count,5)

    def test_all_missing_stop_has_zero_answer_stage_calls(self):
        stop=missing(assessment());stop['next_action'].update(type='stop',query=None,source=None)
        with TemporaryDirectory() as temporary:
            result,call=self.invoke(Path(temporary)/'run',[
                response(fixtures.DECOMPOSE),gate(stop)])
        self.assertEqual(result['routing']['route'],'stop')
        self.assertEqual(result['agent']['answer_summary']['api_attempts'],0)
        self.assertIn('证据不足',result['answer'])
        self.assertEqual(call.call_count,2)

    def test_gate_repair_and_tool_feedback_still_share_one_repair_budget(self):
        bad=missing(assessment())
        bad['requirements'][0].update(status='partial',supported_part='A采用第一种做法。',gap='',
                                      evidence=[{'chunk_id':0,'quote':'first procedure'}])
        replies=[response(fixtures.DECOMPOSE),gate(bad),
                 gate(missing(assessment())),response(bad)]
        with TemporaryDirectory() as temporary,patch.object(agent_tools,'search_local_kb',
                return_value=tool_result(self.fixture,ids=(1,))):
            result,call=self.invoke(Path(temporary)/'run',replies)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['routing']['route'],'agent')
        self.assertEqual(call.call_count,4)

    def test_direct_answer_can_use_the_existing_one_citation_repair(self):
        replies=[response(fixtures.DECOMPOSE),gate(supported(0)),
                 answer_response('A使用第一种做法。[99]'),answer_response({'B1':[1]})]
        with TemporaryDirectory() as temporary:
            result,call=self.invoke(Path(temporary)/'run',replies)
        self.assertEqual(result['status'],'completed')
        self.assertTrue(result['citation_validation']['repair_attempted'])
        self.assertIn('[1]',result['answer'])
        self.assertEqual(call.call_count,4)

    def test_unresolved_direct_citations_remain_failed_without_an_agent_fallback(self):
        replies=[response(fixtures.DECOMPOSE),gate(supported(0)),
                 answer_response('A使用第一种做法。[99]'),answer_response({'B1':[]})]
        with TemporaryDirectory() as temporary:
            out=Path(temporary)/'run';result,call=self.invoke(out,replies)
            self.assertFalse((out/'answer/answer.md').exists())
        self.assertEqual(result['status'],'failed')
        self.assertIsNone(result['answer'])
        self.assertEqual(result['routing']['route'],'direct')
        self.assertEqual(call.call_count,4)

    def test_gate_can_pause_twice_then_resume_without_new_gate_requests(self):
        replies=[gate(missing(assessment())),response(supported(1))]
        case={'question':{'query':'Describe A.','kb_version':self.fixture['knowledge_base']['version'],
                          'evidence':self.fixture['chunks'][:1],'inventory':[{'source':'a.pdf','title':'A'}]}}
        with TemporaryDirectory() as temporary,patch.object(api,'chat_completion',side_effect=replies) as call, \
                patch.object(agent_tools,'search_local_kb',return_value=tool_result(self.fixture,ids=(1,))) as fetch:
            out=Path(temporary)
            first=agent.run_diagnostics(case,out,{},resources=self.fixture,max_actions=3,route_only=True,combined_gate=True)
            again=agent.run_diagnostics(case,out,{},resources=self.fixture,max_actions=3,route_only=True,combined_gate=True)
            self.assertEqual(first['paused_cases'],1)
            self.assertEqual(again['paused_cases'],1)
            fetch.assert_not_called();self.assertEqual(call.call_count,1)
            final=agent.run_diagnostics(case,out,{},resources=self.fixture,max_actions=3,combined_gate=True)
        self.assertEqual(final['completed_cases'],1)
        self.assertEqual(final['paused_cases'],0)
        self.assertEqual(call.call_count,2)
        self.assertEqual(fetch.call_count,1)

    def test_route_only_requires_a_bounded_loop_before_any_api_call(self):
        with TemporaryDirectory() as temporary,patch.object(api,'chat_completion') as call, self.assertRaises(ValueError):
            agent.run_diagnostics({},temporary,{},route_only=True)
        call.assert_not_called()

    def test_cli_defaults_to_auto_while_python_api_keeps_the_rag_baseline(self):
        with patch('sys.argv',['main.py','Describe A.']),patch.object(pipeline,'main',return_value={}) as entry:
            pipeline.cli()
        self.assertEqual(entry.call_args.kwargs['mode'],'auto')


if __name__=='__main__':unittest.main()
