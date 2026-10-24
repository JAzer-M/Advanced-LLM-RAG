# 全部论文、查询重写 / HyDE 与两轮补查实验（2026-10-20）

结论：已完成全部 8 篇论文、42 道英文可答题、四种查询增强设置及 0/1/2 轮补查对照。原流程 Recall@10=0.7361、MAP@10=0.4899；重写 + HyDE + 两轮补查为 0.7242、0.4797，完整 Gold 从 27/42 降到 25/42。**保持三项默认关闭，下一步优先修复证据保留。**

八次真实主流程回答、独立指标复核与本地测试均完成。检索分数与回答语义分别验收。

## 固定条件

- 遍历 `data` 的全部 PDF：8 篇不同论文，共 120 页。三篇旧库与五篇先导库中的每个 PDF 均通过 SHA-256 核对，没有重复 PDF。
- 独立合并版本 `all-papers-8-20261020`：1,397 条、384 维，精确复用已验证的分块和向量，仅重新分配合并位置 ID；不是重新解析或改变分块策略。原三篇默认库、五篇实验库及配置保留。
- 42 道英文可答题：26 旧题原样保留，16 新题（8 单篇、8 跨篇）；共 26 单篇、16 跨篇。另 4 道无 Gold 题跳过检索计分，不算正确。新题引文已逐条核对 PDF 物理页。
- 同一语料、同一题集、同一分解与查询增强输出，比较 base / rewrite / HyDE / both，以及补查上限 0 / 1 / 2。每路候选 60，最终 10；第二轮的来源候选深度为 120。
- 原 `evaluation/run_evaluation.py` 增加 `--query-ablation`，额外输出与 `main.py` 对齐的四组条件；旧对照组与指标公式保留。运行检索时禁止 API。

## 查询增强的实际含义

rewrite 生成一个便于检索的改写，同时保留原问题的 Dense/BM25 候选；HyDE 生成短的假设回答，只将它用于 Dense 检索。真实论文片段经 RRF 融合、原问题全局重排与子题证据选择后，仍最多保留十条。假设回答本身不进入证据上下文。

补查依据现有来源覆盖启发式决定是否执行，并非每题固定查两遍。第一轮候选深度 60、第二轮 120；题目必须能识别两个以上来源才会触发。未修改名称识别器、分解提示、重写 / HyDE 提示、重排模型或选证据规则。

## 成本与运行边界

已实际新增辅助 API 110 次：26 次分解、42 次重写、42 次 HyDE；复用 16 份旧分解。代理累计报告 43,785 token（输入 40,038、输出 3,747），无失败或自动重试。沿用请求 `cn:deepseek-v4.1-flash`，以审计记录中的报告模型和用量为准，不推算金额或独立证明上游权重。

检索评估按题保存、复用模型实例和完全相同的 query-passage 重排分数，节省四组对照的重复计算。这一总耗时不是生产服务的逐组延迟或 P95。真实主流程抽测将另用未缓存的重排计算，查询增强输出固定，回答与必要的引用修复实际调用 API。

一个复用的旧分解 p4 因返回五个子题而被原有校验拒绝，仍按历史缓存处理，没有为提高分数重新生成。准备阶段曾遇到 PDF 连字字符和旧库外题缺失 `gold_evidence` 字段：分别按既有 NFKC 匹配口径和缺失即无 Gold 修复；已完成的 API 输出复用，没有重复调用。

这仍是人工构造的同语料验证，不是外部盲测。Gold 是指定段落集合，不穷尽全部正确证据；检索 Recall 不等于回答正确率。旧 n08 的条件归属歧义保留。

## 完整量化结果

使用用户指定的原 `evaluation/run_evaluation.py`，每题保留原方法并追加主流程四种查询设置。以下全部是在同一个八篇库、同一题集和同一最终 Top-10 内的对照；未拿不同语料的历史分数冒充改动收益。

Precision 按十条为分母；Recall、AP、RR 按原 Gold 定义计算后逐题平均。完整覆盖指该题全部指定 Gold 都进入最终十条。指标直接比较真实检索片段 ID 与原文 Gold，不使用 DeepSeek 回答或 LLM judge 打分；增强查询文本本身仍由 DeepSeek API 生成。

| 查询设置 | 补查上限 | P@10 | Recall@10 | MAP@10 | MRR@10 | 完整 Gold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 原流程 | 0 | 0.1262 | 0.7361 | 0.4899 | 0.5693 | 27/42 |
| 原流程 | 1 | 0.1310 | 0.7520 | 0.4922 | 0.5737 | 26/42 |
| 原流程 | 2 | 0.1310 | 0.7480 | 0.4937 | 0.5830 | 26/42 |
| 仅重写 | 0 | 0.1238 | 0.7123 | 0.4759 | 0.5554 | 26/42 |
| 仅重写 | 1 | 0.1286 | 0.7282 | 0.4783 | 0.5598 | 25/42 |
| 仅重写 | 2 | 0.1286 | 0.7242 | 0.4797 | 0.5690 | 25/42 |
| 仅 HyDE | 0 | 0.1214 | 0.7083 | 0.4847 | 0.5655 | 26/42 |
| 仅 HyDE | 1 | 0.1262 | 0.7242 | 0.4870 | 0.5699 | 25/42 |
| 仅 HyDE | 2 | 0.1262 | 0.7202 | 0.4885 | 0.5792 | 25/42 |
| 重写 + HyDE | 0 | 0.1238 | 0.7123 | 0.4759 | 0.5554 | 26/42 |
| 重写 + HyDE | 1 | 0.1286 | 0.7282 | 0.4783 | 0.5598 | 25/42 |
| 重写 + HyDE | 2 | 0.1286 | 0.7242 | 0.4797 | 0.5690 | 25/42 |

原流程不补查的 Recall 为 0.7361、MAP 为 0.4899；用户要求的“同时开启重写、HyDE，最多两轮补查”为 0.7242、0.4797，完整 Gold 从 27/42 降到 25/42。不开增强时，一轮的 Recall 最高 0.7520；两轮 MAP 略高 0.4937，但完整覆盖仍低于原流程，且旧题退步。

### 分组结果：原流程 vs 重写 + HyDE + 两轮

| 题组 | 题数 | 原 Recall | 实验 Recall | 原 MAP | 实验 MAP | 原完整 Gold | 实验完整 Gold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 全部旧题 | 26 | 0.7660 | 0.7340 | 0.4557 | 0.4329 | 17 | 15 |
| 新增题 | 16 | 0.6875 | 0.7083 | 0.5455 | 0.5559 | 10 | 10 |
| 全部单篇 | 26 | 0.9263 | 0.8878 | 0.6329 | 0.6104 | 22 | 21 |
| 全部跨篇 | 16 | 0.4271 | 0.4583 | 0.2575 | 0.2674 | 5 | 4 |
| 新增跨篇 | 8 | 0.5000 | 0.5417 | 0.3785 | 0.3993 | 3 | 3 |

新增 16 题仅开启重写 / HyDE 时，各组聚合四项分数都与原流程相同；个别十条列表有变化，不能据此说检索完全相同。对全部跨篇题，四种增强设置在同一个补查上限下的聚合四项分数也相同。补查提供了有限新证据，增强文本没有带来额外量化收益。

### 旧题回归：保持同一八篇库

| 原题集 | 原 Recall | 实验 Recall | 原 MAP | 实验 MAP |
| --- | ---: | ---: | ---: | ---: |
| questions | 0.8167 | 0.8167 | 0.5609 | 0.5609 |
| arxiv_pilot_questions_en | 1.0000 | 0.7500 | 0.4831 | 0.3625 |
| arxiv_validation_questions_en | 1.0000 | 1.0000 | 0.8000 | 0.8000 |
| arxiv_next_questions_en | 0.4833 | 0.5500 | 0.2144 | 0.2275 |

“旧题”指问题与 Gold 未改；其中十题过去的部分对照禁用了分解，本轮为四组统一生成了分解，不能把它们与旧三篇 / 五篇库的历史指标直接比较并归因于扩库。p1～p6 和 n01～n10 的 16 份分解沿用历史缓存。

## 具体失败机制

1. **p1 的增强融合改变了保护锚点。** 该题询问 RAG 的生成器和参数量。Gold 750 在原流程候选中全局只排第 17，但正好是原始 RRF 首条，因此被保护到最终第十。开启增强后，融合首条变为 Self-RAG 的 986，750 虽仍在候选池，却失去保护并离开 Top-10，Recall 从 1 变成 0。这定位到锚点选择和证据保留，不是 API 没有返回内容。
2. **p6 的补查移除了已覆盖的证据。** 两个指定 Gold 406、597 原本均在十条内；一轮和两轮后只保留 406。候选仍包含 597，问题出在最终选择。
3. **n07 的新增候选没有变成完整上下文。** 合并库 Gold 为 615、761，分别对应原五篇库 237、383。原流程只召回 615 到候选但未选中；第一轮选中 615，Recall 到 1/2；第二轮两段都已在大候选池，却又全部落选，回到 0。四种增强设置均有这个现象。
4. **第二轮也有有限收益。** 新 a13 在第二轮找到 Self-RAG 的段落 995 并保留，Recall 从 0 到 1/3，仍未覆盖 CRAG 的两段 Gold。DCNN/VGG 池化题 a10 一直为 3/3，没有因增强增加收益。
5. **来源识别仍有缺口。** a09、a15 用 Transformer 简称，现有基于文件名和标题的别名规则未映射到 `Attention is all you need.pdf`，因此没有按双来源触发补查。这是实测边界，本轮未修改识别规则或题目措辞。

## 采用门槛与下一步

实验前固定的检索门槛全部未通过：总体 MAP 至少增加 0.01、八道新跨篇 Recall 至少增加 0.10、各旧题组 Recall 不下降、各旧题组 MAP/MRR 下降不超过 0.01。实际总体 MAP 下降约 0.0102，新跨篇 Recall 仅增加 0.0417，旧六题 Recall 1.0 降到 0.75。

因此保留生产默认：重写关闭、HyDE 关闭、补查关闭，当前默认库仍是三篇版本。完整八篇库与显式实验入口保留，可以随时用同一组输入回放。

下一步建议只做一轮有边界的证据保留修复：先保护**增强前**原问题的检索锚点，再单独验证补查是否保留每个子题的关键首条。沿用本轮全部缓存、同一题集与门槛离线复评；收益不稳定就保留当前流程。不要把 Gold 输入运行时作为选证据条件，也不将这次论文导入等同于已经实现这些论文的方法。

## 运行成本与已验证边界补充

- 四种模式各有 13 题触发补查，每组 26 次处理、50 次来源定向查询。其他题按启发式跳过；不是所有题固定运行两轮。
- 实际重排推理为 14,379 对，重复的 45,364 对 query-passage 分数被共享复用。42 个分题的检索处理耗时合计 761.258 秒，约 12.69 分钟；不是逐组服务延迟。
- 默认知识库指针、旧三篇和五篇配对资产、旧题 / Gold、私有配置及 `main.py` 未改。新增生产代码只扩展原 evaluation 的显式对照入口，新增两个本地行为测试；构建和实验脚本归档在本次结果目录。

## 真实主流程与人工语义复核

预先固定 p3、n07、a10、a12，逐题真实运行 `main.main` 的 base/0 和 both/2，共八次；只重放已生成的分解 / rewrite / HyDE，最终回答实际调用 API，没有用假答案代替。所有八次选证据编号都与 evaluation 相同，引用结构通过 8/8，没有触发引用修复。

| 题目 | 原流程 | 重写 + HyDE + 两轮 | 人工核对 |
| --- | --- | --- | --- |
| p3 ColBERT MaxSim 聚合 | 核心答全 | 核心答全 | 每个查询 token 对文档 token 取最大相似度，再对查询 token 求和；有额外但受支持的距离度量说明 |
| n07 RAG / ColBERT 预计算表示 | 部分回答 | 部分回答 | ColBERT 的替代原文可支撑；RAG 缺主要预计算段落，两轮后仅多了索引向量放在 CPU 的附录段落 |
| a10 DCNN / VGG 池化 | 核心答全 | 核心答全 | 窗口、步幅及 DCNN 重叠池化正确；VGG 非重叠关系措辞保守，含少量未要求的补充 |
| a12 DPR / ColBERT 权重共享 | 部分回答 | 部分回答 | ColBERT 共享 BERT 正确；未选中 DPR 独立编码器原文，两组均对 DPR 部分保留证据不足 |

两种条件都是四题中两题核心完整、两题部分完成，没有观察到增强带来的完整回答提升。这是人工、同语料、小样本核对，不能称作总体准确率 50%；引用结构通过也不等于语义全对。运行时并未使用 Gold 或 reference_points。

真实回答新增 API 8 次、17,934 token；整轮实际 chat 调用 **118 次、61,719 token**（输入 56,650、输出 5,069），全部 `finish_reason=stop`，失败 0、自动重试 0、引用修复 0。没有根据 token 推算代理账单金额。

## 最终核验

- 64 项单元 / 本地行为测试通过，新增真实候选隔离与不完整 HyDE 缓存拒绝检查。
- 独立实现重新映射全部 42 道 Gold、重算 1,008 组逐题指标及所有分组汇总，全部一致。
- 八次实际 main 选证据结果与 evaluation 完全一致；人工答案复核单独留档。
- 合并前后的所有分块正文 / 元数据和向量逐条一致，仅新库的位置 ID 有映射；九个最早迁移数据文件仍与原清单 SHA 一致。
- 旧三篇 / 五篇版本、当前指针、旧题与 Gold、私有配置、`main.py` 均保留；实验日志与快照未发现配置中的 Key。
- 源码只扩展原 evaluation 的显式对照入口及两个对应测试；未提交或推送 Git。

## 操作与产物

检查已保存的 `comparison.json` 即可查看全部指标，无需再次付费。原 evaluation 的离线回放命令如下，重新执行仍会消耗本机 CPU，结果目录须使用新名称：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m evaluation.run_evaluation \
  --questions evaluation/all_papers_questions_en.json \
  --kb-version all-papers-8-20261020 \
  --auxiliary-cache evaluation/results/all_papers_20261020/auxiliary.json \
  --query-ablation --complete-evidence --completion-rounds 1 2 \
  --output-dir evaluation/results/new_all_papers_replay
```

本次分题驱动还在 Python 中设置了 torch intra/inter-op 单线程，复用同一组 Embedding/BGE 模型与相同 query-passage 分数；其入口和完整日志一起归档。

在新的 Python 进程中临时查看“两个增强都开启、最多两轮”的真实问答，可使用下列调用；它会重新调用 API，当前无需重复执行：

```python
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
import main
main.USE_MULTI_QUERY = True
main.USE_HYDE = True
main.main(
    "Do DPR and ColBERT share BERT weights between their question or query encoder and document encoder?",
    kb_version="all-papers-8-20261020",
    complete_evidence=True,
    completion_rounds=2,
)
```

- [冻结协议](../evaluation/results/all_papers_20261020/protocol.json)、[全部 PDF 清单](../evaluation/results/all_papers_20261020/inventory.json)、[分块 ID 映射](../evaluation/results/all_papers_20261020/chunk_id_mapping.json)。
- [完整英文题集](../evaluation/all_papers_questions_en.json)、[Gold 页码与映射预检](../evaluation/results/all_papers_20261020/gold_preflight.json)。
- [全部逐题量化与汇总](../evaluation/results/all_papers_20261020/comparison.json)、[案例变化诊断](../evaluation/results/all_papers_20261020/diagnostics.json)。
- [辅助 API 审计](../evaluation/results/all_papers_20261020/api_calls.json)、[真实回答 API 审计](../evaluation/results/all_papers_20261020/answer_probe/api_calls.json)、[人工答案复核](../evaluation/results/all_papers_20261020/answer_probe/review.json)。
- [独立验证](../evaluation/results/all_papers_20261020/verification.json)、[测试日志](../evaluation/results/all_papers_20261020/tests_initial.log)、[本次文件差异](../evaluation/results/all_papers_20261020/task_changes.patch)。
