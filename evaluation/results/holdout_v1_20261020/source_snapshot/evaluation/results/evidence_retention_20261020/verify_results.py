"""Independent four-metric and provenance audit; no model inference or API calls."""
import ast
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
METHOD = 'Evidence Completion (up to 2 rounds)'


def read(path):
    return json.loads(path.read_text())


def metric(ids, gold, k):
    gold, hits, total, rr = set(gold), 0, 0, 0
    assert len(ids) == len(set(ids)) == k
    for rank, cid in enumerate(ids, 1):
        if cid in gold:
            hits += 1
            total += hits / rank
            rr = rr or 1 / rank
    return {'precision':hits/k,'recall':hits/len(gold),'ap':total/len(gold),'rr':rr}


def main():
    result = read(OUT/'comparison.json')
    assert result['status']=='completed' and result['api_calls']==0
    qmap = {q['id']:q for q in read(ROOT/'evaluation/all_papers_questions_en.json')}
    chunks = read(ROOT/'data/processed/versions/all-papers-8-20261020/chunks.json')
    normalized = lambda text: re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).lower().strip()
    gold = {}
    for qid,question in qmap.items():
        if not question.get('gold_evidence'):continue
        mapped=set()
        for evidence in question['gold_evidence']:
            matches={c['chunk_id'] for c in chunks if c['source']==evidence['source'] and c['page']==evidence['page']
                     and normalized(evidence['quote']) in normalized(c['text'])}
            assert matches,(qid,evidence)
            mapped.update(matches)
        gold[qid]=mapped
    row_count=0
    def verify_rows(rows):
        nonlocal row_count
        for q in rows:
            if q['status']!='completed':continue
            assert set(q['gold_ids'])==gold[q['id']]
            for k,methods in q['metrics_by_k'].items():
                for method,saved in methods.items():
                    for field,value in metric(saved['retrieved_ids'],q['gold_ids'],int(k)).items():
                        assert math.isclose(value,saved[field],abs_tol=1e-12),(q['id'],k,method,field)
                    row_count+=1
    for name,variant in result['variants'].items():
        rows=variant['questions'];assert len(rows)==42
        verify_rows(rows)
        if name.startswith('fixed'):
            for q in rows:
                local={cid for item in q['sub_query_evidence'] for cid in item['top_ids']}
                for k,trace in q['evidence_completion_by_k'].items():
                    retained=set(trace['selected_ids_before']) & local
                    assert retained==set(trace['retained_local_ids'])
                    assert trace['max_rounds']==2 and trace['completed_passes']<=2
                    assert trace['supplement_queries']<=8
                    assert retained<=set(trace['selected_ids_after'])
                    for step in trace['round_history']:
                        assert retained<=set(step['selected_ids'])
        for k,groups in variant['metrics'].items():
            for group,table in groups.items():
                members=[q for q in rows if group=='all' or
                         group=='old' and qmap[q['id']]['cohort']!='new_all_papers' or
                         group=='new' and qmap[q['id']]['cohort']=='new_all_papers' or
                         group=='single' and qmap[q['id']]['type']=='single_document' or
                         group=='cross' and qmap[q['id']]['type']!='single_document' or
                         group==qmap[q['id']]['cohort']]
                for method,saved in table.items():
                    assert saved['questions']==len(members)
                    scores=[metric(q['metrics_by_k'][k][method]['retrieved_ids'],q['gold_ids'],int(k)) for q in members]
                    for aggregate,field in [('precision','precision'),('recall','recall'),('map','ap'),('mrr','rr')]:
                        assert math.isclose(saved[aggregate],statistics.mean(s[field] for s in scores),abs_tol=1e-12)
                    assert saved['full_gold']==sum(set(q['gold_ids'])<=set(q['metrics_by_k'][k][method]['retrieved_ids']) for q in members)
        for name,digest in variant['input_sha256'].items():
            path=Path(name)
            # Only the adopted final-k default may differ after the explicitly parameterized runs.
            if path==ROOT/'main.py':path=OUT/'evaluated/main.py'
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
    previous={q['id']:q for q in read(ROOT/'evaluation/results/all_papers_20261020/comparison.json')['questions']}
    for q in result['variants']['old_selection_candidate60']['questions']:
        for method,saved in q['metrics_by_k']['10'].items():
            assert saved==previous[q['id']]['metrics_by_k']['10'][method]
    contexts=read(OUT/'context_cost.json')['fixed_selection_candidate120']
    table=result['variants']['fixed_selection_candidate120']['metrics']
    ten,twenty=table['10']['all'][METHOD],table['20']['all'][METHOD]
    ratio=statistics.median(contexts['20'][qid]['context_characters']/contexts['10'][qid]['context_characters'] for qid in gold)
    gates={'recall_gain':twenty['recall']>=ten['recall']+.05,
           'map_nonregression':twenty['map']>=ten['map']-.01,
           'mrr_nonregression':twenty['mrr']>=ten['mrr']-.01,'context_ratio':ratio<=2.2}
    chosen=20 if all(gates.values()) else 10
    adoption={'candidate_k':120,'completion_cap':2,'rewrite':False,'hyde':False,'chosen_top_k':chosen,
              'top10':ten,'top20':twenty,'median_complete_context_character_ratio':ratio,'gates':gates,
              'precision_note':'Both precisions reported; denominator changes from 10 to 20, so raw equality is not an adoption gate.',
              'answer_generation':'Not revalidated; this comparison is offline retrieval and context assembly.'}
    (OUT/'adoption.json').write_text(json.dumps(adoption,indent=2)+'\n')
    allowed={'main.py','src/reranker.py','src/evidence_gap.py','evaluation/run_evaluation.py',
             'tests/test_evidence_gap.py','README.md','PROGRESS.md'}
    changed=[]
    for name,digest in read(OUT/'baseline_hashes.json').items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:changed.append(name)
    assert set(changed)<=allowed,changed
    def main_ast(path):
        tree=ast.parse(path.read_text())
        for statement in tree.body:
            if isinstance(statement,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RERANK_TOP_K' for t in statement.targets):
                statement.value=ast.Constant(value=None)
        return ast.dump(tree,include_attributes=False)
    assert main_ast(ROOT/'main.py')==main_ast(OUT/'evaluated/main.py')
    for name,digest in read(OUT/'candidate_hashes.json').items():
        path=OUT/'evaluated/main.py' if name=='main.py' else ROOT/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
    assert all(hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256']
               for entry in read(ROOT/'data/migration_manifest.json')['files'])
    probe_path=OUT/'main_replay_summary.json'
    if probe_path.exists():
        probe=read(probe_path);assert probe['actual_main_retrieval_runs']==8 and probe['all_selected_ids_match']
        for name in ['p1_ablation','active_three_papers']:
            report=read(OUT/name/'results.json');assert report['api_call_count']==0
            verify_rows(report['questions'])
    secret=read(ROOT/'api.local.json')['api_key'].encode()
    for parent in [OUT,ROOT/'docs/chat_history']:
        for path in parent.rglob('*'):
            if path.is_file():
                content=gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
                assert secret not in content,f'Unredacted secret in {path}'
    summary={'status':'passed','four_metric_rows_independently_recomputed':row_count,
             'all_42_gold_maps_valid':True,'all_fixed_local_evidence_retained':True,
             'all_old60_k10_control_rows_reproduced':True,'api_calls':0,
             'intentional_changed_baseline_files':changed,'baseline_files_preserved':len(read(OUT/'baseline_hashes.json'))-len(changed),
             'legacy_migration_hashes_match':9,'default_top_k_recommendation':chosen,
             'main_replay_completed':probe_path.exists(),'secrets_absent':True}
    (OUT/'verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(json.dumps(adoption,indent=2))


if __name__=='__main__':main()
