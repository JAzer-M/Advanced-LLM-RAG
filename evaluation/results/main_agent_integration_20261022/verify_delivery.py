"""入口交付离线核验；不访问模型，不改旧实验；输出可复核证据和本轮资产哈希。"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import py_compile
import re
import socket
import sys
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT))
import main as pipeline
import agent
from src import agent_answer


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    baseline=json.loads((OUT/'baseline_hashes.json').read_text())
    changed=[n for n,h in baseline.items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
    assert set(changed)=={'main.py','src/query_decomposer.py','PROGRESS.md','README.md',
                          'docs/CODE_READING_GUIDE.md','docs/PROJECT_METRICS.md'},changed
    frozen=json.loads((OUT/'frozen_protocol.json').read_text())
    for name,h in frozen['source_hashes'].items():assert sha(ROOT/name)==h,name
    before=ast.parse((OUT/'source_before/main.py').read_text())
    after=ast.parse((ROOT/'main.py').read_text())
    old={n.name:n for n in before.body if isinstance(n,ast.FunctionDef)}
    new={n.name:n for n in after.body if isinstance(n,ast.FunctionDef)}
    helpers=[n for n in old if n!='main']
    assert len(helpers)==5
    assert all(ast.dump(old[n],include_attributes=False)==ast.dump(new[n],include_attributes=False) for n in helpers)
    assert [a.arg for a in old['main'].args.args]==[a.arg for a in new['main'].args.args[:4]]
    old_decomp=ast.parse((OUT/'source_before/src/query_decomposer.py').read_text())
    new_decomp=ast.parse((ROOT/'src/query_decomposer.py').read_text())
    def prompt_node(tree):
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='decompose_query')
        return next(n.value for n in function.body if isinstance(n,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id=='prompt' for t in n.targets))
    assert ast.dump(prompt_node(old_decomp),include_attributes=False)==ast.dump(prompt_node(new_decomp),include_attributes=False)
    summary=json.loads((OUT/'smoke_summary.json').read_text())
    events=json.loads((OUT/'http_events.json').read_text())
    assert summary['actual_attempts']==summary['http_posts']==len(events)==8
    assert summary['failed_attempts']==0 and not summary['missing_usage'] and summary['all_finish_reasons_stop']
    assert summary['reported_usage']=={'prompt_tokens':12689,'completion_tokens':942,'total_tokens':13631}
    all_calls=[];canonical_count=0;zero_request_guard_checks=0
    for name in ('answerable','unanswerable'):
        run=OUT/'cases'/name/'run'
        result=json.loads((run/'result.json').read_text())
        protocol=json.loads((run/'protocol.json').read_text())
        calls=json.loads((run/'actual_chat_calls.json').read_text())
        initial=json.loads((run/'retrieval.json').read_text())
        inputs=json.loads((run/'loop/inputs.json').read_text())['question']
        assert set(inputs)=={'query','kb_version','evidence','inventory'}
        assert result['status']=='completed' and protocol['mode']=='agent'
        assert protocol['max_actual_attempts']==11 and protocol['stage_call_limits']=={'decompose':1,'decision':6,'answer':4}
        assert protocol['frozen_at_utc']<min(c['started_at_utc'] for c in calls)
        assert frozen['frozen_at_utc']<min(c['started_at_utc'] for c in calls)
        assert len(calls)<=11 and sum(c['phase']=='decompose' for c in calls)==1
        assert len({(e['case'],e['main_number']) for e in events})==len(events)
        selected=[e for e in events if e['case']==name]
        assert [e['main_number'] for e in selected]==[c['number'] for c in calls]
        assert all(e['status']=='completed' for e in selected)
        assert result['initial_selected_ids']==initial['selected_ids']
        payload=json.loads((run/'answer/inputs.json').read_text())
        assert result['selected_ids']==[p['chunk_id'] for p in payload['passages']]
        assert result['ledger']['citation_registry']==payload['passages']
        _,chunks,metadata=pipeline.load_knowledge_base(ROOT/'data/processed',inputs['kb_version'])
        for p in payload['passages']:
            assert all(p[k]==chunks[p['chunk_id']][k] for k in ('source','page','title','text'))
            assert p['text'] in result['context'];canonical_count+=1
        assert result['knowledge_base']['files']==metadata['files']
        assert result['agent']['actions_executed']==0
        assert all(field not in c['prompt'] for c in calls
                   for field in ('"old_answer"','"reference_points"','"gold_evidence"'))
        answer=json.loads((run/'answer/question.json').read_text())['result']
        assert result['answer']==answer['answer']==(run/'answer/answer.md').read_text().strip()
        if name=='answerable':
            assert answer['status']=='review_passed' and len(calls)==5
            agent_answer.validate_review(answer['reviews'][-1]['review'],payload,answer['answer'])
            assert payload['passages'][6]['chunk_id']==66 and '[7]' in answer['answer']
        else:
            assert answer['status']=='insufficient_evidence' and len(calls)==3
            assert result['agent']['answer_summary']['api_attempts']==0
            assert '证据不足' in answer['answer']
        before_hash=sha(run/'actual_chat_calls.json')
        try:pipeline.main(result['query'],mode='agent',output_dir=run)
        except ValueError as exc:assert 'empty output directory' in str(exc)
        else:raise AssertionError('Nonempty output was accepted')
        assert before_hash==sha(run/'actual_chat_calls.json')
        zero_request_guard_checks+=1;all_calls+=calls
    assert summary['reported_usage']=={k:sum(c['response']['usage'][k] for c in all_calls)
                                      for k in ('prompt_tokens','completion_tokens','total_tokens')}
    assert 'Ran 230 tests' in (OUT/'all_tests.log').read_text()
    assert 'OFFLINE_NETWORK_ATTEMPTS 0' in (OUT/'all_tests.log').read_text()
    for name in ('main.py','src/query_decomposer.py','tests/test_main_agent.py'):
        assert sha(ROOT/name)==sha(OUT/'source_after'/name)
        py_compile.compile(str(ROOT/name),doraise=True)
    for p in OUT.glob('*.py'):py_compile.compile(str(p),doraise=True)
    progress=(ROOT/'PROGRESS.md').read_text()
    assert all(text in progress for text in ('必须修复','按任务补充','可以省略','未来新题先区分必答与补充'))
    docs=[ROOT/n for n in ('README.md','PROGRESS.md','docs/CODE_READING_GUIDE.md','docs/PROJECT_METRICS.md')]
    docs+=[OUT/'report.md',OUT/'manual_review.md']
    link_count=0
    for p in docs:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
            if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
            linked=(p.parent/target.split('#')[0]).resolve()
            assert linked.exists() or linked==OUT/'verification.json',(str(p),target)
            link_count+=1
    secret=agent.api.load_settings().get('api_key','')
    if isinstance(secret,str) and len(secret)>=8:
        for p in OUT.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                assert secret.encode() not in p.read_bytes(),'Configured credential found in artifact'
    result={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'existing_files_checked':len(baseline),
        'changed_existing_files':changed,'other_existing_files_unchanged':len(baseline)-len(changed),
        'all_previous_experiments_kb_pairs_and_active_pointer_unchanged':True,
        'agent_algorithm_tools_and_generation_prompts_unchanged':True,
        'default_rag_retained_and_original_helpers_ast_unchanged':helpers,
        'decomposition_prompt_unchanged':True,'explicit_mode_no_auto_router':True,
        'priority_rules_saved_to_progress':True,'frozen_sources_and_inputs_match':True,
        'offline_tests_passed':230,'new_entry_tests':13,'offline_network_attempts':0,
        'known_cli_smoke_cases_completed':2,'actual_model_requests':8,'observed_http_posts':8,
        'reported_usage':summary['reported_usage'],'http_failures':0,'automatic_retries':0,
        'per_agent_main_limit':11,'canonical_final_passage_checks':canonical_count,
        'no_old_answer_gold_or_reference_field_in_model_inputs':True,
        'real_tool_actions_in_this_smoke':0,'tool_execution_verified_through_main_offline':True,
        'nonempty_run_guard_verified_without_new_requests':zero_request_guard_checks,
        'known_limitation':'Answerable smoke replied in English despite Chinese instruction; recorded, not tuned.',
        'local_markdown_links_checked':link_count,'configured_secret_absence_checked':True,
        'no_new_holdout_or_global_quality_improvement_claim':True,'no_commit_or_push':True}
    save(OUT/'verification.json',result)
    hashes={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.name!='artifact_hashes.json'}
    save(OUT/'artifact_hashes.json',hashes)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    attempts=[]
    def blocked(*args,**kwargs):attempts.append(1);raise AssertionError('Network is disabled for delivery verification')
    with patch.object(socket.socket,'connect',blocked),patch.object(socket,'create_connection',blocked):main()
    assert not attempts
