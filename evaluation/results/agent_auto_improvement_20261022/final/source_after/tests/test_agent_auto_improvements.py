# 已知失败转为开发回归：验证真实校验路径、范围保护及单次Auto门控，不调用网络。
from copy import deepcopy
import json
from pathlib import Path
import unittest

import agent
from src import agent_answer as answering
from test_agent_answer import ANSWER,payload,review


ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'evaluation/results/auto_closeout_20261022/cases'


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

    def test_real_combined_a04_deictic_experiments_keep_their_original_scene(self):
        folder=ROOT/'evaluation/results/agent_auto_improvement_20261022/runs/a04_auto/loop'
        case=json.loads((folder/'inputs.json').read_text())['question']
        raw=json.loads(json.loads((folder/'actual_chat_calls.json').read_text())[0]['response']['answer'])
        bound=agent.bind_requirements(raw['plan'],case['query'])
        check=raw['assessment']
        self.assertIs(agent.validate_assessment(check,bound['requirements'],case['evidence'],case['inventory']),check)
        row=bound['requirements'][2]
        self.assertIn('open-msmarco',agent.normalize(row['need']))
        self.assertIn('jeopardy',agent.normalize(row['need']))
        self.assertNotIn('transformer',agent.normalize(row['need']))
        self.assertEqual(row['question_quote'],raw['plan']['requirements'][2]['question_quote'])

    def test_real_h10_comparison_can_bind_but_wrong_dataset_gap_is_still_rejected(self):
        folder=ROOT/'evaluation/results/agent_auto_improvement_20261022/runs/h10_auto/loop'
        case=json.loads((folder/'inputs.json').read_text())['question']
        raw=json.loads(json.loads((folder/'actual_chat_calls.json').read_text())[0]['response']['answer'])
        bound=agent.bind_requirements(raw['plan'],case['query'])
        first,second=bound['requirements']
        self.assertNotIn('popqa',agent.normalize(first['need']))
        self.assertIn('popqa',agent.normalize(second['need']))
        with self.assertRaisesRegex(ValueError,'borrows another requirement scope'):
            agent.validate_assessment(raw['assessment'],bound['requirements'],case['evidence'],case['inventory'])
        check=deepcopy(raw['assessment'])
        check['requirements'][0]['gap']='缺少RAG原文中的正确性判据。'
        check['next_action']['query']=agent.search_query(first)
        self.assertIs(agent.validate_assessment(check,bound['requirements'],case['evidence'],case['inventory']),check)


if __name__=='__main__':unittest.main()
