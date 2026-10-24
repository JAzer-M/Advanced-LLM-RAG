"""最终只读核验：旧资产、各阶段源码、当前源码、真实/缓存费用、原文身份和链接。"""
import ast
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]


def read(path):return json.loads(path.read_text())


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target=OUT/'verification.json';target.write_text('{"status":"checking"}\n')
    before=read(OUT/'baseline_hashes.json')
    deleted=[p for p in before if not (ROOT/p).is_file()]
    changed=[p for p,h in before.items() if (ROOT/p).is_file() and sha(ROOT/p)!=h]
    expected={'agent.py','main.py','src/agent_answer.py','src/citation_validation.py',
              'tests/test_main_auto.py','tests/test_agent_scope.py','README.md','PROGRESS.md',
              'docs/PROJECT_METRICS.md','docs/CODE_READING_GUIDE.md'}
    assert not deleted and set(changed)==expected,(deleted,changed)
    version_checks=[]
    for phase in ('.','followup','final','scoped_inputs'):
        folder=OUT/phase;protocol=read(folder/'frozen_protocol.json')
        for name,digest in protocol['source_hashes'].items():
            snapshot=folder/'source_after'/name
            actual=snapshot if snapshot.exists() else ROOT/name
            assert sha(actual)==digest,(phase,name)
        version_checks.append({'phase':phase,'frozen_files_verified':len(protocol['source_hashes'])})
    latest=read(OUT/'scoped_inputs/frozen_protocol.json')
    assert all(sha(ROOT/p)==h for p,h in latest['source_hashes'].items())
    functions=lambda text:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    old_main=functions((OUT/'source_before/main.py').read_text());new_main=functions((ROOT/'main.py').read_text())
    unchanged=[n for n in old_main if old_main[n]==new_main.get(n)]
    assert '_run_pipeline' in unchanged and 'build_prompt' in unchanged and len(unchanged)==6
    old_agent=functions((OUT/'source_before/agent.py').read_text());new_agent=functions((ROOT/'agent.py').read_text())
    assert old_agent['run_diagnostics']==new_agent['run_diagnostics']
    assert 'plan_and_assess' not in new_agent and 'combined_gate' not in (ROOT/'main.py').read_text()
    old_cite=functions((OUT/'source_before/src/citation_validation.py').read_text())
    new_cite=functions((ROOT/'src/citation_validation.py').read_text())
    assert all(new_cite[n]==value for n,value in old_cite.items())
    result=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    documents=[ROOT/n for n in ('PROGRESS.md','README.md','docs/PROJECT_METRICS.md','docs/CODE_READING_GUIDE.md')]+list(OUT.glob('*.md'))
    links=[];broken=[]
    for p in documents:
        for url in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',url) or url.startswith('#'):continue
            local=unquote(url.strip('<>').split('#')[0])
            if not local:continue
            links.append((str(p.relative_to(ROOT)),url))
            if not (p.parent/local).exists():broken.append(links[-1])
    assert not broken,broken
    private=read(ROOT/'api.local.json')
    secrets=[s for s in (private.get('api_key'),os.environ.get('RAG_API_KEY')) if s]
    exposed=[str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file()
             and any(s.encode() in p.read_bytes() for s in secrets)]
    assert not exposed,exposed
    chunks=read(ROOT/'data/processed/versions/all-papers-8-20261020/chunks.json');identity_count=0
    for p in OUT.rglob('loop/inputs.json'):
        if 'source_after' in p.parts or 'source_before' in p.parts:continue
        case=read(p)['question'];assert set(case)=={'query','kb_version','evidence','inventory'}
        for c in case['evidence']:
            assert all(c[k]==chunks[c['chunk_id']][k] for k in ('source','page','text'));identity_count+=1
    for p in OUT.rglob('answer/inputs.json'):
        if 'source_after' in p.parts or 'source_before' in p.parts:continue
        for c in read(p)['passages']:
            assert all(c[k]==chunks[c['chunk_id']][k] for k in ('source','page','text'));identity_count+=1
    cache=read(OUT/'scoped_inputs/probe_cache.json')
    assert sha(ROOT/cache['origin'])==cache['origin_sha256']
    assert cache['api_public_settings']==latest['api_public_settings']
    reused=[c for c in read(OUT/'scoped_inputs/actual_chat_calls.json') if c.get('response_source')]
    assert len(reused)==1 and reused[0]['http_posts']==0
    assert reused[0]['prompt']==cache['entry']['prompt'] and reused[0]['response']==cache['entry']['response']
    summary=read(OUT/'summary.json');assert summary['actual_unique_http_posts']==32
    assert summary['actual_new_reported_usage']['total_tokens']==98399
    for review in summary['selected_development_reviews']:
        assert sha(OUT/review['result_path'])==review['result_sha256']
    log=(OUT/'tests_final.log').read_text()
    assert 'Ran 251 tests' in log and 'OK' in log and 'Network attempts: 0' in log
    active=read(ROOT/'data/processed/active_kb.json');assert 'semantic-mac-20261019' in json.dumps(active)
    value={'status':'passed','verified_at_utc':datetime.now(timezone.utc).isoformat(),
           'baseline_files':len(before),'changed_existing_files':sorted(changed),
           'unchanged_existing_files':len(before)-len(changed),'deleted_files':deleted,
           'historical_scores_results_and_knowledge_bases_unchanged':True,
           'phase_source_snapshots':version_checks,'final_production_matches_last_frozen_validation':True,
           'unchanged_main_functions':unchanged,'original_agent_loop_and_budgets_unchanged':True,
           'original_rag_citation_functions_unchanged':True,'unused_combined_gate_removed':True,
           'git_diff_check':'passed','local_links_checked':len(links),'broken_links':broken,
           'secret_absence':not exposed,'canonical_passage_identity_checks':identity_count,
           'offline_tests':251,'offline_network_attempts':0,'actual_new_http_posts':32,'actual_new_tokens':98399,
           'exact_successful_probe_reused_without_double_billing':True,
           'held_out_quality_gain_proven':False,'latest_h10_upgrade_completed':False,
           'P3_implemented':False,'commit_or_push_performed':False}
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:value[k] for k in ('status','baseline_files','changed_existing_files','local_links_checked','canonical_passage_identity_checks')}))


if __name__=='__main__':main()
