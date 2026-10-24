# 只读取已保存的检索 ID，核对原指标并增补 nP 报表；不重新检索、不调用模型/API。
# 整体 nP 使用总命中/总可命中数，各题权重不同，不能直接平均逐题 nP。

"""Add normalized Precision to saved retrieval results, without model or API calls."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from evaluation.metrics import (
    average_precision_at_k,
    mean_average_precision_at_k,
    mean_reciprocal_rank_at_k,
    normalized_precision_at_k,
    overall_normalized_precision_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'Evidence Completion (up to 2 rounds)'


def summarize_cases(cases, k):
    count = len(cases)
    hits = sum(len(set(r[:k]) & set(g)) for r, g in cases)
    attainable = sum(min(k, len(set(g))) for _, g in cases)
    return {
        'questions': count,
        'precision': sum(precision_at_k(r, g, k) for r, g in cases) / count,
        'normalized_precision': overall_normalized_precision_at_k(cases, k),
        'recall': sum(recall_at_k(r, g, k) for r, g in cases) / count,
        'map': mean_average_precision_at_k(cases, k),
        'mrr': mean_reciprocal_rank_at_k(cases, k),
        'full_gold': sum(set(g) <= set(r[:k]) for r, g in cases),
        'hits': hits,
        'gold_count': sum(len(set(g)) for _, g in cases),
        'attainable_gold': attainable,
        'precision_ceiling': attainable / (count * k),
    }


# 先复算并核对原四项指标，再新增 nP；不改历史检索 ID 或覆盖原实验。
def build_report(source, questions):
    qmap = {q['id']: q for q in questions}
    result = {
        'status': 'completed', 'api_calls': 0, 'model_inference_calls': 0,
        'definition': {
            'per_question': 'H / min(K, G)',
            'aggregate': 'sum(H) / sum(min(K, G)); not the mean of per-question normalized scores',
            'precision_ceiling': 'sum(min(K, G)) / (question_count * K)',
            'recall': 'Macro average: mean(H/G), unchanged',
            'micro_recall_equivalence': 'Aggregate normalized Precision equals Micro Recall when every G <= K',
            'no_gold': 'Skipped; an all-no-Gold aggregate is undefined (None)',
            'interpretation': 'Attainable annotated-Gold coverage, not context usefulness or answer accuracy',
        },
        'skipped_no_gold': source.get('skipped_no_gold', []),
        'metric_rows_verified': 0, 'aggregate_rows_verified': 0, 'variants': {},
    }
    for name, variant in source['variants'].items():
        rows = []
        for original in variant['questions']:
            if original['status'] != 'completed' or not original.get('gold_ids'):
                continue
            row = {'id': original['id'], 'gold_ids': original['gold_ids'], 'metrics_by_k': {}}
            for key, methods in original['metrics_by_k'].items():
                k = int(key)
                row['metrics_by_k'][key] = {}
                for method, saved in methods.items():
                    ids, gold = saved['retrieved_ids'], original['gold_ids']
                    scores = {
                        'precision': precision_at_k(ids, gold, k),
                        'recall': recall_at_k(ids, gold, k),
                        'ap': average_precision_at_k(ids, gold, k),
                        'rr': reciprocal_rank_at_k(ids, gold, k),
                    }
                    for field, value in scores.items():
                        if not math.isclose(value, saved[field], abs_tol=1e-12):
                            raise ValueError(f'Original metric mismatch: {name}/{row["id"]}/{key}/{method}/{field}')
                    row['metrics_by_k'][key][method] = {
                        **saved, 'normalized_precision': normalized_precision_at_k(ids, gold, k)}
                    result['metric_rows_verified'] += 1
            rows.append(row)
        groups = {'all': rows,
                  'old': [q for q in rows if qmap[q['id']]['cohort'] != 'new_all_papers'],
                  'new': [q for q in rows if qmap[q['id']]['cohort'] == 'new_all_papers'],
                  'single': [q for q in rows if qmap[q['id']]['type'] == 'single_document'],
                  'cross': [q for q in rows if qmap[q['id']]['type'] != 'single_document']}
        groups.update({cohort: [q for q in rows if qmap[q['id']]['cohort'] == cohort]
                       for cohort in dict.fromkeys(qmap[q['id']]['cohort'] for q in rows)})
        table = {}
        for key, saved_groups in variant['metrics'].items():
            table[key] = {}
            for group, methods in saved_groups.items():
                table[key][group] = {}
                for method, saved in methods.items():
                    cases = [(q['metrics_by_k'][key][method]['retrieved_ids'], q['gold_ids'])
                             for q in groups[group]]
                    scores = summarize_cases(cases, int(key))
                    for field in ('questions', 'precision', 'recall', 'map', 'mrr', 'full_gold'):
                        if not math.isclose(scores[field], saved[field], abs_tol=1e-12):
                            raise ValueError(f'Original aggregate mismatch: {name}/{key}/{group}/{method}/{field}')
                    table[key][group][method] = scores
                    result['aggregate_rows_verified'] += 1
        result['variants'][name] = {'questions': rows, 'metrics': table}
    return result


def markdown_report(report):
    lines = [
        '# 整体归一化 Precision 补充报表（2026-10-20）', '',
        '本表只复算已保存的检索 ID，没有重新检索、调用模型或 API；原始实验文件保留。', '',
        '逐题 nP@K = H/min(K,G)；整体 nP@K = sum(H)/sum(min(K,G))，不是逐题 nP 的平均。',
        'H 是前 K 条中去重后的 Gold 命中数，G 是该题去重后的 Gold 数；无 Gold 题跳过。',
        '各组单独计算分母。所有 G≤K 时，整体 nP 等于 Micro Recall；原 Recall 仍是 Macro Recall。',
        '该列衡量预算内指定 Gold 的完成程度，不衡量全部上下文的有用比例或回答正确率。', '',
        f"已复核 {report['metric_rows_verified']} 条逐题记录和 {report['aggregate_rows_verified']} 条分组汇总，原四项指标全部一致。", '',
    ]
    header = ['| 条件 | K | 题数 | Precision | nP（整体） | Recall（宏平均） | MAP | MRR | 全部 Gold |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']

    def add_row(label, k, scores):
        lines.append(f"| {label} | {k} | {scores['questions']} | {scores['precision']:.4f} | "
                     f"{scores['normalized_precision']:.4f} | {scores['recall']:.4f} | "
                     f"{scores['map']:.4f} | {scores['mrr']:.4f} | {scores['full_gold']}/{scores['questions']} |")

    lines += ['## 最终设置与分组', '', *header]
    final = report['variants']['fixed_selection_candidate120']['metrics']
    for group, label in [('all', '全部'), ('old', '旧题'), ('new', '新增题'),
                         ('single', '单篇'), ('cross', '跨篇')]:
        for k, groups in final.items():
            if group in groups:
                add_row(label, k, groups[group][METHOD])
    lines += ['', '## 各方法：候选 120，修复后', '', *header]
    for k, groups in final.items():
        for method, scores in groups['all'].items():
            add_row(method, k, scores)
    lines += ['', '## 修复与候选数对照：最多两轮补查', '', *header]
    for name, variant in report['variants'].items():
        for k, groups in variant['metrics'].items():
            add_row(name, k, groups['all'][METHOD])
    lines.append('')
    for k, groups in final.items():
        scores = groups['all'][METHOD]
        lines.append(f"Top-{k} 总命中 {scores['hits']} / 可命中 {scores['attainable_gold']} = {scores['normalized_precision']:.4f}。")
    lines += ['所有 G≤K 时，逐题归一化后平均等于现有宏平均 Recall。',
              '新增列是对同一检索结果的重新表达；检索结果及历史预算采用门槛没有改变。',
              '完整方法、全部历史题组、命中数、可命中数及理论上限见同目录 report.json。', '']
    return '\n'.join(lines)


# 此入口只读已有结果；使用新输出目录，避免把补充报表混入历史实验目录。
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'evaluation/results/evidence_retention_20261020/comparison.json')
    parser.add_argument('--questions', type=Path, default=ROOT / 'evaluation/all_papers_questions_en.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('输出目录非空；请用新目录保留已有结果。')
    source = json.loads(args.input.read_text(encoding='utf-8'))
    if source.get('status') != 'completed':
        parser.error('输入实验尚未完成。')
    questions = json.loads(args.questions.read_text(encoding='utf-8'))
    report = build_report(source, questions)
    report['input_sha256'] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (args.input, args.questions)}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output_dir / 'report.md').write_text(markdown_report(report), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('status', 'metric_rows_verified', 'aggregate_rows_verified', 'api_calls', 'model_inference_calls')}))


if __name__ == '__main__':
    main()
