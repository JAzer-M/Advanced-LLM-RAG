# P3.2真实main闭环：只替换HTTP/模型及CPU资源，保留工具解析、来源核对、引用和回答复核。
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import pymupdf

import agent
import main as pipeline
from src import arxiv_evidence, arxiv_tools, api_llm as api
import test_main_agent as fixtures
from test_agent_answer import response, review
from test_agent_step1 import assessment, missing
from test_arxiv_tools import http_response


IDENTITY = '2312.00752v2'
QUERY = 'Describe Mamba.'
QUOTE = 'five times the inference throughput'
ANSWER = 'Mamba报告五倍的推理吞吐量。[2]'
FEED = f'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>http://arxiv.org/abs/{IDENTITY}</id><title>Mamba: A fixture primary paper</title>
<author><name>Fixture Author</name></author><summary>METADATA_ONLY_SENTINEL</summary>
<published>2023-12-01</published><updated>2024-05-31</updated></entry></feed>'''.encode()


def paper_pdf():
    with pymupdf.open() as pdf:
        pdf.set_metadata({'title': 'Mamba Fixture Paper'})
        pdf.new_page().insert_text((72, 72), 'Mamba reports five times the inference throughput.')
        return pdf.tobytes()


def plan(subject='Mamba'):
    return {'requirements': [{'id': 'r1', 'subject': subject, 'question_quote': f'Describe {subject}'}]}


def stop(subject='Mamba'):
    value = missing(assessment())
    value['requirements'][0].update(reason=f'Primary {subject} paper absent locally.', gap=f'{subject}原文缺失。')
    value['next_action'].update(type='stop', query=None, source=None, reason='Primary source absent.')
    return value


def route():
    return {'route': 'arxiv', 'requirement_id': 'r1', 'paper_title': 'Mamba: A fixture primary paper',
            'reason': 'Mamba原论文不在本地目录。'}


def choice():
    return {'arxiv_id': IDENTITY, 'two_columns': False, 'reason': '返回列表中的Mamba原论文。'}


def supported_external():
    value = assessment()
    value['requirements'][0].update(status='supported', evidence=[{'chunk_id': 3, 'quote': QUOTE}],
        supported_part='Mamba报告五倍的推理吞吐量。', reason='New original PDF passage establishes it.', gap='')
    return value


def reviewed():
    value = review(ANSWER)
    value['requirements'][0]['citations'] = [{'number': 2, 'quote': QUOTE}]
    return value


class MainArxivIntegrationTests(unittest.TestCase):
    def setUp(self):
        fixtures.MainAgentTests.setUp(self)
        model = SimpleNamespace(predict=lambda pairs: [1.0] * len(pairs))
        self.stack.enter_context(patch.object(pipeline, 'CrossEncoder', return_value=model))
        self.stack.enter_context(patch.object(arxiv_tools, '_request_state', {'last_started': None}))
        self.stack.enter_context(patch.object(arxiv_tools.time, 'sleep'))

    def replies(self):
        return [fixtures.DECOMPOSE, plan(), stop(), route(), choice(), supported_external(), ANSWER, reviewed()]

    def http_replies(self, feed=FEED):
        return [http_response(feed, 'https://export.arxiv.org/api/query'),
                http_response(paper_pdf(), f'https://arxiv.org/pdf/{IDENTITY}')]

    def invoke(self, output, replies=None, http=None, mode='agent', query=QUERY, allow_network=True):
        with patch.object(api, 'chat_completion', side_effect=[response(r) for r in (replies or self.replies())]) as call, \
                patch.object(arxiv_tools, 'urlopen', side_effect=http or self.http_replies()) as network:
            result = pipeline.main(query, mode=mode, output_dir=output, allow_network=allow_network)
        return result, call, network

    def test_actual_main_reads_primary_pdf_and_delivers_reviewed_answer_with_external_source(self):
        before = deepcopy(self.fixture['chunks'])
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / 'run'
            result, call, network = self.invoke(out)
            payload = json.loads((out / 'network/inputs.json').read_text())
            protocol = json.loads((out / 'protocol.json').read_text())
            extraction = json.loads((out / 'network/read/result.json').read_text())
            external = json.loads((out / 'network/external_registry.json').read_text())
            self.assertFalse((out / 'answer').exists())
        self.assertEqual(result['status'], 'completed', result.get('error'))
        self.assertEqual(result['answer_strategy'], 'arxiv_evidence_reviewed')
        self.assertIn(ANSWER, result['answer'])
        self.assertIn(f'https://arxiv.org/pdf/{IDENTITY}', result['answer'])
        self.assertEqual(result['network']['answer_status'], 'review_passed')
        self.assertEqual(protocol['max_actual_attempts'], 14)
        self.assertEqual(protocol['stage_call_limits']['network'], 3)
        self.assertEqual(call.call_count, 8)
        self.assertEqual(network.call_count, 2)
        self.assertIn('search_query=ti%3A%22Mamba%3A+A+fixture+primary+paper%22',
                      network.call_args_list[0].args[0].full_url)
        self.assertNotIn('METADATA_ONLY_SENTINEL', json.dumps(payload))
        self.assertEqual(self.fixture['chunks'], before)
        source = external[0]
        self.assertEqual(source['origin'], 'arxiv')
        self.assertGreaterEqual(source['chunk_id'], len(self.fixture['chunks']))
        self.assertEqual(source['text'], extraction['documents'][0]['text'][source['start']:source['end']])
        self.assertEqual(payload['passages'][1]['citation'], 2)
        self.assertEqual(result['selected_ids'], [0, 3])

    def test_default_offline_agent_keeps_original_refusal_and_never_calls_network(self):
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', self.replies()[:3], allow_network=False)
        self.assertEqual(result['status'], 'completed')
        self.assertIn('证据不足', result['answer'])
        self.assertEqual(call.call_count, 3)
        network.assert_not_called()

    def test_ready_local_evidence_has_no_extra_route_call_even_with_network_enabled(self):
        from test_agent_feedback import supported
        from test_agent_answer import ANSWER as local_answer, review as local_review
        replies = [fixtures.DECOMPOSE, plan('A'), supported(0), local_answer, local_review()]
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', replies, query='Describe A.')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(call.call_count, 5)
        network.assert_not_called()

    def test_known_local_primary_source_is_not_replaced_by_web_retrieval(self):
        for passage in self.fixture['chunks']:
            passage['title'] = 'Local Method'
        replies = [fixtures.DECOMPOSE, plan('Local Method'), stop('Local Method')]
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', replies, query='Describe Local Method.')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['network']['status'], 'skipped')
        self.assertEqual(call.call_count, 3)
        network.assert_not_called()

    def test_router_can_decline_an_ambiguous_primary_paper_without_get_requests(self):
        decline = {'route': 'local_only', 'requirement_id': None, 'paper_title': None, 'reason': '原论文身份不明。'}
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', self.replies()[:3] + [decline])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(call.call_count, 4)
        network.assert_not_called()

    def test_empty_search_produces_explicit_insufficient_evidence_without_pdf_or_answer_calls(self):
        feed = b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', self.replies()[:4], self.http_replies(feed))
        self.assertEqual(result['network']['status'], 'no_evidence')
        self.assertIn('证据不足', result['answer'])
        self.assertEqual(call.call_count, 4)
        self.assertEqual(network.call_count, 1)

    def test_invented_version_is_rejected_before_pdf_download(self):
        replies = self.replies()[:5]
        replies[4] = {**choice(), 'arxiv_id': '2312.00752v99'}
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', replies)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('actual returned', result['error'])
        self.assertEqual(network.call_count, 1)
        self.assertEqual(call.call_count, 5)

    def test_only_followup_candidates_can_be_declined_without_more_searches_or_pdf(self):
        decline = {'arxiv_id': None, 'two_columns': True, 'reason': '返回的候选均为后续论文。'}
        feed = FEED.replace(b'Mamba: A fixture primary paper', b'Mamba Followup: A comparison')
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / 'run'
            result, call, network = self.invoke(out, self.replies()[:4] + [decline], self.http_replies(feed))
            self.assertFalse((out / 'network/read').exists())
        self.assertEqual(result['network']['status'], 'no_evidence')
        self.assertIn('证据不足', result['answer'])
        self.assertEqual(call.call_count, 5)
        self.assertEqual(network.call_count, 1)

    def test_wrong_primary_title_is_rejected_before_pdf_download(self):
        with TemporaryDirectory() as temporary:
            result, _, network = self.invoke(Path(temporary) / 'run', self.replies()[:5],
                self.http_replies(FEED.replace(b'Mamba: A fixture primary paper', b'Other Model: A fixture paper')))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(network.call_count, 1)

    def test_http_failure_remains_failed_with_one_attempt_and_saved_error(self):
        error = HTTPError('https://export.arxiv.org/api/query', 503, 'unavailable', {}, None)
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / 'run'
            result, call, network = self.invoke(out, self.replies()[:4], [error])
            self.assertEqual(json.loads((out / 'network/search/result.json').read_text())['status'], 'failed')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(network.call_count, 1)
        self.assertEqual(call.call_count, 4)

    def test_auto_network_failure_keeps_visible_degraded_initial_answer(self):
        probe = '当前证据不足，无法回答。[1]'
        replies = [fixtures.DECOMPOSE, probe, plan(), stop(), route()]
        error = HTTPError('https://export.arxiv.org/api/query', 503, 'unavailable', {}, None)
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / 'run'
            result, call, network = self.invoke(out, replies, [error], mode='auto')
            self.assertEqual(json.loads((out / 'protocol.json').read_text())['max_actual_attempts'], 16)
        self.assertEqual(result['status'], 'degraded')
        self.assertIn('补查未完成', result['answer'])
        self.assertEqual(network.call_count, 1)
        self.assertEqual(call.call_count, 5)

    def test_modified_extracted_text_is_rejected_against_saved_pdf(self):
        original = arxiv_tools.read_arxiv_paper
        def tamper(*args, **kwargs):
            record = original(*args, **kwargs)
            record['documents'][0]['text'] += ' invented result'
            return record
        with TemporaryDirectory() as temporary, patch.object(arxiv_tools, 'read_arxiv_paper', side_effect=tamper):
            result, call, network = self.invoke(Path(temporary) / 'run', self.replies()[:5])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('does not match', result['error'])
        self.assertEqual(call.call_count, 5)
        self.assertEqual(network.call_count, 2)

    def test_reviewer_fabricated_source_quote_never_becomes_a_successful_answer(self):
        bad = reviewed()
        bad['requirements'][0]['citations'][0]['quote'] = 'invented original text'
        replies = self.replies()[:7] + [bad, ANSWER, bad]
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / 'run'
            result, call, network = self.invoke(out, replies)
            self.assertFalse((out / 'network/answer.md').exists())
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(call.call_count, 10)
        self.assertEqual(network.call_count, 2)

    def test_fixed_rag_cannot_silently_enable_arxiv_and_cli_passes_explicit_flag(self):
        with self.assertRaisesRegex(ValueError, 'requires mode'):
            pipeline.main(QUERY, mode='rag', allow_network=True)
        with patch('sys.argv', ['main.py', QUERY, '--allow-network']), patch.object(pipeline, 'main', return_value={}) as entry:
            pipeline.cli()
        self.assertTrue(entry.call_args.kwargs['allow_network'])

    def test_unbound_requirement_or_title_is_rejected_before_any_get(self):
        for changed in ({'requirement_id': 'r99'}, {'paper_title': 'Other Model'}, {'paper_title': ''}):
            with self.subTest(changed=changed), TemporaryDirectory() as temporary:
                replies = self.replies()[:3] + [{**route(), **changed}]
                result, call, network = self.invoke(Path(temporary) / 'run', replies)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(call.call_count, 4)
                network.assert_not_called()

    def test_metadata_abstract_cannot_be_cited_as_pdf_evidence(self):
        bad = supported_external()
        bad['requirements'][0]['evidence'][0]['quote'] = 'METADATA_ONLY_SENTINEL'
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', self.replies()[:5] + [bad])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Quoted text', result['error'])
        self.assertEqual(call.call_count, 6)
        self.assertEqual(network.call_count, 2)

    def test_external_decision_budget_stops_before_a_second_model_decision_or_pdf(self):
        with TemporaryDirectory() as temporary, patch.object(arxiv_evidence, 'MAX_NETWORK_DECISIONS', 1):
            result, call, network = self.invoke(Path(temporary) / 'run', self.replies()[:4])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('budget exhausted', result['error'])
        self.assertEqual(call.call_count, 4)
        self.assertEqual(network.call_count, 1)

    def test_reading_a_pdf_without_support_still_produces_explicit_insufficient_evidence(self):
        unsupported = stop()
        unsupported['requirements'][0]['gap'] = 'Mamba所问的事实尚未由原文建立。'
        with TemporaryDirectory() as temporary:
            result, call, network = self.invoke(Path(temporary) / 'run', self.replies()[:5] + [unsupported])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['network']['answer_status'], 'insufficient_evidence')
        self.assertIn('证据不足', result['answer'])
        self.assertEqual(call.call_count, 6)
        self.assertEqual(network.call_count, 2)


class ExternalPassageBudgetTests(unittest.TestCase):
    def test_selected_windows_preserve_original_offsets_and_all_local_evidence(self):
        document = {'source': f'{IDENTITY}.pdf', 'title': 'Mamba', 'page': 1, 'section': 'Fixture',
            'text': 'Mamba reports measurable throughput. ' * 4000, 'arxiv_id': IDENTITY,
            'url': f'https://arxiv.org/pdf/{IDENTITY}', 'pdf_sha256': 'fixture',
            'evidence_id': f'arxiv:{IDENTITY}:document:0'}
        resources = {'chunks': [{}, {}, {}], 'reranker_model': SimpleNamespace(predict=lambda pairs: [1.0] * len(pairs))}
        for local in ([{'chunk_id': i, 'text': 'Local original.'} for i in range(31)],
                      [{'chunk_id': 0, 'text': 'x' * (agent.MAX_FEEDBACK_CHARS - 400)}]):
            with self.subTest(local_count=len(local)):
                before = deepcopy(local)
                selected, trace = arxiv_evidence.select_passages({'documents': [document]}, 'Mamba throughput', resources, local)
                self.assertEqual(local, before)
                self.assertLessEqual(trace['reranked_candidates'], 120)
                self.assertLessEqual(len(selected), 6)
                self.assertLessEqual(len(selected) + len(local), agent.MAX_FEEDBACK_PASSAGES)
                self.assertLessEqual(sum(len(p['text']) for p in [*local, *selected]), agent.MAX_FEEDBACK_CHARS)
                for passage in selected:
                    self.assertEqual(passage['text'], document['text'][passage['start']:passage['end']])
                    self.assertEqual(passage['origin'], 'arxiv')
                    self.assertGreaterEqual(passage['chunk_id'], len(resources['chunks']))


if __name__ == '__main__':
    unittest.main()
