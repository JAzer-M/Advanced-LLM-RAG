"""只读检查修复边界、真实请求、原文身份、预算、旧资产与交接链接；不调用模型。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import py_compile
import re
import socket
import sys
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
import agent
from src import agent_answer


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def main():
    baseline = json.loads((OUT/'baseline_hashes.json').read_text())
    changed = [name for name,expected in baseline.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=expected]
    expected_changes = {'agent.py','src/agent_answer.py','PROGRESS.md','README.md',
                        'docs/PROJECT_METRICS.md','docs/CODE_READING_GUIDE.md'}
    assert set(changed) == expected_changes, changed
    protocol = json.loads((OUT/'frozen_protocol.json').read_text())
    for name,expected in protocol['source_hashes'].items():
        assert sha(ROOT/name) == expected, name
    calls = json.loads((OUT/'actual_chat_calls.json').read_text())
    assert len(calls)==15 and sum(c['http_posts'] for c in calls)==15
    assert all(c['status']=='completed' and c['response']['finish_reason']=='stop' for c in calls)
    assert all(c['response'].get('usage') for c in calls)
    assert protocol['frozen_at_utc'] < min(c['started_at_utc'] for c in calls)
    usage = {key:sum(c['response']['usage'][key] for c in calls)
             for key in ('prompt_tokens','completion_tokens','total_tokens')}
    assert usage=={'prompt_tokens':35697,'completion_tokens':3406,'total_tokens':39103}
    assert len({c['signature'] for c in calls})==len(calls)
    assert not any(field in c['prompt'] for c in calls
                   for field in ('"gold_evidence"','"reference_points"','"old_answer"'))
    chunks = json.loads((ROOT/'data/processed/versions/all-papers-8-20261020/chunks.json').read_text())
    canonical_checks, final_review_checks, tool_actions = 0, 0, 0
    for qid in ('b02','b03','b06'):
        base = OUT/'cases'/qid
        loop = json.loads((base/'loop'/f'{qid}.json').read_text())
        inputs = json.loads((base/'loop/inputs.json').read_text())[qid]
        assert set(inputs)=={'query','kb_version','evidence','inventory'}
        assert loop['status']=='completed' and loop['halt_reason']=='answer_ready'
        agent.validate_plan(loop['plan'],inputs['query'])
        for p in inputs['evidence']:
            assert all(p[k]==chunks[p['chunk_id']][k] for k in ('source','page','text'))
            canonical_checks += 1
        decisions = json.loads((base/'loop/actual_chat_calls.json').read_text())
        answers = json.loads((base/'answer/actual_chat_calls.json').read_text())
        assert len(decisions)<=6 and len(answers)<=4 and len(decisions)+len(answers)<=10
        assert sum(c['phase'].endswith('_repair') for c in decisions)<=1
        assert sum(c['phase']=='plan' for c in decisions)==1
        assert not any(c['phase']=='plan_repair' for c in decisions)
        assert loop['actions_executed']<=3
        tool_actions += loop['actions_executed']
        outer = [c for c in calls if c['question_id']==qid]
        assert len(outer)==len(decisions)+len(answers)
        for c in decisions+answers:
            matching = [o for o in outer if o['prompt']==c['prompt']]
            assert len(matching)==1 and c['response']==matching[0]['response']
        payload = json.loads((base/'answer/inputs.json').read_text())
        record = json.loads((base/'answer'/f'{qid}.json').read_text())
        result = record['result']
        assert result['status']=='review_passed'
        agent_answer.validate_review(result['reviews'][-1]['review'],payload,result['answer'])
        assert (base/'answer/answer.md').read_text().strip()==result['answer']
        final_review_checks += 1
    labels = json.loads((OUT/'semantic_review.json').read_text())
    assert sum(v['strict_pass'] for v in labels.values())==1
    assert sum(p['label']=='covered' for v in labels.values() for p in v['points'])==7
    for qid,row in labels.items():
        answer = (OUT/'cases'/qid/'answer/answer.md').read_text().strip()
        assert row['answer_sha256']==hashlib.sha256(answer.encode()).hexdigest()
    assert tool_actions==0
    assert 'Ran 217 tests' in (OUT/'all_tests_final.log').read_text()
    assert 'OFFLINE_NETWORK_ATTEMPTS 0' in (OUT/'all_tests_final.log').read_text()
    for name in ('agent.py','src/agent_answer.py','tests/test_agent_plan_repair.py'):
        assert sha(ROOT/name)==sha(OUT/'source_after'/name)
        py_compile.compile(str(ROOT/name),doraise=True)
    for p in OUT.glob('*.py'):
        py_compile.compile(str(p),doraise=True)
    docs = [ROOT/name for name in ('README.md','PROGRESS.md','docs/PROJECT_METRICS.md','docs/CODE_READING_GUIDE.md')]
    docs += [OUT/'report.md',OUT/'manual_review.md']
    link_count = 0
    for p in docs:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
            if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
            linked = (p.parent/target.split('#')[0]).resolve()
            assert linked.exists() or linked==OUT/'verification.json', (str(p),target)
            link_count += 1
    # 只检查配置中的凭证是否泄露；不打印配置值或凭证。
    secret = agent.api.load_settings().get('api_key','')
    if isinstance(secret,str) and len(secret)>=8:
        for p in OUT.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                assert secret.encode() not in p.read_bytes(), 'Configured credential appeared in artifact'
    verification = {'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'existing_files_checked':len(baseline),'changed_existing_files':changed,
        'other_existing_files_unchanged':len(baseline)-len(changed),
        'main_tools_retrieval_kb_and_all_previous_experiments_unchanged':True,
        'frozen_production_code_and_inputs_match':True,'protocol_frozen_before_first_request':True,
        'actual_new_requests':15,'http_posts':15,'usage':usage,'http_failures':0,'missing_usage':0,
        'all_finish_reasons_stop':True,'automatic_retries':0,'maximum_calls_unchanged':True,
        'one_shared_decision_repair_limit_preserved':True,'planning_delivery_and_review_successes':3,
        'frozen_strict_pass_count':1,'complete_core_points':'7/9',
        'three_real_plan_extractions_passed_first_attempt':True,
        'plan_repair_branch_verified_offline_not_triggered_in_this_real_run':True,
        'whitelisted_cases':3,'canonical_initial_passage_checks':canonical_checks,
        'final_model_reviews_locally_revalidated':final_review_checks,
        'manual_scores_hash_bound_not_independently_adjudicated':True,'tool_actions':0,
        'offline_tests_passed':217,'offline_network_attempts':0,'local_markdown_links_checked':link_count,
        'configured_secret_absence_checked':True,'no_main_integration_or_new_holdout':True,
        'no_commit_or_push':True,'actual_calls_sha256':sha(OUT/'actual_chat_calls.json')}
    save(OUT/'verification.json',verification)
    hashes = {str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.name!='artifact_hashes.json'}
    save(OUT/'artifact_hashes.json',hashes)
    print(json.dumps(verification,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    attempts=[]
    def blocked(*args,**kwargs):
        attempts.append(1)
        raise AssertionError('No network permitted during delivery verification')
    with patch.object(socket.socket,'connect',blocked),patch.object(socket,'create_connection',blocked):
        main()
    assert not attempts
