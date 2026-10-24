# 本轮最小真实验证：只续接已保存的证据；不重跑检索，不读取Gold进提示词。
# h10最多四次新请求；h11全缺失分支必须零请求。失败不自动重试。
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT))
import agent


def main():
    output = Path(__file__).resolve().parent
    settings = agent.api.load_settings()
    if (settings.get('base_url') != 'http://127.0.0.1:7863/v1'
            or settings.get('model') != 'cn:deepseek-v4.1-flash'):
        raise RuntimeError('The configured route changed; inspect before sending new requests.')
    boundary = PROJECT / 'evaluation/results/agent_p21_closeout_20261020/run/h11.json'
    _, data, _, _ = agent.load_answer_case(PROJECT, boundary)
    if any(row['status'] != 'missing' for row in data['assessment']):
        raise RuntimeError('h11 is not the expected all-missing zero-call case.')
    results = {}
    results['h10'] = agent.run_answer(PROJECT,
        PROJECT / 'evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json', output / 'run/h10')
    def no_call(prompt):
        raise AssertionError('h11 must not call the model')
    results['h11'] = agent.run_answer(PROJECT, boundary, output / 'run/h11', no_call)
    agent.save_json(output / 'api_usage_summary.json', results)
    print(json.dumps(results, ensure_ascii=False), flush=True)
    if (results['h10']['answer_status'] != 'review_passed'
            or results['h11']['answer_status'] != 'insufficient_evidence'
            or results['h11']['api_attempts'] != 0):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
