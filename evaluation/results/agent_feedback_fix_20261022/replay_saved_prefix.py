# 反事实离线回放：旧响应只验证新控制流，提示已变，不冒称同提示缓存或新的模型结果。
import json
from pathlib import Path
import sys
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import agent
from src import agent_tools as tools

OUT=Path(__file__).resolve().parent
saved=ROOT/'evaluation/results/agent_auto_improvement_20261022/scoped_inputs/runs/h10_auto/loop'
case=json.loads((saved/'inputs.json').read_text())['question']
old=json.loads((saved/'question.json').read_text())
calls=json.loads((saved/'actual_chat_calls.json').read_text())
resource={'chunks':json.loads((ROOT/'data/processed/versions'/tools.SEARCH_KB_VERSION/'chunks.json').read_text()),
          'knowledge_base':old['steps'][0]['execution']['tool_result']['knowledge_base']}
# 原始usage属于旧账单；此处替身不发生任何HTTP，也不重复把旧token当新用量。
call=Mock(side_effect=[{'answer':c['response']['answer'],'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0},
                       'finish_reason':'stop','model':'saved-response-fixture'} for c in calls])
original_assess=agent.assess_evidence

def stop_at_unrecorded_feedback(*args,**kwargs):
    if call.call_count>=len(calls):
        raise KeyboardInterrupt
    return original_assess(*args,**kwargs)

output=OUT/'saved_prefix_loop'
if output.exists():raise ValueError('Replay outputs already exist; preserve the first run.')
with patch.object(agent.api,'load_settings',return_value={'model':'offline-saved-prefix'}), \
     patch.object(tools,'search_local_kb',return_value=old['steps'][0]['execution']['tool_result']) as search, \
     patch.object(tools,'read_neighbors',wraps=tools.read_neighbors) as read, \
     patch.object(agent,'assess_evidence',side_effect=stop_at_unrecorded_feedback):
    try:
        agent.run_diagnostics({'question':case},output,{},call,resources=resource,max_actions=3)
    except KeyboardInterrupt:
        status='paused_before_unrecorded_model_feedback'
    else:
        status='saved_prefix_completed'
record=json.loads((output/'question.json').read_text())
assert 'error' not in record,record.get('error')
first=record['steps'][0]
assert first['assessment_after']['requirements'][1]==old['assessment']['requirements'][1]
assert len(record['validation_repairs'])==1
summary={'scope':'Counterfactual saved-response injection with changed prompts; not exact-cache reuse or new semantic acceptance.',
         'status':status,'old_error_reproduced_after_fix':False,'fixture_model_calls':call.call_count,
         'actual_http_requests':0,'new_llm_tokens':0,'first_feedback_scope':first['feedback_scope'],
         'supported_requirement_retained':True,'initial_validation_repair_count':len(record['validation_repairs']),
         'search_result_replays':search.call_count,'real_local_neighbor_reads':read.call_count,
         'actions_executed_before_pause':record['actions_executed'],'halt_reason':record.get('halt_reason'),
         'h10_final_answer_validated':False}
(OUT/'saved_prefix_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
