"""两道已知题验证真实main命令行；不替换模型/检索，只观察HTTP，非新题效果评测。"""
import contextlib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlsplit
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
CASES = {
    'answerable': 'Which optimizer and beta1, beta2, and epsilon values does the Transformer in Attention Is All You Need use?',
    'unanswerable': 'According to the original Mistral 7B paper, how many training tokens were used and what context length was used?'
}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import main as pipeline
    from src import api_llm as api
    paths=[ROOT/'main.py',ROOT/'agent.py',ROOT/'llm.py',OUT/'run_smoke.py',ROOT/'tests/test_main_agent.py']
    paths+=sorted((ROOT/'src').glob('*.py'))
    paths+=[ROOT/'data/processed/active_kb.json']
    paths+=[ROOT/'data/processed/versions/all-papers-8-20261020'/name
            for name in ('manifest.json','chunks.json','faiss.index')]
    public={key:api.load_settings().get(key) for key in ('base_url','model','chat_options')}
    protocol={'scope':'main CLI integration smoke; two known questions, no held-out quality score',
              'questions':CASES,'api_public_settings':public,'max_http_posts':22,
              'max_posts_per_case':11,'automatic_retries':0,
              'criteria':{'answerable':'Deliver supported optimizer and requested constants with valid citations.',
                          'unanswerable':'State primary-paper evidence is unavailable; do not guess requested values.'},
              'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths}}
    frozen=OUT/'frozen_protocol.json'
    if frozen.exists():
        prior=json.loads(frozen.read_text())
        assert {k:v for k,v in prior.items() if k!='frozen_at_utc'}==protocol
    else: save(frozen,{**protocol,'frozen_at_utc':datetime.now(timezone.utc).isoformat()})
    if (OUT/'smoke_summary.json').exists():
        print('Smoke already has a terminal summary; new requests: 0.',flush=True)
        return
    endpoint=urlsplit(public['base_url'])
    with socket.create_connection((endpoint.hostname,endpoint.port or 80),timeout=3):pass
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    events_path=OUT/'http_events.json'
    events=json.loads(events_path.read_text()) if events_path.exists() else []
    current={}
    raw_http=api._request

    def observe(path,payload=None):
        if path!='/chat/completions':return raw_http(path,payload)
        calls=json.loads((current['output']/'actual_chat_calls.json').read_text())
        active=calls[-1]
        assert active['status']=='running'
        assert len(events)<protocol['max_http_posts']
        assert not any(e['case']==current['case'] and e['main_number']==active['number'] for e in events)
        event={'number':len(events)+1,'case':current['case'],'main_number':active['number'],
               'phase':active['phase'],'status':'running','started_at_utc':datetime.now(timezone.utc).isoformat()}
        events.append(event);save(events_path,events)
        try:
            response=raw_http(path,payload)
            event['status']='completed'
            return response
        except Exception as exc:
            event.update(status='failed',error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            save(events_path,events)
            print(current['case'],active['phase'],'HTTP',event['number'],event['status'],flush=True)

    results={}
    started=time.perf_counter()
    with patch.object(api,'_request',side_effect=observe):
        for name,query in CASES.items():
            folder=OUT/'cases'/name;folder.mkdir(parents=True,exist_ok=True)
            output=folder/'run'
            current.update(case=name,output=output)
            if output.exists() and any(output.iterdir()):
                raise RuntimeError('A case was already started; do not automatically retry its main invocation.')
            argv=['main.py','--mode','agent','--output-dir',str(output),query]
            code=0
            try:
                with patch.object(sys,'argv',argv),(folder/'console.log').open('w') as log, \
                        contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                    pipeline.cli()
            except SystemExit as exc:
                code=exc.code
            result=json.loads((output/'result.json').read_text())
            results[name]={'cli_exit_code':code,'status':result['status'],
                           'api_summary':result.get('api_summary'),
                           'agent':result.get('agent'),'answer':result.get('answer')}
            print(name,result['status'],flush=True)
    calls=[c for name in CASES for c in json.loads((OUT/'cases'/name/'run/actual_chat_calls.json').read_text())]
    summary={'scope':protocol['scope'],'elapsed_seconds':time.perf_counter()-started,
             'cases':results,'actual_attempts':len(calls),'http_posts':len(events),
             'failed_attempts':sum(c['status']!='completed' for c in calls),
             'reported_usage':{key:sum((c.get('response',{}).get('usage') or {}).get(key,0) for c in calls)
                               for key in ('prompt_tokens','completion_tokens','total_tokens')},
             'missing_usage':[i+1 for i,c in enumerate(calls) if c.get('response',{}).get('usage') is None],
             'automatic_retries':0,'all_finish_reasons_stop':all(c.get('response',{}).get('finish_reason')=='stop' for c in calls)}
    save(OUT/'smoke_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
