"""Check frozen labels, metric calculations, unchanged rankings and bounded API use."""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from evaluation.metrics import (precision_at_k,recall_at_k,average_precision_at_k,
    reciprocal_rank_at_k,mean_average_precision_at_k,mean_reciprocal_rank_at_k)

read=lambda p:json.loads(p.read_text())
protocol=read(OUT/'protocol.json')
questions=read(ROOT/protocol['question_file'])
assert hashlib.sha256((ROOT/protocol['question_file']).read_bytes()).hexdigest()==protocol['question_sha256']
assert len(questions)==12 and len({q['id'] for q in questions})==12
report=read(OUT/'retrieval/results.json')
assert report['status']=='completed' and report['inputs_unchanged'] and report['api_call_count']==0
valid=[q for q in report['questions'] if q['status']=='completed']
assert len(valid)==10
assert {q['id'] for q in report['questions'] if q['status']=='skipped_no_gold'}=={'n11','n12'}
rows=0
for name,summary in report['metrics']['10'].items():
    pairs=[]
    for q in valid:
        m=q['metrics_by_k']['10'][name];ids,gold=m['retrieved_ids'],q['gold_ids']
        assert len(ids)==len(set(ids))<=10
        for metric,fn in [('precision',precision_at_k),('recall',recall_at_k),
                          ('ap',average_precision_at_k),('rr',reciprocal_rank_at_k)]:
            assert math.isclose(m[metric],fn(ids,gold,10),abs_tol=1e-12)
        pairs.append((ids,gold));rows+=1
    expected={'questions':10,'precision':sum(precision_at_k(r,g,10) for r,g in pairs)/10,
              'recall':sum(recall_at_k(r,g,10) for r,g in pairs)/10,
              'map':mean_average_precision_at_k(pairs,10),'mrr':mean_reciprocal_rank_at_k(pairs,10)}
    assert all(math.isclose(summary[k],v,abs_tol=1e-12) for k,v in expected.items())
probes=read(OUT/'rank_probes.json')
assert probes['decision']=='retain_baseline' and probes['api_calls']==0
assert len(probes['gates'])==2 and not any(g['passed'] for g in probes['gates'].values())
for dataset,cases in probes['cases'].items():
    for policy in ('baseline','rrf_votes','anchor_first'):
        pairs=[]
        for c in cases:
            ids=c['rankings'][policy]
            assert set(ids)==set(c['selected']) and len(ids)==len(c['selected'])
            pairs.append((ids,c['gold_ids']))
        summary=probes['metrics'][dataset][policy]
        assert math.isclose(summary['map'],mean_average_precision_at_k(pairs,10),abs_tol=1e-12)
        assert math.isclose(summary['mrr'],mean_reciprocal_rank_at_k(pairs,10),abs_tol=1e-12)
baseline=read(OUT/'baseline_hashes.json')
changed=[name for name,sha in baseline.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
assert changed==['main.py'],changed
old_ast=ast.parse((OUT/'code_baseline/main.py').read_text())
new_ast=ast.parse((ROOT/'main.py').read_text())
without_context=lambda tree:[ast.dump(n,include_attributes=False) for n in tree.body
    if not (isinstance(n,ast.FunctionDef) and n.name=='build_context')]
assert without_context(old_ast)==without_context(new_ast)
def context_function(tree):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_context')
    namespace={}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<context audit>','exec'),namespace)
    return namespace['build_context']
old_context,new_context=context_function(old_ast),context_function(new_ast)
old_chunks=read(ROOT/'data/processed/versions/semantic-mac-20261019/chunks.json')
new_chunks=read(ROOT/'data/processed/versions/arxiv-pilot-5-20261019/chunks.json')
assert all(old_context([c])==new_context([c]) for c in old_chunks)
assert all(new_context([c]).replace(f"Title: {c['title']}\n",'',1)==old_context([c]) for c in new_chunks)
context_check={'old_contexts_identical':len(old_chunks),'new_contexts_only_add_existing_title':len(new_chunks),
               'all_other_main_ast_nodes_identical':True}
(OUT/'context_equivalence.json').write_text(json.dumps(context_check,indent=2)+'\n')
decomposition=read(OUT/'decomposition_calls.json')
generation=[read(p) for p in sorted((OUT/'grounding').glob('*.json'))]
followup=[read(p) for p in sorted((OUT/'grounding_metadata').glob('*.json'))]
assert len(decomposition)==10 and len(generation)==12 and len(followup)==2
assert all(q['status']=='completed' for q in generation+followup)
by_q={q['id']:q for q in questions}
for call in decomposition:
    assert all(e['quote'] not in call['prompt'] for e in by_q[call['question_id']]['gold_evidence'])
for replay in followup:
    parent=read(ROOT/replay['parent']);expected=parent['prompt']
    for i,c in enumerate(parent['registry'],1):
        header=f"[{i}] {c['source']}, PDF p.{c['page']}\n"
        expected=expected.replace(header,header+f"Title: {c['title']}\n",1)
    assert replay['prompt']==expected
    assert all(replay[k]==parent[k] for k in ('query','registry','source_ids','condition'))
responses=[c['response'] for c in decomposition+generation+followup]
assert all(c['finish_reason']=='stop' for c in responses)
usage={k:sum(c['usage'][k] for c in responses) for k in ('prompt_tokens','completion_tokens','total_tokens')}
assert 'Ran 50 tests' in (OUT/'tests_final.log').read_text() and '\nOK' in (OUT/'tests_final.log').read_text()
secret=read(ROOT/'api.local.json')['api_key'].encode()
assert secret and all(secret not in p.read_bytes() for p in OUT.rglob('*') if p.is_file())
verification={'status':'passed','primary_metric_rows_recomputed':rows,'unique_rank_probe_cases':26,
    'rank_candidates':2,'rank_decision':'retain_baseline','baseline_files_preserved':len(baseline)-1,
    'intentional_production_change':'main.build_context: existing title metadata only',
    'other_main_code_and_retrieval_functions_unchanged':True,'context_equivalence':context_check,
    'api_calls':{'decomposition':10,'initial_generation':12,'metadata_followup':2,'total':24},
    'usage':usage,'all_finish_reason_stop':True,'tests':50,'configured_key_absent':True,
    'active_kb':read(ROOT/'data/processed/active_kb.json')['version']}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps(verification,indent=2))
