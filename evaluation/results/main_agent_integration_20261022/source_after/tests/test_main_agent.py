# 新问题经main真实入口进入既有Agent循环；只替换模型/检索资源，不替换Agent执行。
import io
import json
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import agent
import main as pipeline
from src import agent_tools, api_llm as api
from test_agent_answer import ANSWER, response as answer_response, review
from test_agent_feedback import resources, supported, tool_result
from test_agent_step1 import assessment, missing, plan, response


DECOMPOSE = {'needs_decomposition':False,'sub_queries':[]}


class MainAgentTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(redirect_stdout(io.StringIO()))
        self.fixture = resources()
        self.index = SimpleNamespace(ntotal=3,d=384)
        self.embedding, self.bm25, self.reranker = object(), object(), object()
        for owner,name,value in (
            (pipeline,'load_settings',{'model':'fixture'}),
            (api,'load_settings',{'model':'fixture'}),
            (pipeline,'load_knowledge_base',(self.index,self.fixture['chunks'],self.fixture['knowledge_base'])),
            (pipeline,'load_embedding_model',self.embedding),
            (pipeline,'build_bm25_index',self.bm25),
            (pipeline,'CrossEncoder',self.reranker),
            (pipeline,'retrieve',[self.fixture['chunks'][0]]),
            (pipeline,'retrieve_bm25',[]),
            (pipeline,'rank_evidence',([self.fixture['chunks'][0]],[])),
            (pipeline,'supplement_evidence',([self.fixture['chunks'][0]],{'rounds':0})),
            (pipeline,'render_complete',{'answer':'fixture'})):
            self.stack.enter_context(patch.object(owner,name,return_value=value))
        self.stack.enter_context(patch('src.knowledge_base.load_knowledge_base',return_value=(
            self.index,self.fixture['chunks'],self.fixture['knowledge_base'])))
        context = pipeline.build_context(self.fixture['chunks'][:1])
        self.stack.enter_context(patch.object(pipeline,'build_evidence_context',return_value=(
            context,{'citation_registry':self.fixture['chunks'][:1]})))

    def invoke(self, output, responses):
        with patch.object(api,'chat_completion',side_effect=responses) as call:
            result = pipeline.main('Describe A.',mode='agent',output_dir=output)
        return result, call

    def test_fresh_question_reaches_answer_without_a_rag_draft_or_resource_reload(self):
        replies=[response(DECOMPOSE),response(plan()),response(supported(0)),
                 answer_response(ANSWER),answer_response(review())]
        with TemporaryDirectory() as temporary, patch.object(agent_tools,'load_search_resources') as reload:
            out=Path(temporary)/'run'
            result,call=self.invoke(out,replies)
            inputs=json.loads((out/'loop/inputs.json').read_text())['question']
            log=json.loads((out/'actual_chat_calls.json').read_text())
            saved=json.loads((out/'result.json').read_text())
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['answer'],ANSWER)
        self.assertEqual(result['agent']['answer_summary']['answer_status'],'review_passed')
        self.assertEqual(saved['answer'],ANSWER)
        self.assertEqual(set(inputs),{'query','kb_version','evidence','inventory'})
        self.assertEqual([c['phase'] for c in log],['decompose','decision','decision','answer','answer'])
        self.assertEqual(result['api_summary']['attempts'],5)
        self.assertEqual(call.call_count,5)
        reload.assert_not_called()
        self.assertEqual(result['ledger']['citation_registry'][0]['chunk_id'],0)

    def test_agent_can_execute_a_tool_using_the_same_loaded_resources(self):
        answer='A报告第二种条件。[2]'
        checked=review(answer)
        checked['requirements'][0]['citations']=[{'number':2,'quote':'the second condition'}]
        replies=[response(DECOMPOSE),response(plan()),response(missing(assessment())),
                 response(supported(1)),answer_response(answer),answer_response(checked)]
        with TemporaryDirectory() as temporary, patch.object(agent_tools,'search_local_kb',
                return_value=tool_result(self.fixture,ids=(1,))) as search:
            result,call=self.invoke(Path(temporary)/'run',replies)
        used=search.call_args.args[1]
        self.assertIs(used['index'],self.index)
        self.assertIs(used['embedding_model'],self.embedding)
        self.assertIs(used['bm25'],self.bm25)
        self.assertIs(used['reranker_model'],self.reranker)
        self.assertEqual(result['agent']['actions_executed'],1)
        self.assertEqual(result['selected_ids'],[0,1])
        self.assertEqual(result['initial_selected_ids'],[0])
        self.assertEqual(result['answer'],answer)
        self.assertEqual(call.call_count,6)

    def test_default_rag_keeps_the_existing_generation_path(self):
        with patch.object(api,'chat_completion',side_effect=[response(DECOMPOSE),answer_response(ANSWER)]) as call, \
                patch.object(agent,'run_diagnostics') as loop:
            result=pipeline.main('Describe A.')
        self.assertEqual(result['answer'],ANSWER)
        self.assertEqual(call.call_count,2)
        loop.assert_not_called()
        pipeline.load_knowledge_base.assert_called_once_with(Path(pipeline.__file__).resolve().parent/'data/processed',None)

    def test_agent_selects_the_supported_eight_paper_version_without_changing_a_pointer(self):
        with TemporaryDirectory() as temporary:
            self.invoke(Path(temporary)/'run',[response(DECOMPOSE),response(plan()),response(supported(0)),
                answer_response(ANSWER),answer_response(review())])
        self.assertEqual(pipeline.load_knowledge_base.call_args.args[1],agent_tools.SEARCH_KB_VERSION)

    def test_invalid_mode_or_agent_kb_fails_before_loading_or_calling_models(self):
        for options in ({'mode':'auto'},{'mode':'agent','kb_version':'another-version'}):
            with self.subTest(options=options),patch.object(api,'chat_completion') as call,self.assertRaises(ValueError):
                pipeline.main('Describe A.',**options)
            call.assert_not_called()
        pipeline.load_embedding_model.assert_not_called()

    def test_nonempty_output_is_rejected_before_any_api_request(self):
        with TemporaryDirectory() as temporary,patch.object(api,'chat_completion') as call:
            out=Path(temporary);(out/'keep.txt').write_text('keep')
            with self.assertRaises(ValueError):pipeline.main('Describe A.',mode='agent',output_dir=out)
            self.assertEqual((out/'keep.txt').read_text(),'keep')
        call.assert_not_called()

    def test_request_is_logged_before_dispatch_and_usage_is_reconciled(self):
        replies=iter([response(DECOMPOSE),response(plan()),response(supported(0)),
                      answer_response(ANSWER),answer_response(review())])
        with TemporaryDirectory() as temporary:
            out=Path(temporary)/'run'
            def dispatch(prompt):
                log=json.loads((out/'actual_chat_calls.json').read_text())
                self.assertEqual(log[-1]['status'],'running')
                self.assertEqual(log[-1]['prompt'],prompt)
                return next(replies)
            result,_=self.invoke(out,dispatch)
        self.assertEqual(result['api_summary']['reported_usage']['total_tokens'],75)
        self.assertEqual(result['api_summary']['usage_missing_calls'],[])

    def test_all_missing_stops_with_no_answer_generation_calls(self):
        stop=missing(assessment());stop['next_action'].update(type='stop',query=None,source=None)
        with TemporaryDirectory() as temporary:
            result,call=self.invoke(Path(temporary)/'run',[response(DECOMPOSE),response(plan()),response(stop)])
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['agent']['answer_summary']['answer_status'],'insufficient_evidence')
        self.assertEqual(result['agent']['answer_summary']['api_attempts'],0)
        self.assertIn('证据不足',result['answer'])
        self.assertEqual(call.call_count,3)

    def test_invalid_planning_keeps_failure_without_generating_a_rag_fallback(self):
        invalid=plan();invalid['requirements'][0]['question_quote']='A on another benchmark'
        with TemporaryDirectory() as temporary:
            out=Path(temporary)/'run'
            result,call=self.invoke(out,[response(DECOMPOSE),response(invalid),response(invalid)])
            self.assertFalse((out/'answer/answer.md').exists())
        self.assertEqual(result['status'],'failed')
        self.assertIsNone(result['answer'])
        self.assertEqual(call.call_count,3)

    def test_failed_final_review_is_reported_as_failure_with_a_boundary_answer(self):
        rejected=review()
        rejected['requirements'][0]['verdict']='fail'
        rejected['checks']['coverage']=False
        rejected['issues']=['回答仍有缺口。']
        replies=[response(DECOMPOSE),response(plan()),response(supported(0)),
                 answer_response(ANSWER),answer_response(rejected),
                 answer_response(ANSWER),answer_response(rejected)]
        with TemporaryDirectory() as temporary:
            result,call=self.invoke(Path(temporary)/'run',replies)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['agent']['answer_summary']['answer_status'],'review_failed')
        self.assertIn('未通过复核',result['answer'])
        self.assertEqual(call.call_count,7)

    def test_empty_agent_question_does_not_load_models_or_make_requests(self):
        with patch.object(api,'chat_completion') as call:
            self.assertIsNone(pipeline.main('   ',mode='agent'))
        pipeline.load_embedding_model.assert_not_called()
        call.assert_not_called()

    def test_truncated_decomposition_keeps_evidence_and_does_not_retry(self):
        partial=answer_response('partial');partial['finish_reason']='length'
        with TemporaryDirectory() as temporary,patch.object(api,'chat_completion',
                side_effect=api.IncompleteResponseError(partial)) as call:
            out=Path(temporary)/'run'
            with self.assertRaises(api.IncompleteResponseError):
                pipeline.main('Describe A.',mode='agent',output_dir=out)
            failed=json.loads((out/'result.json').read_text())
            log=json.loads((out/'actual_chat_calls.json').read_text())
            with self.assertRaises(ValueError):pipeline.main('Describe A.',mode='agent',output_dir=out)
        self.assertEqual(failed['status'],'failed')
        self.assertEqual(log[0]['response']['finish_reason'],'length')
        self.assertEqual(call.call_count,1)

    def test_cli_exposes_an_explicit_mode_and_reports_failed_runs(self):
        argv=['main.py','--mode','agent','--output-dir','some-run','Describe A.']
        with patch('sys.argv',argv),patch.object(pipeline,'main',return_value={'status':'failed'}):
            with self.assertRaises(SystemExit) as caught:pipeline.cli()
        self.assertEqual(caught.exception.code,1)


if __name__=='__main__':
    unittest.main()
