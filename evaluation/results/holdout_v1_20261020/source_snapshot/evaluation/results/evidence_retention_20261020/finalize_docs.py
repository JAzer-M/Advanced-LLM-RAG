"""Write evidence-derived handoff documentation after the offline replay audit."""
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
METHOD = 'Evidence Completion (up to 2 rounds)'


def read(name):
    return json.loads((OUT / name).read_text())


def main():
    comparison = read('comparison.json')
    verification = read('verification.json')
    adoption = read('adoption.json')
    replay = read('main_replay_summary.json')
    assert verification['status'] == 'passed' and verification['main_replay_completed']
    assert adoption['chosen_top_k'] == 10
    variants = comparison['variants']
    fixed = variants['fixed_selection_candidate120']['metrics']
    row = lambda s: f"{s['precision']:.4f} | {s['recall']:.4f} | {s['map']:.4f} | {s['mrr']:.4f} | {s['full_gold']}/{s['questions']}"
    headline = '| 最终预算 | Precision | Recall | MAP | MRR | 全部 Gold 入选 |\n| --- | ---: | ---: | ---: | ---: | ---: |\n'
    for k in ['10', '20']:
        headline += f"| Top-{k} | {row(fixed[k]['all'][METHOD])} |\n"
    complete_table = '| 选择规则 | 候选 | 最终 K | Precision | Recall | MAP | MRR | 全部 Gold 入选 |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n'
    for name, label, budget in [('old_selection_candidate60', '修复前', 60),
                                ('fixed_selection_candidate60', '修复后', 60),
                                ('old_selection_candidate120', '修复前', 120),
                                ('fixed_selection_candidate120', '修复后', 120)]:
        for k in ['10', '20']:
            complete_table += f"| {label} | {budget} | {k} | {row(variants[name]['metrics'][k]['all'][METHOD])} |\n"
    groups = '| 题组 | 题数 | 最终 K | Precision | Recall | MAP | MRR | 全部 Gold 入选 |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n'
    for group, label in [('old', '此前题集'), ('new', '八篇评估新增题（本轮复用）'), ('single', '单篇'), ('cross', '跨篇')]:
        for k in ['10', '20']:
            score = fixed[k][group][METHOD]
            groups += f"| {label} | {score['questions']} | {k} | {row(score)} |\n"
    ratio = adoption['median_complete_context_character_ratio']
    contexts = read('context_cost.json')['fixed_selection_candidate120']
    context_medians = {k: statistics.median(x['context_characters'] for x in values.values())
                       for k, values in contexts.items()}
    cost = read('processing_cost.json')
    pairs = {k: sum(x[k] for x in cost.values()) for k in ['unique_pairs', 'reused_pairs']}
    audit_count = verification['four_metric_rows_independently_recomputed']
    current = '**已完成**原查询锚点和补查局部证据保留修复；当前 main 为候选 120、最终 Top-10、按需最多两轮补查。Top-20 已独立量化并保留结果，尚未设为默认。重写与 HyDE 关闭。四项指标全部计算，本轮新增 API 调用为 0。'
    settings = '''| 项目 | 当前值 / 验证边界 |
| --- | --- |
| Embedding | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，CPU、384 维 |
| Reranker | `BAAI/bge-reranker-base`，本机缓存，CPU 离线实测 |
| 每路 Dense / BM25 与 RRF 候选 | `RETRIEVAL_TOP_K=120`、`RRF_TOP_K=120` |
| RRF 秩平滑常数 | `RRF_K=60`，不是候选数 |
| 最终证据 | `RERANK_TOP_K=10`；Top-20 已独立对照 |
| 来源定向补查 | `USE_EVIDENCE_COMPLETION=True`，`main(..., completion_rounds=2)`；按信号触发并可提前停止 |
| 补查候选深度 | 第 1 / 2 轮为 120 / 240，先限定论文再截断；不是固定执行两次 |
| rewrite / HyDE | `USE_MULTI_QUERY=False`、`USE_HYDE=False` |
| 默认知识库 | `semantic-mac-20261019` 三篇库；八篇需显式指定 |
| evaluation | 候选默认 120；本轮显式 `--top-k 10 20 --complete-evidence --completion-rounds 2`；CLI 补查轮数默认仍为 1 |
| 当前真实生成 | API 配置存在；本轮未重新发起生成，不能据此验收新参数回答 |
'''
    reason = f'Top-20 的 Recall 增加 **4.37 个百分点**、完整 Gold 由 28/42 增至 30/42，MAP / MRR 略增；完整上下文字符比值中位数为 **{ratio:.2f}**。本轮开始前设定 Recall 至少增加 5 个百分点才把默认提高为 20，因此保持 10。此门槛是本轮的工程预算选择，不是通用统计结论；偏重召回时可显式使用 20。候选 120 按用户决定保留，但修复后候选 60 的 Top-10 Recall 同为 .7679、MAP / MRR 更高，不能说候选越大越好。'
    checked = f'''- 先在旧代码上建立四个失败回归测试，再修复；全部 **68 项 unittest** 通过，红灯 / 绿灯原始输出保留。
- 原 `run_evaluation` CLI 完成 42 题 × 修复前后 × 候选 60/120 × 独立 K=10/20；所有方法保存 Precision、Recall、AP/RR，汇总 MAP/MRR。4 道无 Gold 题跳过，未伪造为 0 分。
- 独立脚本重新由原文映射 Gold，并复算 **{audit_count:,} 组方法/K/题记录的四项指标**（主对照 3,696 组，加增强和三篇入口检查）；分组均值也一致。
- `main.main` 真实检索 / 重排 / 上下文回放 **{replay['actual_main_retrieval_runs']} 次**，p1 含 rewrite + HyDE 的两种 K，选中 ID 均与 evaluation 对齐；最终回答显式替身，不能称为真实回答成功。
- 当前仍激活的三篇库，通过五道题、候选 120、两种 K、最多两轮的实际 evaluation CLI；原三篇/五篇/八篇资产哈希及 9 项迁移清单一致。
- 原 60 / Top-10 共有方法逐题复现上一轮；全部被标记的局部证据在补查各轮保留，API 调用计数为 **0**，凭证未进入导出产物。
- 主对照耗时约 **{comparison['elapsed_seconds']/60:.1f} 分钟**，共享重排缓存，不能作为单请求延迟或服务基准。'''
    template = (OUT / 'progress_template.md').read_text()
    replacements = {'CURRENT_OUTCOME': current, 'SETTINGS_TABLE': settings,
                    'METRIC_TABLE': '八篇库 42 道英文可答题，候选 120、关闭 rewrite / HyDE、按需最多补查两轮：\n\n' + headline,
                    'ADOPTION_REASON': reason, 'VERIFICATION': checked}
    for key, value in replacements.items():
        template = template.replace('{{' + key + '}}', value)
    assert '{{' not in template
    (ROOT / 'PROGRESS.md').write_text(template)
    report_path = ROOT / 'docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md'
    report = report_path.read_text()
    report = report.replace('状态：修复与 68 项本地测试完成；完整量化和主流程检索回放进行中。',
                            '状态：修复、完整离线量化、main 检索回放、独立复核和交接完成。')
    report = report.replace('## 用户最终决定与实验范围',
                            '## 本轮结论\n\n' + current + '\n\n' + headline + '\n' + reason + '\n\n## 用户最终决定与实验范围')
    insert = f'''## 完整量化结果

以下均为原 evaluation 的 `Evidence Completion (up to 2 rounds)` 行，四项分数都是逐题计算后取平均。题集相同、rewrite / HyDE 关闭；不是重写增强后的结果。

{complete_table}
同候选 120、Top-10 下，修复使 Recall 从 .7718 变为 .7679（下降 0.40 个百分点），MAP 从 .483554 变为 .483675，MRR 从 .5726 变为 .5708，全部 Gold 入选题数从 27 增为 28。可见保留行为修复成立，但并非全部指标上升。保护较弱的局部候选会与其他证据竞争预算。

与上一轮修复前 60 / Top-10 的两轮补查相比，最终 120 / Top-10 Recall .7480→.7679（+1.98 个百分点），MAP .4937→.4837、MRR .5830→.5708；不能只报召回而隐藏排序损失。修复后 60 / Top-10 的 MAP .4982、MRR .5852 均高于 120，候选 120 依用户选择保留。

### 候选 120 的分组结果

{groups}
跨篇题仍是主要短板，Top-10 / 20 Recall 为 .4479 / .5521。新增题与旧题、单篇与跨篇属于两种交叉分组，不能加在一起当作额外题量。四道无 Gold 题 q6 / p7 / n11 / n12 未计检索分数；未重新验证它们的生成拒答效果。

### 上下文、耗时与默认预算

完整上下文包括正文、真实标题及规则账本。Top-10 / Top-20 的字符数中位数分别为 {context_medians['10']:,.0f} / {context_medians['20']:,.1f}，按题计算比值的中位数为 {ratio:.4f}（与两个总体中位数相除不同）。它只是输入长度代理，未测实际 token 或新版 API 账单。

Top-20 召回 +4.37 个百分点，MAP +.0020、MRR +.0019，全部 Gold 多覆盖两题。预先采用门槛要求召回至少 +5 个百分点，其余三项门槛通过，召回门槛未过，因此默认保留 10；20 是可用选项，不是失败配置。没有在看完分数后修改阈值，也没有据此断言生成一定更好。

主对照实际耗时 {comparison['elapsed_seconds']:.3f} 秒（约 {comparison['elapsed_seconds']/60:.1f} 分钟），共 {pairs['unique_pairs']:,} 次唯一 query-passage 评分、{pairs['reused_pairs']:,} 次缓存复用。为降低本机重复推理，按题共享模型和分数并清空跨题缓存；这是顺序相关的实验总耗时，不可用于对比四方案的在线延迟。此次全部离线，**新 API 调用 0、没有新增 API token 消费**；以前 118 次调用属于上一轮。

## 实际验收与复核

{checked}

核心失败案例：p1 的增强查询锚点已固定并通过实际入口对照；p6 在候选 60 恢复被补查挤掉的 597，但在 120 的首次局部排序中该片段已未入选，仍只有部分指定证据。n07 的缺证据问题也没有因为保留规则而全部消失。所有这些题都保留逐轮 ID 和轨迹，运行时未读取 Gold。

## 仍需下一轮确认

本轮验证了检索、重排、证据预算与上下文构建，没有新调用最终回答 API。上一轮八次真实回答是旧设置的历史证据；新设置的答案准确性、语义引用和拒答仍需小量实测。来源简称匹配（例如 Transformer）、手工 Gold 不穷尽、p4 旧分解被拒绝、n08 题意歧义及受控线程根因均原样保留。不要重跑全套付费增强来恢复上下文。

下一轮先读重写后的 [PROGRESS](../PROGRESS.md)，再按用户授权做少量真实回答验收。Agent、通用增量入库和盲测属于后续工作，本轮未实现。

'''
    report = report.replace('## 保存与交接', insert + '## 保存与交接')
    report += '''
### 可核查产物

- [完整对照 JSON](../evaluation/results/evidence_retention_20261020/comparison.json)、[默认预算依据](../evaluation/results/evidence_retention_20261020/adoption.json)、[独立复核](../evaluation/results/evidence_retention_20261020/verification.json)。
- [红灯回归](../evaluation/results/evidence_retention_20261020/regressions_red.log)、[68 项绿灯](../evaluation/results/evidence_retention_20261020/tests_first_green.log)、[main 检索回放摘要](../evaluation/results/evidence_retention_20261020/main_replay_summary.json)。
- [上下文成本](../evaluation/results/evidence_retention_20261020/context_cost.json)、[评分复用](../evaluation/results/evidence_retention_20261020/processing_cost.json)、[原始输入哈希](../evaluation/results/evidence_retention_20261020/baseline_hashes.json)、[实验协议](../evaluation/results/evidence_retention_20261020/protocol.json)。
- [完整可见对话](chat_history/RAG_2026-10-19_20_完整对话.md)、[工具记录](chat_history/RAG_2026-10-19_20_tools.jsonl.gz)、[导出清单](chat_history/RAG_2026-10-19_20_export_manifest.json)、[重写前 PROGRESS 原件](history/PROGRESS_BEFORE_RETENTION_2026-10-20.md)。

对话导出以清单中的时间 / 哈希为快照边界，包含本次线程此前的可见用户 / 助手记录，不包含内部推理。当前轮最后一条交付答复若晚于快照，须后续刷新才进入原始会话归档；本报告和 PROGRESS 已保存最终交付状态。根目录 PROGRESS 已重写，旧版字节原样归档，没有丢弃长期路线。
'''
    report_path.write_text(report)
    print(json.dumps({'progress_lines': len(template.splitlines()), 'report_lines': len(report.splitlines()),
                      'metric_rows_verified': audit_count, 'main_replays': replay['actual_main_retrieval_runs']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
