# 从终态记录复算请求/原文身份，准备人工审阅；不调用模型，不自动判答案语义正确。
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
from src.citation_validation import check_citations
from src.knowledge_base import load_knowledge_base


def main():
    live = OUT / 'live'
    summary = json.loads((live / 'summary.json').read_text())
    protocol = json.loads((OUT / 'frozen_protocol.json').read_text())
    assert len(summary['runs']) == protocol['planned_runs'], 'Wait for all planned runs to be terminal.'
    _, chunks, _ = load_knowledge_base(ROOT / 'data/processed', protocol['knowledge_base_version'])
    wire = json.loads((live / 'model_http.json').read_text())
    rows, all_calls, public, errors = [], [], [], []
    review = ['# 冻结新题：真实输出与引用，语义待人工核对\n']
    for row in summary['runs']:
        folder = live / row['id'] / row['arm']
        result = json.loads((folder / 'result.json').read_text()) if (folder / 'result.json').exists() else row
        calls = json.loads((folder / 'actual_chat_calls.json').read_text()) if (folder / 'actual_chat_calls.json').exists() else []
        all_calls.extend(calls)
        answer = result.get('answer') or ''
        passages = result.get('ledger', {}).get('citation_registry', [])
        cited = check_citations(answer, passages, require_citations=False)
        local = [p for p in passages if p.get('origin') != 'arxiv']
        local_ok = all(0 <= p['chunk_id'] < len(chunks) and all(p[k] == chunks[p['chunk_id']][k]
                       for k in ('text', 'source', 'page')) for p in local)
        external_ok = True
        read_path = folder / 'network/read/result.json'
        if read_path.exists():
            downloaded = json.loads(read_path.read_text())
            if downloaded['status'] == 'completed':
                pdf = Path(downloaded['pdf_path'])
                external_ok = hashlib.sha256(pdf.read_bytes()).hexdigest() == downloaded['trace']['response_sha256']
                documents = {p['evidence_id']: p for p in downloaded['documents']}
                for p in passages:
                    if p.get('origin') == 'arxiv':
                        external_ok &= (p['text'] == documents[p['document_evidence_id']]['text'][p['start']:p['end']]
                            and p['pdf_sha256'] == downloaded['trace']['response_sha256']
                            and p['arxiv_id'] == downloaded['arxiv_id'] and p['url'] == downloaded['pdf_url'])
        for path in (folder / 'network').glob('*/result.json'):
            record = json.loads(path.read_text())
            public.append({'id': row['id'], 'arm': row['arm'], 'tool': record['tool'],
                           'status': record['status'], 'trace': record['trace'], 'error': record.get('error')})
        if not local_ok or not external_ok:
            errors.append({'id': row['id'], 'arm': row['arm'], 'local_ok': local_ok, 'external_ok': external_ok})
        initial_path = folder / 'retrieval.json'
        initial = json.loads(initial_path.read_text()) if initial_path.exists() else {}
        answer_path = folder / 'network/answer_result.json'
        answer_record = json.loads(answer_path.read_text()) if answer_path.exists() else {}
        if not answer_record and (folder / 'answer/question.json').exists():
            answer_record = json.loads((folder / 'answer/question.json').read_text()).get('result', {})
        record = {**row, 'usage': {k: sum((c.get('response', {}).get('usage') or {}).get(k, 0) for c in calls)
                    for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
            'phases': dict(Counter(c['phase'] for c in calls)), 'citation_structure_passed': cited['structure_passed'],
            'cited_numbers': cited['cited_numbers'], 'local_registry_matches_kb': local_ok,
            'external_registry_matches_saved_pdf': external_ok, 'initial_ids': initial.get('selected_ids'),
            'answer_repair_attempted': answer_record.get('repair_attempted', False),
            'review_validation_errors': [r['review_error'] for r in answer_record.get('reviews', []) if 'review_error' in r],
            'initial_context_sha256': hashlib.sha256(initial.get('context', '').encode()).hexdigest(),
            'final_passage_count': len(passages), 'final_character_count': sum(len(p['text']) for p in passages)}
        rows.append(record)
        review += [f"\n## {row['id']} / {row['arm']} / {row['status']}\n", answer or str(result.get('error', row.get('error')))]
        for number in cited['cited_numbers']:
            passage = next(p for i, p in enumerate(passages, 1) if p.get('citation', i) == number)
            review += [f"\n引用[{number}] {passage['source']} p.{passage['page']} id={passage['chunk_id']}\n", passage['text']]
    totals = {k: sum(r['usage'][k] for r in rows) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    paired_context = {f'n{i:02d}': len({r['initial_context_sha256'] for r in rows
        if r['id'] == f'n{i:02d}' and r['arm'] in ('agent_off', 'agent_on')}) == 1 for i in range(1, 7)}
    result = {'planned_runs': protocol['planned_runs'], 'terminal_runs': len(rows),
        'actual_model_http_attempts': len(wire), 'logical_model_attempts': len(all_calls),
        'model_http_failures': sum(w['status'] != 'completed' for w in wire),
        'model_call_failures': sum(c['status'] != 'completed' for c in all_calls),
        'finish_reasons': dict(Counter(c.get('response', {}).get('finish_reason', 'missing') for c in all_calls)),
        'usage_missing_calls': sum(not c.get('response', {}).get('usage') for c in all_calls),
        'usage': totals, 'automatic_retries': 0, 'live_public_get_attempts': sum(r['trace']['http_attempts'] for r in public),
        'live_public_get_http_200': sum(r['trace'].get('http_status') == 200 for r in public),
        'gold_prefetch_public_gets': 2, 'public_records': public, 'registry_errors': errors,
        'paired_agent_initial_context_identical': paired_context, 'runs': rows,
        'semantic_correctness': 'requires_manual_review', 'old_scores_recomputed': False}
    (OUT / 'metrics_raw.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'answers_for_review.md').write_text('\n'.join(review) + '\n')
    print(json.dumps({k: result[k] for k in ('terminal_runs', 'actual_model_http_attempts', 'usage',
        'model_call_failures', 'live_public_get_attempts', 'registry_errors', 'paired_agent_initial_context_identical')}))


if __name__ == '__main__':
    main()
