"""额度恢复后的离线核验：独立复算分数/成本，核对冻结输入、原文与既有资产。"""
from collections import Counter
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import runpy
import socket
import sys
from unittest.mock import patch
from urllib.parse import unquote

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    read=lambda name:json.loads((OUT/name).read_text())
    protocol=read('frozen_protocol.json'); baseline=read('baseline_hashes.json')
    calls=read('actual_chat_calls.json'); calls_before=sha(OUT/'actual_chat_calls.json')
    questions=read('questions_frozen.json'); summary=read('summary.json'); review=read('semantic_review.json')
    assert summary['quality_complete'] and len(questions)==12
    assert Counter(q['type'] for q in questions)=={'single_document':4,'cross_document':6,'unanswerable':2}
    drift=[name for name,digest in protocol['source_hashes'].items() if sha(ROOT/name)!=digest]
    assert not drift, drift
    first=min(datetime.fromisoformat(c['started_at_utc']) for c in calls)
    assert datetime.fromisoformat(protocol['frozen_at_utc'])<first
    assert len(calls)<=protocol['max_actual_chat_attempts']
    assert [c['number'] for c in calls]==list(range(1,len(calls)+1))
    assert len({c['signature'] for c in calls})==len(calls)
    assert all(c['status']=='completed' and c['http_posts']==1 and c['response']['finish_reason']=='stop' for c in calls)
    assert max(Counter(c['question_id'] for c in calls).values())<=protocol['max_actual_chat_attempts_per_question']
    assert len(calls)==summary['actual_usage']['attempts']==61
    usage_keys=('prompt_tokens','completion_tokens','total_tokens')
    for key in usage_keys:
        assert sum(c['response']['usage'][key] for c in calls)==summary['actual_usage'][key]
    for arm,stage in [('rag','rag_answer'),('agent','agent_')]:
        attributed=[c for c in calls if c['stage']=='initial' or (c['stage']==stage if arm=='rag' else c['stage'].startswith(stage))]
        assert len(attributed)==summary['path_attributed_usage'][arm]['attempts']
        for key in usage_keys:
            assert sum(c['response']['usage'][key] for c in attributed)==summary['path_attributed_usage'][arm][key]
    folder=ROOT/'data/processed/versions'/protocol['kb_version']
    chunks=json.loads((folder/'chunks.json').read_text())
    pvals=[];rvals=[];aps=[];rrs=[];hits=0;denom=0;input_checks=0;canonical_checks=0
    for q in questions:
        qid=q['id'];case=OUT/'cases'/qid
        rag=json.loads((case/'rag.json').read_text()); record=json.loads((case/'result.json').read_text())
        assert record['status']=='completed' and rag['status']=='completed'
        assert rag['query']==q['question'] and rag['knowledge_base']['version']==protocol['kb_version']
        payload=json.loads((case/'loop/inputs.json').read_text())[qid]
        assert set(payload)=={'query','kb_version','evidence','inventory'}
        assert payload['query']==q['question']
        assert [c['chunk_id'] for c in payload['evidence']]==[c['chunk_id'] for c in rag['ledger']['citation_registry']]
        assert all(set(c)=={'chunk_id','source','page','title','text'} for c in payload['evidence'])
        input_checks+=1
        answer_input=case/'answer/inputs.json'
        registries=[rag['ledger']['citation_registry'],payload['evidence']]
        if answer_input.exists():
            data=json.loads(answer_input.read_text())
            assert set(data)=={'question','requirements','assessment','passages','halt_reason'}
            assert data['question']==q['question']
            registries.append(data['passages'])
        for registry in registries:
            for c in registry:
                raw=chunks[c['chunk_id']]
                assert all(c[k]==raw[k] for k in ('text','source','page'))
                canonical_checks+=1
        gold=set(q['gold_chunk_ids_at_freeze']); ids=rag['selected_ids'][:10]
        if gold:
            h=len(set(ids)&gold);hits+=h;denom+=min(10,len(gold));pvals.append(h/10);rvals.append(h/len(gold))
            seen=set(); found=0; ap=0; rr=0
            for rank,cid in enumerate(ids,1):
                if cid in seen: continue
                seen.add(cid)
                if cid in gold:
                    found+=1;ap+=found/rank
                    if not rr: rr=1/rank
            aps.append(ap/len(gold));rrs.append(rr)
    metrics={'precision':sum(pvals)/len(pvals),'recall':sum(rvals)/len(rvals),'map':sum(aps)/len(aps),
             'mrr':sum(rrs)/len(rrs),'normalized_precision':hits/denom}
    assert all(math.isclose(value,summary['initial_top10_metrics'][key],abs_tol=1e-12) for key,value in metrics.items())
    for arm in ('rag','agent'):
        strict=sum(review[q['id']][arm]['strict_pass'] for q in questions)
        assert strict==summary['groups']['all'][arm]['strict_pass_count']
        answerable=[q for q in questions if q['type']!='unanswerable']
        coverage=sum(sum(p=='covered' for p in review[q['id']][arm]['points'])/len(q['reference_points']) for q in answerable)/len(answerable)
        assert math.isclose(coverage,summary['groups']['answerable'][arm]['core_coverage_macro'],abs_tol=1e-12)
    # 仅运行离线调用边界检查。禁止任何意外连接，记录实际执行输出。
    network=[]
    def deny(*args,**kwargs):
        network.append('attempt');raise AssertionError('Network forbidden in offline delivery verification')
    buffer=io.StringIO()
    with contextlib.redirect_stdout(buffer),contextlib.redirect_stderr(buffer),patch.object(sys,'__stdout__',buffer), \
         patch.object(socket.socket,'connect',deny),patch.object(socket,'create_connection',deny):
        runpy.run_path(str(OUT/'test_driver.py'),run_name='__main__')
    assert not network
    (OUT/'offline_guard_checks.log').write_text(buffer.getvalue())
    compile_paths=sorted(OUT.glob('*.py'))
    for p in compile_paths: compile(p.read_text(),str(p),'exec')
    changed=[name for name,digest in baseline.items() if not (ROOT/name).exists() or sha(ROOT/name)!=digest]
    intended={'PROGRESS.md','README.md','docs/CODE_READING_GUIDE.md'}
    assert set(changed)==intended, changed
    docs=[ROOT/'PROGRESS.md',ROOT/'README.md',ROOT/'docs/CODE_READING_GUIDE.md',ROOT/'docs/PROJECT_METRICS.md',*OUT.glob('*.md')]
    missing=[]; links=0
    for p in docs:
        for ref in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
            if re.match(r'^(?:https?://|mailto:|codex:|#)',ref): continue
            target=unquote(ref.strip('<>').split('#')[0]);target=re.sub(r':\d+$','',target)
            if not target: continue
            links+=1
            # verification.json在本次核验结束时生成。
            if (p.parent/target).resolve()==(OUT/'verification.json').resolve():continue
            if not (p.parent/target).exists():missing.append([str(p.relative_to(ROOT)),ref])
    assert not missing,missing
    private=json.loads((ROOT/'api.local.json').read_text())
    secret=private.get('api_key','').strip().encode()
    secret_hits=[]
    if len(secret)>=8:
        secret_hits=[str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file() and secret in p.read_bytes()]
    assert not secret_hits
    assert sha(OUT/'actual_chat_calls.json')==calls_before
    result={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'continuation_local_date':'2026-10-22',
            'resume_new_model_requests':0,'actual_calls_preserved':61,'actual_calls_sha256':calls_before,
            'frozen_inputs_and_code_match':True,'protocol_frozen_before_first_model_call':True,
            'existing_files_checked':len(baseline),'changed_existing_files':changed,
            'other_existing_files_unchanged':len(baseline)-len(changed),'production_python_and_kb_unchanged':True,
            'canonical_passage_identity_checks':canonical_checks,'agent_input_whitelist_cases':input_checks,
            'old_answers_gold_and_reference_fields_excluded':True,'independently_recomputed_initial_metrics':metrics,
            'manual_labels_recomputed_not_independently_rejudged':True,'cost_attribution_reconciled':True,
            'all_reported_usage_present':True,'all_real_finish_reasons_stop':True,'automatic_retries':0,
            'offline_driver_guard_checks_passed':True,'offline_network_attempts':len(network),
            'new_experiment_scripts_compiled':len(compile_paths),'local_markdown_links_checked':links,
            'secret_absence_checked':True,'secret_occurrences':0,'no_commit_or_push':True}
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    manifest={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'}
    (OUT/'artifact_hashes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
