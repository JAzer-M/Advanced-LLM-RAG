"""Two bounded rank-only probes; preserve every selected passage and all Gold labels."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from evaluation.metrics import mean_average_precision_at_k, mean_reciprocal_rank_at_k, recall_at_k
from src.reranker import select_evidence


def rank_selected(selected, global_ids, retrieval_ids, local_evidence, policy):
    if policy=='rrf_votes':
        votes = dict.fromkeys(selected,0.0)
        for ranked in [global_ids,retrieval_ids,*[item['top_ids'] for item in local_evidence]]:
            for rank,cid in enumerate(ranked,1):
                if cid in votes:
                    votes[cid] += 1/(60+rank)
        return sorted(selected,key=lambda cid:-votes[cid])
    ordered = [*retrieval_ids[:1],*[item['top_ids'][0] for item in local_evidence if item['top_ids']],*selected]
    return list(dict.fromkeys(cid for cid in ordered if cid in selected))


def load_cases(path):
    report=json.loads(path.read_text())
    assert report['status']=='completed'
    cases=[]
    for q in report['questions']:
        if q['status']!='completed': continue
        methods=q['metrics_by_k']['10']
        method='Decomposition + Hybrid + Reranker' if 'Decomposition + Hybrid + Reranker' in methods else 'Hybrid + Reranker + RRF Anchor'
        ids=methods[method]['retrieved_ids']
        stages=q['stage_ids'];global_ids=stages.get('decomposition_global',stages['global_reranker'])
        local=q['sub_query_evidence']
        replay=[c['chunk_id'] for c in select_evidence([{'chunk_id':cid} for cid in global_ids],local,10,stages['rrf'][:1])]
        assert replay==ids,(q['id'],replay,ids)
        case={'id':q['id'],'gold_ids':q['gold_ids'],'selected':ids,
              'global_ids':global_ids,'retrieval_ids':stages['rrf'],'local_evidence':local}
        case['rankings']={'baseline':ids,**{policy:rank_selected(ids,global_ids,stages['rrf'],local,policy)
                                         for policy in ('rrf_votes','anchor_first')}}
        assert all(len(ranked)==len(ids) and set(ranked)==set(ids) for ranked in case['rankings'].values())
        cases.append(case)
    return cases


def summary(cases,policy):
    pairs=[(c['rankings'][policy],c['gold_ids']) for c in cases]
    return {'questions':len(cases),'recall':sum(recall_at_k(r,g,10) for r,g in pairs)/len(pairs),
            'map':mean_average_precision_at_k(pairs,10),'mrr':mean_reciprocal_rank_at_k(pairs,10)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline-red',action='store_true');args=parser.parse_args()
    prior=ROOT/'evaluation/results/retrieval_optimization_20261019'
    old_core=load_cases(prior/'verified_english_60/results.json')
    if args.baseline_red:
        case=next(c for c in old_core if c['id']=='p1')
        first=min(case['selected'].index(g)+1 for g in case['gold_ids'] if g in case['selected'])
        print('Actual current select_evidence replay: p1 first Gold rank',first)
        assert first<=5,'Gold is present but late in the returned context.'
        raise SystemExit()
    cases={'new':load_cases(OUT/'retrieval/results.json'),'old_core':old_core,
           'old_validation':load_cases(prior/'validation_60/results.json'),
           'old_three_papers':load_cases(prior/'legacy_60/results.json')}
    question_types={q['id']:q['type'] for q in json.loads((ROOT/'evaluation/arxiv_next_questions_en.json').read_text())}
    cases['new_cross']=[c for c in cases['new'] if question_types[c['id']]=='cross_document']
    table={dataset:{policy:summary(values,policy) for policy in ('baseline','rrf_votes','anchor_first')}
           for dataset,values in cases.items()}
    gates={}
    for policy in ('rrf_votes','anchor_first'):
        new,base=table['new'][policy],table['new']['baseline']
        gate={'new_map_gain':new['map']-base['map'],'new_mrr_gain':new['mrr']-base['mrr']}
        gate['new_gain_passed']=gate['new_map_gain']>=.03 and gate['new_mrr_gain']>=.02
        gate['old_regressions_passed']=all(table[name][policy][metric]>=table[name]['baseline'][metric]-.01
            for name in ('old_core','old_validation','old_three_papers') for metric in ('map','mrr'))
        gate['cross_not_worse']=all(table['new_cross'][policy][metric]>=table['new_cross']['baseline'][metric]
                                    for metric in ('map','mrr'))
        gate['passed']=all(gate[key] for key in ('new_gain_passed','old_regressions_passed','cross_not_worse'))
        gates[policy]=gate
    eligible=[p for p in gates if gates[p]['passed']]
    decision=max(eligible,key=lambda p:(table['new'][p]['map'],table['new'][p]['mrr'])) if eligible else 'retain_baseline'
    result={'mode':__doc__,'metrics':table,'gates':gates,'decision':decision,'cases':cases,
            'api_calls':0,'unchanged_selected_sets':True}
    (OUT/'rank_probes.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'metrics':table,'gates':gates,'decision':decision},indent=2))
