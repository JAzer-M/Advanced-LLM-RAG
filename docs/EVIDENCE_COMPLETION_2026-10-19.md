# 一轮证据补检索原型与对照记录

2026-10-19。用户授权尝试：第一次检索后检查缺口，必要时再查一次，合并重排，并运行原 `evaluation/run_evaluation.py`。沿用 Karpathy Guidelines 的最小改动和 Matt Pocock diagnosing-bugs 的固定失败回放。

**结论：原型和固定新旧题评测已完成。新十题 Recall@10 从 0.4833 提升到 0.6000，跨篇从 0.2222 到 0.4167；但旧六题从 1.0000 降到 0.9167，未通过采用门槛。保留原默认流程，新方案仅显式启用，不继续调参。** 本轮生成 API 调用 0，没有实际生成问答验收。

## 本轮固定范围

- 保留已有工作树、Gold、题集、索引、知识库选择与 API 私有配置。运行前保存源码快照和哈希，不复制私有配置内容。
- 一个候选方案，不依据跑分再改参数。候选 60、最终 10、最多一轮补查、最多四个子问题，不换模型、不重建索引、不安装依赖。
- 比较同样十道新可答题、六道旧开发题、五道旧验证题和三篇库五道题，共 26 道。无 Gold 题依旧跳过，不计为正确。
- 新题使用既有分解缓存、关闭改写以匹配主流程；旧题保留原有辅助查询条件。生成 API 在检索评测进程中被显式禁止。
- 这十道计分题仍是上一轮同五篇论文的手工新编验证集，不是外部盲测；n08 原题的条件归属歧义仍保留，题目、Gold 和原成绩均未改动。
- 完整的输入条件和采用门槛在评测前写入 [protocol.json](../evaluation/results/evidence_gap_20261019/protocol.json)。

## 流程如何运行

1. 原问题及已有子问题做 Dense/BM25/RRF 检索，得到第一次候选池；按现有方法重排和选证据，作为保留基线。
2. 从问题明确点名的论文与现有 title/source 元数据建立对应关系。仅对明确涉及两篇及以上论文的问题启用原型，不靠标准答案或固定片段编号定位论文。
3. 检查每个子问题的局部前三条是否来自所问论文、是否至少两条留在最终上下文，并记录指定论文在全局前十却被排除的片段。
4. 已在候选池里的缺口可以只修复选择；局部覆盖信号不足时，对该论文限定范围补做 Dense/BM25/RRF。每个子问题最多补一次，合计最多四个，不继续递归。
5. 保留第一次候选，追加新片段并去重。新片段按原问题用同一 Cross-Encoder 评分；原片段复用同一问题下已有的分数，各子问题的分数不直接互比。
6. 给原问题全局前半预算保留位置，然后保留原 RRF 首条、各限定论文子问题首条，剩余按全局排名填到十条；输出仍按原问题的全局分数排列。

这里先重排一次是为了获得可回退基线及缺口信号，补查后再合并。没有新候选时不重复计算原问题的全部重排分数。

**“覆盖信号不足”不等于经过语义验证的缺证据。** 同一论文中出现两条段落，也不保证回答所问事实。真实语义缺口仍由评测和人工原文复核判断。本轮不是完整 Agent、自主联网或通用事实验证。

限定论文检索先对当前小型 IndexFlat 语料取完整 Dense/BM25 排名，再按论文过滤、截取各 60 条；没有把第一次全库前 60 条再过滤冒充限定检索。这个实现适合本次 1,019 块先导库，没有验证大库性能。

## 失败回放与边界测试

实际调用旧 `select_evidence`，n07 返回的十条与既有记录逐项相同：所需 383 未进候选，237 已在候选但未入选。断言真实失败见 [baseline_red.log](../evaluation/results/evidence_gap_20261019/baseline_red.log)，入口为 [reproduce_gap.py](../evaluation/results/evidence_gap_20261019/reproduce_gap.py)。编号仅用于评测定位，不进入运行策略。

新测试覆盖来源名称边界（Self-RAG 不误匹配成 RAG）、错论文候选、没有子题分解的来源回退、单篇保留基线、补查合并/去重/停止、已有候选修复不额外检索、四子题上限。初次缺少模块的失败记录与实现后测试分别保存；后者验证实际行为，不能用模块导入成功代替检索效果。

## 结果与采用决定

均为 Top-10 宏平均，使用原 `run_evaluation.py` 和原指标公式，基线与原型在同一次运行里对照。

| 题集 | 基线 Recall | 原型 Recall | 基线 MAP | 原型 MAP | 基线 MRR | 原型 MRR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 新十题 | 0.4833 | 0.6000 | 0.2144 | 0.2367 | 0.3061 | 0.3272 |
| 其中跨篇六题 | 0.2222 | 0.4167 | 0.1181 | 0.1551 | 0.2500 | 0.2852 |
| 旧六题 | 1.0000 | 0.9167 | 0.3998 | 0.3792 | 0.3917 | 0.3875 |
| 旧五验证题 | 1.0000 | 1.0000 | 0.8000 | 0.8000 | 0.8000 | 0.8000 |
| 三篇库五题 | 0.8417 | 0.8667 | 0.5814 | 0.5931 | 0.7667 | 0.7667 |

新题 Precision@10 从 0.0700 到 0.1000；单篇 Recall 仍 0.8750。跨篇 Recall 增加约 19.44 个百分点，但完整覆盖全部指定 Gold 仍为 4/10，跨篇完整覆盖仍为 1/6。这是检索改善，不是回答准确率。

### 哪些地方改善，哪些仍失败

- n05：Gold 仍 2/2，但触发了三次定向补查。这说明来源覆盖信号会产生额外工作，并不自动知道答案其实已足够。
- n06：不补检索，仅调整入选集合，DPR loss 的 36 从未入选变为第五条；指定证据从 1/3 到 2/3，39 仍被排除。
- n07：ColBERT 的 237 恢复到第九条；RAG 的 383 从第一次候选池之外进入合并池，但最终仍未入选。指定证据从 0/2 到 1/2，原问题的“完整覆盖”断言仍未通过。
- n08：Self-RAG 的 590 恢复到第十条，指定证据从 0/3 到 1/3；CRAG 的 873/874 仍未入选。
- n09：来源与子题覆盖信号没有触发实际补查，重选后仍 0/2；说明“已经有同论文段落”不能识别具体日期等事实缺口。
- n10：补查两次仍没有把 32/233 找入候选，指定证据仍 0/2。限定论文范围不足以解决所有细节查询。
- 旧 p6：原来 28/219 两段均在最终十条；原型只保留 28，219 被挤掉，题目 Recall 从 1.0 到 0.5，导致旧六题宏平均下降。

这些 ID 只用于事后审计，不进入运行策略。[新题逐段候选/入选变化](../evaluation/results/evidence_gap_20261019/gold_gap_review.json)保留原始位置，不修改标注。

预先设定的采用条件是：新跨篇 Recall 至少增加 0.10；新题 MAP/MRR 下降不超过 0.01；每套旧题 Recall 不下降、MAP/MRR 下降不超过 0.01；评测耗时中位比不超过 2。本次前两项与耗时条件通过，旧题 Recall 和 MAP 条件失败。**不采用为默认流程，保留实验开关，不追加第二个策略或参数搜索。**

### 成本与核验

- 26 道可答题中，18 道未改变路径；8 道执行了重选/定向重排，其中 6 道实际补检索，共 11 次限定论文查询。每题最多一轮、每轮最多四次查询；查询次数与 API 调用次数不同。
- 四套实际 evaluation 共约 358.6 秒，不含模型首次载入。受影响八题的额外时间中位数约 11.37 秒，评测耗时比中位数约 1.54 倍；三篇库 q5 为约 3.50 倍。全题中位数接近 1 倍，是未触发题较多造成的，不意味着补查没有成本。这些时间包含评测对照方法的工作，是成本参考，不是生产服务延迟或 P95。
- **58 项本地测试全部通过**，包括新增八项来源识别、补查与停止边界测试。[测试记录](../evaluation/results/evidence_gap_20261019/tests_final.log)。原 50 项保留。
- 全部旧方法逐题 ID 和四项指标与冻结记录一致，独立算术复核检查 236 组逐题方法指标及汇总。候选、Gold、原指标、索引、默认库、私有 API 配置均保留。
- n06/n07 另外走实际 `main.main(..., complete_evidence=True)` 检索路径，选中 ID 与本轮 evaluation 完全一致，分别为只重选与补查一轮。此检查复用冻结分解，**生成器使用占位输出**，不能算真实生成或语义验收。[主流程检索回放](../evaluation/results/evidence_gap_20261019/main_replay.json)。
- 生成上下文、提示词和证据账本函数 AST 与基线完全相同。源码改动限于新增补查函数、主流程显式开关及 evaluation 对照行；既有重排/选择实现不变。
- 检索评测与主流程检索回放的生成 API 调用均为 0。因采用门槛未通过，未启动原先有条件安排的少量真实生成，没有新增付费模型消耗。

总表、门槛与逐题耗时见 [comparison.json](../evaluation/results/evidence_gap_20261019/comparison.json)。原始四套记录：[新题](../evaluation/results/evidence_gap_20261019/new/results.json)、[旧六题](../evaluation/results/evidence_gap_20261019/old_core/results.json)、[旧五验证题](../evaluation/results/evidence_gap_20261019/old_validation/results.json)、[三篇库五题](../evaluation/results/evidence_gap_20261019/old_three_papers/results.json)。

## 操作与产物

主流程通过 `main.main(query, kb_version='arxiv-pilot-5-20261019', complete_evidence=True)` 显式尝试；默认开关为 False。主流程返回的 `retrieval_diagnostics['evidence_completion']` 保存触发原因、每个子问题的来源对应、补查次数、新候选、前后选中 ID 与停止原因。省略该参数时沿用默认行为。

量化入口新增 `--complete-evidence`，增加 `Evidence Completion (one round)` 方法行，同时保留全部旧方法与原指标。此原型只接受最终 `--top-k 10`。固定缓存的 Mac 示例（输出请使用新目录）：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -u -c "import runpy, torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); runpy.run_module('evaluation.run_evaluation', run_name='__main__')" \
  --questions evaluation/arxiv_next_questions_en.json \
  --kb-version arxiv-pilot-5-20261019 --candidate-k 60 --top-k 10 \
  --auxiliary-cache evaluation/results/independent_validation_20261019/auxiliary.json \
  --complete-evidence --output-dir evaluation/results/new_completion_run
```

复用缓存不会调用分解/改写 API，但加载 CPU 模型和检索重排仍有计算成本。本轮实验完整入口为 [run_comparison.py](../evaluation/results/evidence_gap_20261019/run_comparison.py)。
