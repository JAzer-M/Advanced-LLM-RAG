"""从冻结结果生成分模型、网关故障与真实成本的补充汇总；不调用API。"""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'paper_bound_deepseek_v41_flash'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    questions = load(OUT / 'frozen_sample.json')['questions']
    rows = load(OUT / 'scores/per_question.json')
    results, judges, model_groups, proxy_questions = {}, {}, {}, set()
    for question in questions:
        qid = question['question_id']
        models = []
        for mode in ('rag', 'agent', 'auto'):
            result = load(OUT / 'runs' / qid / f'{mode}.json')
            results[qid, mode] = result
            judges[qid, mode] = load(OUT / 'judge' / qid / f'{mode}.json')
            models.append(result['execution']['settings']['model'])
            if any('反代 API' in c.get('error', '') for c in result['eval_api_calls']):
                proxy_questions.add(qid)
        assert len(set(models)) == 1, qid
        model_groups.setdefault(models[0], []).append(qid)

    def summary(qids):
        answer = {}
        for mode in ('rag', 'agent', 'auto'):
            mine = [r for r in rows if r['mode'] == mode and r['question_id'] in qids]
            runs = [results[r['question_id'], mode] for r in mine]
            verdicts = [judges[r['question_id'], mode] for r in mine]
            mean = lambda values: sum(values) / len(values) if values else None
            unanswerable = [r for r in mine if r['gold_majority_unanswerable']]
            answer[mode] = {
                'n': len(mine), 'answer_f1': mean([r['answer_f1'] for r in mine]),
                'evidence_f1': mean([r['evidence_f1'] for r in mine]),
                'retrieval_hit_rate': mean([int(r['retrieved_gold_evidence']) for r in mine if r['has_gold_evidence']]),
                'status': dict(Counter(r['status'] for r in runs)),
                'requests': sum(r['requests'] for r in mine), 'tokens': sum(r['tokens'] for r in mine),
                'mean_seconds': mean([r['seconds'] for r in mine]),
                'judge': dict(Counter(j.get('verdict', j['status']) for j in verdicts)),
                'majority_unanswerable': len(unanswerable),
                'declined_on_unanswerable': sum(r['prediction_kind'] == 'declined' for r in unanswerable),
                'declined_on_answerable': sum(r['prediction_kind'] == 'declined' for r in mine if not r['gold_majority_unanswerable']),
            }
        return answer

    def calls_cost(calls):
        return {'requests': len(calls), 'failed_requests': sum(c['status'] != 'completed' for c in calls),
                'usage_missing_requests': sum(c.get('usage') is None for c in calls),
                'reported_tokens': sum((c.get('usage') or {}).get('total_tokens', 0) for c in calls),
                'requested_models': dict(Counter(c.get('requested_model') for c in calls)),
                'reported_models': dict(Counter(c.get('reported_model') for c in calls if c.get('reported_model')))}

    costs = {}
    for name, folder in [('glm_429_attempt', HERE), ('unbound_input_attempt', HERE / 'deepseek_v41_flash'),
                         ('formal_generation', OUT)]:
        calls = [c for p in (folder / 'runs').glob('*/*.json') for c in load(p)['eval_api_calls']]
        costs[name] = calls_cost(calls)
    judge_calls = [c for value in judges.values() for c in value['eval_api_calls']]
    costs['judge'] = calls_cost(judge_calls)
    costs['all_recorded_calls'] = {key: sum(value[key] for value in costs.values())
                                  for key in ('requests', 'failed_requests', 'usage_missing_requests', 'reported_tokens')}
    costs['unbound_interruption_note'] = 'Interrupted during the next RAG reranking after decomposition; at least one additional decomposition request and its usage were not saved. Recorded totals are a lower bound.'

    mismatched_judges = [{'question_id': qid, 'mode': mode,
                         'answer_model': result['execution']['settings']['model'],
                         'judge_model': judges[qid, mode].get('judge_requested_model')}
                        for (qid, mode), result in results.items()
                        if result['execution']['settings']['model'] != judges[qid, mode].get('judge_requested_model')]
    failed = [{'question_id': qid, 'mode': mode, 'status': r['status'],
               'error': r.get('error'), 'answer_status': r.get('answer_status'), 'stop_reason': r.get('stop_reason')}
              for (qid, mode), r in results.items() if r['status'] != 'completed']
    all_ids = {q['question_id'] for q in questions}
    result = {'primary_52_questions': summary(all_ids),
              'model_question_counts': {model: len(qids) for model, qids in model_groups.items()},
              'by_requested_model': {model: summary(set(qids)) for model, qids in model_groups.items()},
              'proxy_failure_question_ids': sorted(proxy_questions),
              'posthoc_same_49_questions_without_proxy_failure': summary(all_ids - proxy_questions),
              'costs': costs, 'judge_model_mismatches': mismatched_judges, 'non_completed_results': failed,
              'input_hashes': {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                               for name in ('frozen_sample.json', 'protocol.md')}}
    (OUT / 'extended_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / 'summary.json').write_text(json.dumps({
        'primary_output_dir': OUT.name, 'result_kind': 'paper-bound, per-question model-paired, rotating-model evaluation',
        **result}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'primary': result['primary_52_questions'], 'costs': costs,
                      'judge_model_mismatches': mismatched_judges}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
