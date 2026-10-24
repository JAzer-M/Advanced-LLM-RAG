"""离线汇总P2.5真实账本、检索与人工语义评分；不请求模型。"""
import json
from pathlib import Path
import statistics
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.metrics import (precision_at_k, recall_at_k, average_precision_at_k,
                                reciprocal_rank_at_k, overall_normalized_precision_at_k)
from src.citation_validation import check_citations


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def usage(calls):
    return {'attempts': len(calls), 'http_posts': sum(c.get('http_posts',0) for c in calls),
            'failed_attempts': sum(c['status']!='completed' for c in calls),
            'missing_usage_call_numbers': [c['number'] for c in calls if not c.get('response',{}).get('usage')],
            **{key: sum((c.get('response',{}).get('usage') or {}).get(key,0) for c in calls)
               for key in ('prompt_tokens','completion_tokens','total_tokens')}}


def retrieval(ids, gold, k):
    return {'k': k, 'selected_ids': ids[:k], 'gold_ids': gold,
            'precision': precision_at_k(ids,gold,k), 'recall': recall_at_k(ids,gold,k),
            'ap': average_precision_at_k(ids,gold,k), 'rr': reciprocal_rank_at_k(ids,gold,k)}


def main():
    questions = read(OUT/'questions_frozen.json')
    calls = read(OUT/'actual_chat_calls.json', [])
    review = read(OUT/'semantic_review.json', {})
    rows, pack = [], ['# P2.5 实际答案与冻结评分点\n']
    for q in questions:
        qid = q['id']; folder = OUT/'cases'/qid
        record = read(folder/'result.json', {})
        rag = read(folder/'rag.json', {})
        shared = read(folder/'shared.json', {})
        answer_input = read(folder/'answer/inputs.json', {})
        answer_record = read(folder/'answer'/f'{qid}.json', {})
        loop = read(folder/'loop'/f'{qid}.json', {})
        answer_result = answer_record.get('result', {})
        initial = [c for c in calls if c['question_id']==qid and c['stage']=='initial']
        rag_only = [c for c in calls if c['question_id']==qid and c['stage']=='rag_answer']
        agent_only = [c for c in calls if c['question_id']==qid and c['stage'].startswith('agent_')]
        rag_registry = rag.get('ledger',{}).get('citation_registry',[])
        agent_registry = answer_input.get('passages',[])
        loop_inputs = read(folder/'loop/inputs.json',{})
        final_collected = loop.get('evidence_after',loop_inputs.get(qid,{}).get('evidence',[]))
        row = {'id':qid, 'type':q['type'], 'run_status':record.get('status','not_run'),
               'shared_initial_usage':usage(initial), 'actual_usage':usage(initial+rag_only+agent_only),
               'initial_top10':retrieval(rag.get('selected_ids',[]),q['gold_chunk_ids_at_freeze'],10)}
        for arm, answer, registry, success, arm_calls, latency in [
                ('rag',rag.get('answer',''),rag_registry,rag.get('status')=='completed',initial+rag_only,record.get('rag_path_seconds',shared.get('rag_seconds'))),
                ('agent',answer_result.get('answer',''),agent_registry,
                 answer_record.get('status')=='completed' and answer_result.get('status')!='review_failed',initial+agent_only,record.get('agent_path_seconds'))]:
            ids = [c['chunk_id'] for c in registry]
            semantic = review.get(qid,{}).get(arm)
            if semantic is not None:
                assert len(semantic['points'])==len(q['reference_points']), (qid,arm,'point count')
                assert all(p in {'covered','partial','missing','wrong'} for p in semantic['points'])
                assert type(semantic['strict_pass']) is bool
                if semantic['strict_pass']:
                    assert success and all(p=='covered' for p in semantic['points']), (qid,arm,'invalid strict pass')
                    assert not semantic.get('citation_gaps') and not semantic.get('unsupported_claims')
                semantic['coverage'] = sum(p=='covered' for p in semantic['points'])/len(semantic['points'])
            row[arm] = {'execution_success':success, 'answer':answer, 'answer_status':answer_result.get('status') if arm=='agent' else rag.get('status'),
                        'path_attributed_usage':usage(arm_calls), 'path_seconds':latency,
                        'passage_count':len(registry), 'context_chars':sum(len(c['text']) for c in registry),
                        'context_gold_recall':len(set(ids)&set(q['gold_chunk_ids_at_freeze']))/len(q['gold_chunk_ids_at_freeze']) if q['gold_chunk_ids_at_freeze'] else None,
                        'citation_structure':check_citations(answer,registry,require_citations=q['type']!='unanswerable') if answer else None,
                        'semantic':semantic}
        row['agent'].update(tool_actions=loop.get('actions_executed',0), halt_reason=loop.get('halt_reason'),
                            loop_status=loop.get('status','not_run'), collected_passage_count=len(final_collected),
                            collected_gold_recall=len({c['chunk_id'] for c in final_collected}&set(q['gold_chunk_ids_at_freeze']))/len(q['gold_chunk_ids_at_freeze']) if q['gold_chunk_ids_at_freeze'] else None,
                            decision_error=loop.get('error'), answer_error=answer_record.get('error'),
                            assessment_statuses=[r['status'] for r in loop.get('final_assessment',{}).get('requirements',[])])
        # 这些只是同一追加顺序的前缀统计，不是独立K策略的对照。
        row['agent']['append_order_metrics']={str(k):retrieval([c['chunk_id'] for c in agent_registry],q['gold_chunk_ids_at_freeze'],k) for k in sorted({10,20,max(1,len(agent_registry))})}
        rows.append(row)
        pack += [f"## {qid} / {q['type']}\n",q['question']+'\n','冻结评分点：\n',
                 *[f"- {point}" for point in q['reference_points']], '\n固定RAG：\n',row['rag']['answer'] or '(无答案)',
                 '\nAgent：\n',row['agent']['answer'] or '(无答案)',
                 f"\nAgent阶段：{row['agent']['loop_status']} / {row['agent']['answer_status']}；停止：{row['agent']['halt_reason']}；错误：{row['agent']['decision_error'] or row['agent']['answer_error']}\n"]
    save(OUT/'case_metrics.json',rows)
    (OUT/'answers_for_review.md').write_text('\n'.join(pack)+'\n')
    actual = usage(calls)
    path_totals={arm:usage([c for c in calls if c['stage']=='initial' or (c['stage']=='rag_answer' if arm=='rag' else c['stage'].startswith('agent_'))]) for arm in ('rag','agent')}
    initial_usage=usage([c for c in calls if c['stage']=='initial'])
    assert path_totals['rag']['attempts']+path_totals['agent']['attempts']-initial_usage['attempts']==actual['attempts']
    assert path_totals['rag']['total_tokens']+path_totals['agent']['total_tokens']-initial_usage['total_tokens']==actual['total_tokens']
    scored = [r for r in rows if r['initial_top10']['gold_ids']]
    initial_metrics={name:sum(r['initial_top10'][field] for r in scored)/len(scored) for name,field in [('precision','precision'),('recall','recall'),('map','ap'),('mrr','rr')]}
    initial_metrics['normalized_precision']=overall_normalized_precision_at_k([(r['initial_top10']['selected_ids'],r['initial_top10']['gold_ids']) for r in scored],10)
    groups={}
    for label, subset in [('all',rows),('answerable',[r for r in rows if r['type']!='unanswerable']),
                           ('single_document',[r for r in rows if r['type']=='single_document']),
                           ('cross_document',[r for r in rows if r['type']=='cross_document']),
                           ('unanswerable',[r for r in rows if r['type']=='unanswerable'])]:
        groups[label]={}
        for arm in ('rag','agent'):
            reviewed=[r for r in subset if r[arm]['semantic'] is not None]
            data={'planned':len(subset),'reviewed':len(reviewed),'executed_successfully':sum(r[arm]['execution_success'] for r in subset),
                  'strict_pass_count':sum(r[arm]['semantic']['strict_pass'] for r in reviewed)}
            data['strict_pass_rate_planned']=data['strict_pass_count']/len(subset)
            data['strict_pass_rate_executed']=data['strict_pass_count']/data['executed_successfully'] if data['executed_successfully'] else None
            if reviewed:
                data.update(core_coverage_macro=sum(r[arm]['semantic']['coverage'] for r in reviewed)/len(subset),
                            covered_points=sum(sum(p=='covered' for p in r[arm]['semantic']['points']) for r in reviewed),
                            total_points=sum(len(r[arm]['semantic']['points']) for r in reviewed),
                            citation_gap_cases=sum(bool(r[arm]['semantic'].get('citation_gaps')) for r in reviewed),
                            unsupported_claim_cases=sum(bool(r[arm]['semantic'].get('unsupported_claims')) for r in reviewed),
                            citation_support_pass_cases=sum(r[arm]['semantic'].get('citation_support_pass',False) for r in reviewed),
                            appropriate_refusals=sum(r[arm]['semantic'].get('appropriate_refusal',False) for r in reviewed),
                            over_refusals=sum(r[arm]['semantic'].get('over_refusal',False) for r in reviewed))
            groups[label][arm]=data
    quality_complete=all(r[arm]['semantic'] is not None for r in rows for arm in ('rag','agent'))
    pairs={'agent_only_pass':[],'rag_only_pass':[],'both_pass':[],'neither_pass':[]}
    if quality_complete:
        for r in rows:
            a,b=r['agent']['semantic']['strict_pass'],r['rag']['semantic']['strict_pass']
            pairs['both_pass' if a and b else 'agent_only_pass' if a else 'rag_only_pass' if b else 'neither_pass'].append(r['id'])
    matched_success=[r for r in rows if r['rag']['execution_success'] and r['agent']['execution_success']]
    matched_costs={arm:{'cases':[r['id'] for r in matched_success],
                       'path_attributed_attempts':sum(r[arm]['path_attributed_usage']['attempts'] for r in matched_success),
                       'path_attributed_tokens':sum(r[arm]['path_attributed_usage']['total_tokens'] for r in matched_success),
                       'median_seconds':statistics.median(r[arm]['path_seconds'] for r in matched_success) if matched_success else None}
                   for arm in ('rag','agent')}
    timing={arm:{'measured_cases':sum(r[arm]['path_seconds'] is not None for r in rows),
                 'median_seconds':statistics.median(r[arm]['path_seconds'] for r in rows if r[arm]['path_seconds'] is not None),
                 'mean_seconds':statistics.mean(r[arm]['path_seconds'] for r in rows if r[arm]['path_seconds'] is not None)} for arm in ('rag','agent')}
    summary={'quality_complete':quality_complete,'actual_usage':actual,'shared_initial_usage':initial_usage,
             'path_attributed_usage':path_totals,'initial_top10_metrics':initial_metrics,'groups':groups,'strict_pass_pairs':pairs,
             'timing':timing,'matched_execution_success_costs':matched_costs,'agent_tool_actions':sum(r['agent']['tool_actions'] for r in rows),
             'rag_context_gold_recall_macro':statistics.mean(r['rag']['context_gold_recall'] or 0 for r in rows if r['type']!='unanswerable'),
             'agent_collected_gold_recall_macro':statistics.mean(r['agent']['collected_gold_recall'] or 0 for r in rows if r['type']!='unanswerable'),
             'scope':'12 same-corpus frozen new questions, one paired run, same assistant authored/reviewed; no independent/general significance claim.'}
    save(OUT/'summary.json',summary)
    print(json.dumps({'quality_complete':quality_complete,'actual':actual,'groups':groups,'pairs':pairs,'timing':timing},ensure_ascii=False))


if __name__ == '__main__':
    main()
