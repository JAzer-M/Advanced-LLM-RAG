"""离线复现冻结新题的原始失败；不修生产代码，不覆盖任何真实输出。"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT))
import agent
from src import api_llm as api


def read(path):return json.loads(path.read_text())


def main():
    rows=[]
    with patch.object(api,'chat_completion',side_effect=AssertionError('Offline replay must not call API.')) as call:
        folder=OUT/'cases/a03/auto/loop'
        record=read(folder/'question.json');case=read(folder/'inputs.json')['question']
        raw=read(folder/'actual_chat_calls.json')[-1]
        assessment=json.loads(raw['response']['answer'])
        try:agent.validate_assessment(assessment,record['plan']['requirements'],case['evidence'],case['inventory'])
        except ValueError as exc:error=str(exc)
        else:raise AssertionError('Original a03 error did not reproduce.')
        assert 'Quoted text is not in chunk 1387' in error
        altered=deepcopy(assessment)
        for requirement in altered['requirements']:
            for ref in requirement['evidence']:
                ref['quote']=ref['quote'].replace('Arc-Challenge','Arc- Challenge')
        agent.validate_assessment(altered,record['plan']['requirements'],case['evidence'],case['inventory'])
        rows.append({'id':'a03','arm':'auto','original_error_reproduced':error,
                     'diagnostic_only':'Restoring just the original hyphen whitespace makes the same assessment valid; not a model rerun or production fix.'})
        for arm in ('agent','auto'):
            folder=OUT/f'cases/a04/{arm}/loop'
            case=read(folder/'inputs.json')['question']
            raw=read(folder/'actual_chat_calls.json')[-1]
            try:agent.bind_requirements(json.loads(raw['response']['answer']),case['query'])
            except ValueError as exc:error=str(exc)
            else:raise AssertionError('Original a04 error did not reproduce.')
            assert 'another declared subject' in error
            rows.append({'id':'a04','arm':arm,'original_error_reproduced':error})
        call.assert_not_called()
    (OUT/'failure_replay.json').write_text(json.dumps({'api_calls':0,'production_edits':False,'cases':rows},
                                             ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS: 3 original local failures reproduced; API calls 0; no prediction/result overwritten.')


if __name__=='__main__':main()
