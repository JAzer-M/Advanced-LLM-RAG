# 已知失败转为开发回归：验证真实校验路径、范围保护及单次Auto门控，不调用网络。
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock,patch

import agent
from src import agent_answer as answering
from test_agent_answer import ANSWER,payload,review
from test_agent_feedback import cases,resources,supported,tool_result
from test_agent_step1 import assessment,missing,plan,response


ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'evaluation/results/auto_closeout_20261022/cases'


def combined(check=None,proposal=None):
    extracted=json.loads(response(plan()).get('answer')) if proposal is None else proposal
    return {'plan':extracted,'assessment':supported(0) if check is None else check}


class AgentValidationImprovementTests(unittest.TestCase):
    def test_real_a03_assessment_accepts_only_pdf_hyphen_whitespace_difference(self):
        folder=OLD/'a03/auto/loop'
        record=json.loads((folder/'question.json').read_text())
        case=json.loads((folder/'inputs.json').read_text())['question']
        raw=json.loads((folder/'actual_chat_calls.json').read_text())[-1]['response']['answer']
        check=json.loads(raw)
        self.assertIs(agent.validate_assessment(check,record['plan']['requirements'],case['evidence'],case['inventory']),check)
        for bad in ('ArcChallenge','Arc-Challenger'):
            invalid=deepcopy(check)
            invalid['requirements'][0]['evidence'][0]['quote']=check['requirements'][0]['evidence'][0]['quote'].replace('Arc-Challenge',bad)
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'Quoted text'):
                agent.validate_assessment(invalid,record['plan']['requirements'],case['evidence'],case['inventory'])

    def test_review_uses_same_pdf_quote_rule_without_relaxing_actual_answer_quote(self):
        data=payload();data['passages'][0]['text']='The method is Arc- Challenge and uses the first procedure.'
        checked=review();checked['requirements'][0]['citations'][0]['quote']='Arc-Challenge and uses the first procedure'
        self.assertIs(answering.validate_review(checked,data,ANSWER),checked)
        checked['requirements'][0]['answer_quote']='A...第一种做法[1]'
        with self.assertRaisesRegex(ValueError,'actual answer'):
            answering.validate_review(checked,data,ANSWER)

    def test_hyphen_compatibility_does_not_change_minus_sign_or_concatenate_sentences(self):
        data=payload();data['passages'][0]['text']='The gain was - 0.99. A uses the first procedure.'
        for quote in ['The gain was 0.99','The gain was -0.99','The gain was. A uses']:
            checked=review();checked['requirements'][0]['citations'][0]['quote']=quote
            with self.subTest(quote=quote),self.assertRaisesRegex(ValueError,'original passage'):
                answering.validate_review(checked,data,ANSWER)

    def test_real_a04_both_final_plans_bind_without_transferring_rag_document_count(self):
        for arm in ('agent','auto'):
            folder=OLD/f'a04/{arm}/loop'
            case=json.loads((folder/'inputs.json').read_text())['question']
            raw=json.loads((folder/'actual_chat_calls.json').read_text())[-1]['response']['answer']
            bound=agent.bind_requirements(json.loads(raw),case['query'])
            first,second=bound['requirements']
            self.assertNotIn('rag',agent.normalize(first['need']))
            self.assertNotIn('documents',agent.normalize(first['need']))
            self.assertIn('beam size',first['need'])
            self.assertIn('how many documents',second['need'])
            self.assertNotIn('transformer',agent.normalize(second['need']))
            agent.validate_plan(bound,case['query'])

    def test_repeated_for_keeps_each_subjects_own_task_qualifier(self):
        query='For Atlas on Orion and for Nova on Vega, what batch size is used in each?'
        proposal={'requirements':[{'id':'r1','subject':'Atlas','question_quote':query},
                                  {'id':'r2','subject':'Nova','question_quote':query}]}
        bound=agent.bind_requirements(proposal,query)['requirements']
        self.assertIn('orion',agent.normalize(bound[0]['need']))
        self.assertNotIn('vega',agent.normalize(bound[0]['need']))
        self.assertIn('vega',agent.normalize(bound[1]['need']))
        self.assertNotIn('orion',agent.normalize(bound[1]['need']))

    def test_shared_prefix_cannot_transfer_another_subjects_later_clause(self):
        query='For Atlas translation and for Nova generation, what beam size is used, and what costs does Nova report?'
        proposal={'requirements':[{'id':'r1','subject':'Atlas translation','question_quote':query},
                                  {'id':'r2','subject':'Nova generation','question_quote':query}]}
        with self.assertRaisesRegex(ValueError,'another declared subject'):
            agent.bind_requirements(proposal,query)


class AutoCombinedGateTests(unittest.TestCase):
    def setUp(self):
        patcher=patch.object(agent.api,'load_settings',return_value={'model':'fixture'})
        patcher.start();self.addCleanup(patcher.stop)
        self.fixture=resources();self.inputs=cases(self.fixture)

    def run_gate(self,out,call,route_only=False):
        return agent.run_diagnostics(self.inputs,out,{},call=call,resources=self.fixture,
                                     max_actions=3,combined_gate=True,route_only=route_only)

    def test_sufficient_gate_uses_one_request_and_preserves_evidence_and_plan_validation(self):
        call=Mock(return_value=response(combined()))
        with TemporaryDirectory() as out:
            result=self.run_gate(out,call)
            record=json.loads((Path(out)/'c0.json').read_text())
        self.assertEqual(result['completed_cases'],1)
        self.assertEqual(result['api_attempts'],1)
        self.assertEqual(record['halt_reason'],'answer_ready')
        self.assertEqual(call.call_count,1)

    def test_missing_user_requested_fact_cannot_be_removed_from_plan_to_force_direct(self):
        self.inputs['c0']['query']='Describe A and give its training batch size.'
        proposal={'requirements':[{'id':'r1','subject':'A','question_quote':'Describe A'}]}
        call=Mock(return_value=response(combined(proposal=proposal)))
        with TemporaryDirectory() as out:
            result=self.run_gate(out,call)
            record=json.loads((Path(out)/'c0.json').read_text())
        self.assertEqual(result['completed_cases'],0)
        self.assertIn('requested',record['error'])
        self.assertEqual(call.call_count,2)

    def test_combined_search_is_locally_bound_then_resumed_without_another_gate_call(self):
        check=missing(assessment());check['next_action']['query']=None
        call=Mock(side_effect=[response(combined(check)),response(supported(1))])
        with TemporaryDirectory() as out,patch('src.agent_tools.search_local_kb',return_value=tool_result(self.fixture,ids=(1,))) as search:
            first=self.run_gate(out,call,route_only=True)
            self.run_gate(out,call,route_only=True)
            self.assertEqual(first['paused_cases'],1);self.assertEqual(call.call_count,1);search.assert_not_called()
            final=self.run_gate(out,call)
            logs=json.loads((Path(out)/'actual_chat_calls.json').read_text())
        self.assertEqual(final['completed_cases'],1)
        self.assertEqual([c['phase'] for c in logs],['gate','reassess_1'])
        self.assertEqual(call.call_count,2);search.assert_called_once()
        self.assertEqual(search.call_args.args[0],agent.search_query(plan()['requirements'][0]))

    def test_gate_and_feedback_still_share_only_one_validation_repair(self):
        bad=missing(assessment());bad['requirements'][0].update(status='partial',supported_part='A有事实',gap='')
        call=Mock(side_effect=[response(combined(bad)),response(combined(missing(assessment()))),response(bad)])
        with TemporaryDirectory() as out,patch('src.agent_tools.search_local_kb',return_value=tool_result(self.fixture,ids=(1,))):
            result=self.run_gate(out,call)
            record=json.loads((Path(out)/'c0.json').read_text())
        self.assertEqual(result['completed_cases'],0)
        self.assertIn('repair budget',record['error'])
        self.assertEqual(call.call_count,3)

    def test_gate_transport_failure_is_not_retried_or_converted_to_another_mode(self):
        call=Mock(side_effect=RuntimeError('HTTP 503'))
        with TemporaryDirectory() as out:
            result=self.run_gate(out,call)
            again=self.run_gate(out,call)
        self.assertEqual(result['completed_cases'],0);self.assertEqual(again['completed_cases'],0)
        self.assertEqual(call.call_count,1)

    def test_combined_gate_requires_a_bounded_loop(self):
        with TemporaryDirectory() as out,self.assertRaises(ValueError):
            agent.run_diagnostics({},out,{},combined_gate=True)


if __name__=='__main__':unittest.main()
