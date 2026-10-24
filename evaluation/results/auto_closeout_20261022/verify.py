"""收尾只读核验：保护旧资产、冻结源码、原文身份、成本分母、链接与凭证隔离。"""
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
    target=OUT/'verification.json'
    target.write_text('{"status":"checking"}\n')
    baseline=read(OUT/'baseline_hashes.json')
    deleted=[p for p in baseline if not (ROOT/p).is_file()]
    changed=[p for p,h in baseline.items() if (ROOT/p).is_file() and sha(ROOT/p)!=h]
    expected={'main.py','agent.py','tests/test_main_agent.py','PROGRESS.md','README.md',
              'docs/CODE_READING_GUIDE.md','docs/PROJECT_METRICS.md'}
    assert not deleted and set(changed)==expected,(deleted,changed)
    protocol=read(OUT/'frozen_protocol.json')
    assert all(sha(ROOT/p)==h for p,h in protocol['source_hashes'].items())
    ast_checks={}
    for name,allowed in [('main.py',{'_run_pipeline','_answer_with_agent','main','cli'}),
                         ('agent.py',{'run_diagnostics'})]:
        before=ast.parse((OUT/'source_before'/name).read_text());after=ast.parse((ROOT/name).read_text())
        functions=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
        old,new=functions(before),functions(after)
        altered=[n for n in old if old[n]!=new.get(n)]
        assert set(altered)==allowed,(name,altered)
        globals_only=lambda tree:[ast.dump(n,include_attributes=False) for n in tree.body if not isinstance(n,ast.FunctionDef)]
        assert globals_only(before)==globals_only(after)
        ast_checks[name]={'changed_functions':altered,'unchanged_functions':[n for n in old if n not in altered],
                          'module_globals_unchanged':True}
    checks=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    assert checks.returncode==0,checks.stdout+checks.stderr
    docs=[ROOT/p for p in ('PROGRESS.md','README.md','docs/CODE_READING_GUIDE.md','docs/PROJECT_METRICS.md')]
    docs+=list(OUT.glob('*.md'))
    links=[];broken=[]
    for path in docs:
        for url in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text()):
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',url) or url.startswith('#'):continue
            local=unquote(url.strip('<>').split('#')[0])
            if not local:continue
            links.append((str(path.relative_to(ROOT)),url))
            if not (path.parent/local).exists():broken.append(links[-1])
    assert not broken,broken
    written=[ROOT/p for p in expected]+[ROOT/'tests/test_main_auto.py']
    written += [p for p in OUT.iterdir() if p.suffix in {'.py','.md'}]
    trailing=[(str(p.relative_to(ROOT)),i) for p in written for i,line in enumerate(p.read_text().splitlines(),1)
              if line.rstrip()!=line]
    assert not trailing,trailing
    private=read(ROOT/'api.local.json')
    secrets=[x for x in (private.get('api_key'),os.environ.get('RAG_API_KEY')) if x]
    exposed=[str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file()
             and any(secret.encode() in p.read_bytes() for secret in secrets)]
    assert not exposed,exposed
    chunks=read(ROOT/'data/processed/versions/all-papers-8-20261020/chunks.json')
    canonical={c['chunk_id']:c for c in chunks};identity_checks=0
    for path in (OUT/'cases').glob('*/**/loop/inputs.json'):
        case=read(path)['question']
        assert set(case)=={'query','kb_version','evidence','inventory'}
        for c in case['evidence']:
            original=canonical[c['chunk_id']]
            assert all(c[k]==original[k] for k in ('source','page','text'))
            identity_checks+=1
    for path in (OUT/'cases').glob('*/**/answer/inputs.json'):
        passages=read(path)['passages']
        assert len(passages)<=32 and sum(len(c['text']) for c in passages)<=24000
        for c in passages:
            assert all(c[k]==canonical[c['chunk_id']][k] for k in ('source','page','text'))
            identity_checks+=1
    s=read(OUT/'summary.json');calls=read(OUT/'actual_chat_calls.json')
    assert len(calls)==68 and all(c['status']=='completed' and c['http_posts']==1 for c in calls)
    assert sum(c['response']['usage']['total_tokens'] for c in calls)==149573
    assert all(q['planned_questions']==8 for q in s['quality'].values())
    final_tests=(OUT/'tests_final.log').read_text()
    assert 'Ran 239 tests' in final_tests and 'OK' in final_tests and 'Network attempts: 0' in final_tests
    active=read(ROOT/'data/processed/active_kb.json')
    assert 'semantic-mac-20261019' in json.dumps(active)
    value={'status':'passed','verified_at_utc':datetime.now(timezone.utc).isoformat(),
           'baseline_files':len(baseline),'changed_existing_files':sorted(changed),
           'unchanged_existing_files':len(baseline)-len(changed),'deleted_existing_files':deleted,
           'knowledge_bases_active_pointer_and_old_results_unchanged':True,
           'production_code_frozen_through_real_comparison':True,'frozen_hash_count':len(protocol['source_hashes']),
           'AST':ast_checks,'git_diff_check':'passed','new_or_updated_text_trailing_whitespace':trailing,
           'local_markdown_links_checked':len(links),'broken_local_links':broken,
           'secret_absence_in_new_artifacts':not exposed,'canonical_passage_identity_checks':identity_checks,
           'offline_tests':{'passed':239,'network_attempts':0},'actual_calls':68,'actual_tokens':149573,
           'failures_kept_in_planned_denominator':True,'P3_started':False,'commit_or_push_performed':False}
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:value[k] for k in ('status','baseline_files','changed_existing_files','local_markdown_links_checked','canonical_passage_identity_checks')}))


if __name__=='__main__':main()
