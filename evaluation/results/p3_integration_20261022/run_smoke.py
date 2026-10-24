# 冻结的两题工程冒烟：真实main/模型/检索/公网，不将Gold或评分要求传给模型。
import hashlib
import json
from contextlib import ExitStack,redirect_stdout
from datetime import datetime,timezone
from pathlib import Path
import sys,time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
import main as pipeline
from src import agent_tools,api_llm as api

OUT=Path(__file__).resolve().parent
frozen=json.loads((OUT/'smoke_protocol.json').read_text())
for name,digest in frozen['source_hashes'].items():
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen source changed: '+name)
public={k:api.load_settings().get(k) for k in ('base_url','model','chat_options')}
if public!=frozen['api_public_settings']:raise ValueError('Public model options changed after freezing.')
label=sys.argv[1] if len(sys.argv)>1 else 'live'
if label not in {'live','network_followup','development_followup'}:raise ValueError('Unknown output label.')
folder=OUT/label
if folder.exists():raise ValueError('Preserve prior smoke runs; use a separately authorized audit label.')
folder.mkdir()
print('Loading existing offline CPU resources once...',flush=True)
started=time.perf_counter();resources=agent_tools.load_search_resources()
(folder/'resource_loading.json').write_text(json.dumps({'seconds':time.perf_counter()-started,'kb':resources['knowledge_base'],
    'scope':'One warm CPU process; not cold/concurrent/P95 latency.'},indent=2)+'\n')
wire=[];results=[];current={}
original=api.urlopen

def observe(request,*args,**kwargs):
    entry={'case':current['id'],'method':request.get_method(),'url':request.full_url,
           'started_at_utc':datetime.now(timezone.utc).isoformat(),'status':'running'}
    wire.append(entry);(folder/'model_http.json').write_text(json.dumps(wire,indent=2)+'\n')
    if len(wire)>frozen['max_chat_client_attempts']:raise RuntimeError('Frozen total smoke budget exhausted.')
    try:
        response=original(request,*args,**kwargs);entry.update(status='completed',http_status=response.status);return response
    except Exception as exc:
        entry.update(status='failed',error=f'{type(exc).__name__}: {exc}');raise
    finally:(folder/'model_http.json').write_text(json.dumps(wire,indent=2)+'\n')

with ExitStack() as stack:
    for owner,name,value in [(pipeline,'load_knowledge_base',(resources['index'],resources['chunks'],resources['knowledge_base'])),
          (pipeline,'load_embedding_model',resources['embedding_model']),
          (pipeline,'build_bm25_index',resources['bm25']),(pipeline,'CrossEncoder',resources['reranker_model'])]:
        stack.enter_context(patch.object(owner,name,return_value=value))
    stack.enter_context(patch.object(api,'urlopen',side_effect=observe))
    for case in frozen['cases']:
        current['id']=case['id'];case_dir=folder/case['id'];started=time.perf_counter()
        print('Running',case['id'],flush=True)
        with (folder/(case['id']+'_console.txt')).open('w') as console,redirect_stdout(console):
            try:
                result=pipeline.main(case['query'],mode='agent',allow_network=True,output_dir=case_dir)
            except Exception as exc:
                result=json.loads((case_dir/'result.json').read_text()) if (case_dir/'result.json').exists() else {'status':'failed'}
                result['driver_error']=f'{type(exc).__name__}: {exc}'
        row={'id':case['id'],'status':result['status'],'seconds':time.perf_counter()-started,
             'answer_strategy':result.get('answer_strategy'),'network':result.get('network'),
             'api_summary':result.get('api_summary'),'error':result.get('error',result.get('driver_error'))}
        results.append(row);(folder/'summary.json').write_text(json.dumps({'cases':results,'client_model_attempts':len(wire),
           'automatic_retries':0,'scope':'Two engineering smoke cases, not a held-out comparison.'},ensure_ascii=False,indent=2)+'\n')
        print(case['id'],row['status'],'model attempts',row.get('api_summary',{}).get('attempts'),flush=True)
print('Finished frozen smoke; inspect saved sources and review before claiming semantic success.',flush=True)
sys.exit(0 if all(r['status']=='completed' for r in results) else 1)
