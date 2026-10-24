# 只验证公开arXiv题录与固定版本PDF工具，不调用LLM，不导入知识库，不生成最终答案。
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from src.arxiv_tools import read_arxiv_paper,search_arxiv

OUT=Path(__file__).resolve().parent
label=sys.argv[1] if len(sys.argv)>1 else 'restricted'
if label not in {'restricted','network_followup','ca_followup'}:raise ValueError('Unknown smoke audit label.')
output=OUT/('live_'+label)
if output.exists():raise ValueError('Preserve existing live outputs; do not rerun this directory.')
output.mkdir()
results={};identity='2312.00752v1'
selection='Independent version-pinned primary-source smoke identity verified on the official arXiv page; not an Agent choice.'
try:
    result=search_arxiv('ti:"Mamba" AND au:"Gu"',output/'search',limit=3)
    for paper in result['papers']:
        if paper['title'].lower().startswith('mamba: linear-time sequence modeling'):
            identity=paper['arxiv_id'];selection='Original Mamba title found in the returned feed.';break
    results['search']={'status':result['status'],'papers':len(result['papers']),'trace':result['trace']}
except Exception as exc:
    result=json.loads((output/'search/result.json').read_text())
    results['search']={k:result[k] for k in ('status','trace','error')}
try:
    result=read_arxiv_paper(identity,output/'read',two_columns=True)
    results['read']={'status':result['status'],'arxiv_id':identity,'pages':result['pages'],
                     'documents':len(result['documents']),'characters':sum(len(d['text']) for d in result['documents']),
                     'trace':result['trace']}
except Exception as exc:
    result=json.loads((output/'read/result.json').read_text())
    results['read']={k:result[k] for k in ('status','trace','error')}
summary={'stage':'P3.1 independent tools only','label':label,'selection':selection,'results':results,
         'client_get_attempts':sum(x['trace']['http_attempts'] for x in results.values()),
         'successful_http_responses':sum(x['trace'].get('http_status')==200 for x in results.values()),
         'actual_llm_calls':0,'automatic_retries':0,'permanent_kb_import':False,'agent_invoked_network':False,
         'answer_quality_evaluated':False}
(output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
sys.exit(0 if all(x['status']=='completed' for x in results.values()) else 1)
