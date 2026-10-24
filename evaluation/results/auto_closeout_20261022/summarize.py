"""只读真实记录与人工评分，复算三路径质量、路由、成本和检索；不调用API。"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT))
from evaluation import metrics


def read(path):return json.loads(path.read_text())


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def usage(rows):
    reported=[c.get('response',{}).get('usage') for c in rows]
    return {'attempts':len(rows),'http_posts':sum(c['http_posts'] for c in rows),
            'failed_attempts':sum(c['status']!='completed' for c in rows),
            'usage_missing_calls':[c['number'] for c,u in zip(rows,reported) if u is None],
            'reported_usage':{key:sum((u or {}).get(key,0) for u in reported)
                              for key in ('prompt_tokens','completion_tokens','total_tokens')}}


def timing(rows):
    return {'mean_seconds':statistics.mean(rows),'median_seconds':statistics.median(rows),
            'min_seconds':min(rows),'max_seconds':max(rows)} if rows else None


def main():
    qs=read(OUT/'questions_frozen.json');protocol=read(OUT/'frozen_protocol.json')
    references=read(OUT/'route_reference.json')
    assert {x['id'] for x in references}=={q['id'] for q in qs},'Review initial evidence before final Auto answers.'
    for ref in references:
        assert ref['initial_sha256']==sha(OUT/'cases'/ref['id']/'initial.json')
    frozen_changed=[p for p,h in protocol['source_hashes'].items() if sha(ROOT/p)!=h]
    assert not frozen_changed,frozen_changed
    manual=read(OUT/'manual_review.json');review={c['id']:c for c in manual['cases']}
    assert set(review)=={q['id'] for q in qs}
    calls=read(OUT/'actual_chat_calls.json')
    cases=[];answerable=[q for q in qs if q['gold_evidence']]
    for q in qs:
        folder=OUT/'cases'/q['id'];case=read(folder/'result.json')
        row={'id':q['id'],'type':q['type'],'arms':{}}
        for arm in ('rag','agent','auto'):
            result_path=folder/'rag.json' if arm=='rag' else folder/arm/'result.json'
            result=read(result_path) if result_path.exists() else {'status':'not_run'}
            checked=review[q['id']]['arms'][arm]
            assert checked['result_sha256']==sha(result_path)
            assert checked['answer_sha256']==hashlib.sha256((result.get('answer') or '').encode()).hexdigest()
            statuses=checked['required_statuses']
            assert len(statuses)==len(q['required_points'])
            assert set(statuses)<={'covered','partial','missing','wrong'}
            delivered=result.get('status')=='completed' and bool(result.get('answer'))
            assert delivered or 'covered' not in statuses,'Failed/no-delivery cases must remain zero.'
            strict=bool(delivered and all(s=='covered' for s in statuses) and checked['citations_supported']
                        and not checked['unsupported_or_wrong_claims'])
            context=None
            if arm=='rag':context=result.get('ledger',{}).get('citation_registry')
            elif (folder/arm/'answer/inputs.json').exists():context=read(folder/arm/'answer/inputs.json')['passages']
            context_stats=None
            if context is not None:
                ids=[c['chunk_id'] for c in context];gold=q['gold_chunk_ids_at_freeze']
                used_for_generation=(arm=='rag' or any(c['phase']=='answer' for c in
                                     read(folder/arm/'actual_chat_calls.json')))
                context_stats={'passage_count':len(context),'text_characters':sum(len(c['text']) for c in context),
                               'used_for_model_generation':used_for_generation,
                               'gold_recall_full_context':metrics.recall_at_k(ids,gold,len(ids)) if ids else None}
            row['arms'][arm]={'status':result['status'],'delivered':delivered,'strict_pass':strict,
                'required_statuses':statuses,'covered':statuses.count('covered'),'required_count':len(statuses),
                'path_seconds':case['arms'].get(arm,{}).get('path_seconds'),
                'route':result.get('routing',{}).get('route'),
                'tool_actions':result.get('agent',{}).get('actions_executed',0),
                'halt_reason':result.get('agent',{}).get('halt_reason'),
                'generation_context':context_stats,
                'correct_refusal':checked.get('correct_refusal',False),
                'error':result.get('error')}
        cases.append(row)
    quality={};costs={};latencies={}
    for arm in ('rag','agent','auto'):
        values=[c['arms'][arm] for c in cases]
        av=[c['arms'][arm] for c in cases if c['type']!='unanswerable']
        quality[arm]={'planned_questions':len(qs),'delivered':sum(v['delivered'] for v in values),
            'strict_pass':sum(v['strict_pass'] for v in values),
            'core_complete_questions':sum(v['delivered'] and v['covered']==v['required_count'] for v in values),
            'answerable_strict_pass':sum(v['strict_pass'] for v in av),
            'answerable_core_micro':{'covered':sum(v['covered'] for v in av),'total':sum(v['required_count'] for v in av)},
            'answerable_core_macro':statistics.mean(v['covered']/v['required_count'] for v in av),
            'correct_refusals':sum(v['correct_refusal'] for v in values),
            'tool_actions':sum(v['tool_actions'] for v in values)}
        costs[arm]=usage([c for c in calls if c['stage'] in ('initial',arm)])
        times=[v['path_seconds'] for v in values if v['path_seconds'] is not None]
        successful=[v['path_seconds'] for v in values if v['delivered'] and v['path_seconds'] is not None]
        latencies[arm]={'all_planned':timing(times),'delivered_subset':timing(successful),
                        'delivered_subset_size':len(successful)}
    shared=usage([c for c in calls if c['stage']=='initial']);actual=usage(calls)
    assert sum(v['attempts'] for v in costs.values())-2*shared['attempts']==actual['attempts']
    for key in ('prompt_tokens','completion_tokens','total_tokens'):
        assert sum(v['reported_usage'][key] for v in costs.values())-2*shared['reported_usage'][key]==actual['reported_usage'][key]
    retrieval=[]
    for q in answerable:
        ids=read(OUT/'cases'/q['id']/'initial.json')['selected_ids'];gold=q['gold_chunk_ids_at_freeze']
        retrieval.append((ids,gold))
    retrieved={'answerable_questions':len(retrieval),'k':10,
        'precision':statistics.mean(metrics.precision_at_k(ids,gold,10) for ids,gold in retrieval),
        'overall_normalized_precision':metrics.overall_normalized_precision_at_k(retrieval,10),
        'macro_recall':statistics.mean(metrics.recall_at_k(ids,gold,10) for ids,gold in retrieval),
        'MAP':metrics.mean_average_precision_at_k(retrieval,10),'MRR':metrics.mean_reciprocal_rank_at_k(retrieval,10)}
    routing=[]
    for ref in references:
        actual_route=next(c for c in cases if c['id']==ref['id'])['arms']['auto']['route']
        routing.append({'id':ref['id'],'expected':ref['expected_route'],'actual':actual_route,
                        'correct':actual_route==ref['expected_route'],
                        'reasonable_alternative':actual_route in ref.get('reasonable_alternatives',[])})
    guards=[]
    for q in qs:
        for arm in ('agent','auto'):
            folder=OUT/'cases'/q['id']/arm
            entries=read(folder/'actual_chat_calls.json')
            phases=Counter(c['phase'] for c in entries)
            loop_calls=read(folder/'loop/actual_chat_calls.json')
            guard={'id':q['id'],'arm':arm,'stage_attempts':dict(phases),
                   'decision_calls':len(loop_calls),'plan_calls':sum(c['phase']=='plan' for c in loop_calls),
                   'actions':next(c for c in cases if c['id']==q['id'])['arms'][arm]['tool_actions']}
            assert phases['decompose']==0 and phases['decision']<=6 and phases['answer']<=4
            assert len(entries)+len([c for c in calls if c['question_id']==q['id'] and c['stage']=='initial'])<=11
            assert guard['plan_calls']<=1 and guard['actions']<=3
            guards.append(guard)
    diagnostics={}
    groups={'common_delivered':[c for c in cases if all(c['arms'][a]['delivered'] for a in ('agent','auto'))],
            'direct_delivered':[c for c in cases if c['arms']['auto']['route']=='direct'
                                and all(c['arms'][a]['delivered'] for a in ('agent','auto'))]}
    for name,group in groups.items():
        ids=[c['id'] for c in group]
        group_cost={arm:usage([c for c in calls if c['question_id'] in ids and c['stage'] in ('initial',arm)])
                    for arm in ('rag','agent','auto')}
        diagnostics[name]={'question_ids':ids,'path_attributed_costs':group_cost,
                           'status':'Post-experiment diagnostic subset; not the planned denominator.'}
    summary={'scope':protocol['name'],'quality':quality,'path_attributed_costs':costs,
             'actual_deduplicated_cost':actual,'shared_initial_cost':shared,'latencies':latencies,
             'initial_retrieval_metrics':retrieved,
             'routing':{'counts':dict(Counter(r['actual'] for r in routing)),
                        'correct':sum(r['correct'] for r in routing),'planned':len(qs),'cases':routing},
             'automatic_retries':0,'finish_reasons':dict(Counter(c.get('response',{}).get('finish_reason') for c in calls)),
             'reported_models':dict(Counter(c.get('response',{}).get('reported_model') for c in calls)),
             'production_budget_and_no_duplicate_plan_checks':guards,'diagnostic_subsets':diagnostics,'cases':cases,
             'limits':['Same corpus and same assistant author/reviewer; not independent or blind.',
                       'One run per arm; shared actual initial retrieval, not three independent CLI end-to-end runs.',
                       'Small sample; no tuning or failure replacement after freeze; old measurements stay separate.',
                       'Path latency is warm sequential single-run time, not P95 or concurrency.']}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:summary[key] for key in ('quality','actual_deduplicated_cost','routing')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
