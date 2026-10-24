# 三轮补查上限实验与查询增强建议

2026-10-19。用户要求判断是否开启重写/HyDE，并尝试三次补查观察效果。本轮实现上限三轮并使用原 `evaluation/run_evaluation.py` 对照 0、1、3 轮；生成 API 调用被显式禁止。

**结论：三轮上限已实现，26 道可答题的 0/1/3 轮量化对照完成。新十题 Recall@10 为 0.4833/0.6000/0.5500，三轮低于一轮，旧六题退步也没有恢复。补查仍默认关闭；重写与 HyDE 继续关闭。** 62 项本地测试通过，项目生成 API 调用 0，没有实际答案生成验收。

## 重写与 HyDE 的选择

继续保留 `USE_MULTI_QUERY=False`、`USE_HYDE=False`。历史三题实际消融中，“原查询+重写融合”与 base 三题的最终十条相同；HyDE 只替换一题第十条，没有补到关键证据。旧量化曾显示“只用重写查询”有收益，但它与 main 的融合开关不同，不能据此直接打开主流程开关。依据是[历史消融记录](REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md)，不是本轮重新运行的消融，也不表示两种方法普遍无效。

当前问题集中在细节证据未召回、最终十条丢失已召回证据。本轮保持两个开关关闭，单独观察增加补查预算的变化。旧六题的辅助缓存仍保留历史 rewritten_query 控制行，未产生新重写；0/1/3 轮主比较均从原问题和同一批分解出发。

## 三轮实际如何实现

- 保留已有函数、字典和列表风格，新增普通函数 `complete_evidence(..., max_rounds=1)`，原 `complete_evidence_once()` 作为一轮兼容入口保留。
- 第一轮与之前固定方案相同：只处理明确涉及两篇以上论文且有覆盖信号的问题，最多四个任务；已有候选可仅重选，来源/保留数量不足时进行限定论文检索。
- 第二、三轮针对同一批任务，将各论文 Dense/BM25 与 RRF 深度由 60 加到 120、180，实际不超过该论文块数；问题文本不变，不调用模型产生新查询。每一轮最多四次定向查询，总计最多十二次。
- 保留全部首次与已补查候选，只给新加入的片段计算原问题下的 BGE 分数；按子问题重新计算各论文局部前三条，最终选择规则仍为全局前半预算、原 RRF 首条、任务首条、其余按全局填充，最终仍十条。
- 记录 `(query, source, effective_depth)`，相同检索计划不重复执行。后续轮没有新候选时停止；论文已取完导致下一计划重复时也停止，不机械凑够三轮。
- `round_history` 保存每次处理的深度、新候选、选中 ID、实际查询数和耗时；`completed_passes` 是处理次数，`rounds` 是实际含检索的轮数。因此只重选、不检索的第一步不计入实际检索轮数。

**这次同时增加了轮数上限和候选深度，是分轮加深候选实验。** 没有单独比较“一次就取 180”与“三次逐渐取到 180”，因此效果变化不能独立归因于轮数。也没有新增 LLM 语义缺口判断、动态改写、HyDE、联网或完整 Agent。

只在起点通过旧覆盖规则的题上继续加深，单篇题仍可能被跳过；来源/段落数量依然不是事实支持的证明。

## 固定条件与验收

运行前保存本地源码/文档快照和数据、Gold、默认库、私有配置及上一轮结果的哈希。私有配置仅记录哈希，不复制密钥内容。[预先固定的协议](../evaluation/results/completion_rounds_20261019/protocol.json)。

使用与一轮实验相同的四套题：新十道可答题、旧六题、旧五道验证题及旧三篇库五题，共 26 道。新题来自同五篇论文的手工验证集，不是外部盲测；n08 原题歧义保留。所有无 Gold 题跳过，不计为正确。

0、1、3 轮共享第一次检索和第一轮处理；1 轮结果取同一次轨迹的第一个检查点。原方法与一轮结果须逐题完全复现上一轮 ID 和指标。新跨篇 Recall 至少较 0 轮 +0.10；新题 MAP/MRR 下降不超过 0.01；每套旧题 Recall 不下降、MAP/MRR 下降不超过 0.01。只运行这一种深度计划，观察后不调参。

## 实测结果与决定

新十道计分题，同一知识库、原问题、分解缓存、模型与最终十条预算：

| 指标 | 不补查 | 最多一轮 | 最多三轮 |
| --- | ---: | ---: | ---: |
| Precision@10 | 0.0700 | 0.1000 | 0.0900 |
| Recall@10 | 0.4833 | 0.6000 | 0.5500 |
| MAP@10 | 0.2144 | 0.2367 | 0.2252 |
| MRR@10 | 0.3061 | 0.3272 | 0.3161 |
| 其中跨篇 Recall@10 | 0.2222 | 0.4167 | 0.3333 |

单篇 Recall 仍 0.8750；三种条件完整指定 Gold 均为 4/10，跨篇完整覆盖均为 1/6。这是检索指标，不能换算成生成答案准确率。

旧题回归：

| 题集 | 不补查 Recall | 一轮 Recall | 三轮 Recall | 三轮 MAP | 三轮 MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| 旧六题 | 1.0000 | 0.9167 | 0.9167 | 0.3792 | 0.3875 |
| 旧五验证题 | 1.0000 | 1.0000 | 1.0000 | 0.8000 | 0.8000 |
| 三篇库五题 | 0.8417 | 0.8667 | 0.8667 | 0.5931 | 0.7667 |

三套旧题三轮的全部汇总指标与一轮相同。26 题中，没有一题的最终三轮指定 Gold Recall 高于一轮。三轮相对不补查仍有新题局部收益，但相对一轮没有新增收益，且旧题门槛失败，不默认采用。

### 更多候选为什么没有变成更多有效证据

- n05：每轮新加入 76、119、86 块，但指定证据仍是原有两块，指标不变。第一轮前已经完整覆盖 Gold，后续加深增加了工作量。
- n06：一轮与三轮仍命中 2/3；DPR loss 段落 36 从最终第五退到第九，AP 从 0.4667 降到 0.4074。
- n07：一轮保留的 ColBERT 段落 237 在后续轮次被排除，最终从 1/2 降到 0/2。RAG 的 383 和 ColBERT 的 237 都在候选池，最终选择仍没有保留。
- n09/n10：加深后的候选池中包含指定证据，但最终仍未命中。这一结果把问题进一步指向最终排序/选择，而不只是候选数量不足。
- 旧 p6：三轮仍只命中 28，219 未恢复，题目 Recall 仍 0.5，导致旧六题宏平均为 0.9167。

逐轮 Gold 位置仅用于事后审计，运行没有读 Gold；见[逐轮证据位置](../evaluation/results/completion_rounds_20261019/round_gold_review.json)。当前结论只针对这个固定分轮加深方案，没有否定带有效新查询或语义缺口判断的其他多轮方法。

### 运行成本和核验

- 26 道可答题中 18 道没有触发补查，8 道执行三次处理。本题集没有在第三次处理前提前停止；重复计划和无新候选提前停止由本地测试验证。
- 上述八题实际有检索的轮数在 2～3 轮之间，n06/n09 第一次只重选。合计 60 次来源定向查询，一轮对照为 11 次；单题最多十次，低于十二次上限。
- 额外第二/三次处理的耗时，在八道受影响题中位数约 **57.13 秒**。四套 evaluation 合计约 **791.0 秒（13.18 分钟）**，不含模型首次加载。当前 CPU、受控单线程条件下测得，非生产服务 P95；时间包含其他对照方法。
- 62 项测试通过：原 58 项加三轮深度/十条预算、无新增候选停止、重复有效深度停止、非法轮数四项。[本地测试记录](../evaluation/results/completion_rounds_20261019/tests_final.log)。
- 原方法与一轮方法所有逐题 ID、四项指标完全复现上一轮，避免第一轮被悄悄改变。独立脚本重新计算全部逐题指标和汇总，并核对候选池只增不减、检索签名唯一、逐轮与总查询上限、检查点对齐。
- 主流程同样接入 `completion_rounds=3`；真实主流程检索回放复用冻结分解，并用占位生成器核对与 evaluation 的最终 ID 一致。[主流程回放](../evaluation/results/completion_rounds_20261019/main_replay.json)是检索集成检查，不是实际生成验收。
- 项目生成 API 调用 **0**；没有改写/HyDE 新调用、最终答案调用或引用修复调用。没有改 Gold、索引、默认库、API 私有配置、生成提示或证据账本。

完整表格与成本见 [comparison.json](../evaluation/results/completion_rounds_20261019/comparison.json)。原始结果：[新题](../evaluation/results/completion_rounds_20261019/new/results.json)、[旧六题](../evaluation/results/completion_rounds_20261019/old_core/results.json)、[旧验证题](../evaluation/results/completion_rounds_20261019/old_validation/results.json)、[三篇库](../evaluation/results/completion_rounds_20261019/old_three_papers/results.json)。

**保留结论：重写关闭、HyDE 关闭、补查默认关闭。三轮能力作为显式实验入口保留，不继续增加轮数或参数搜索。**

## 使用方法

主流程显式开启三轮上限：

```python
from main import main

result = main(
    "What document representations are precomputed and stored for retrieval or indexing in RAG and ColBERT?",
    kb_version="arxiv-pilot-5-20261019",
    complete_evidence=True,
    completion_rounds=3,
)
```

正常 main 会调用分解/生成 API；本轮检索评测不会。省略新参数时继续默认一轮上限，省略补查开关时继续沿用关闭状态。五篇库显式指定，不切换当前默认三篇库。

使用固定缓存比较 1、3 轮，原流程 0 轮仍作为原方法行输出：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -u -c "import runpy, torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); runpy.run_module('evaluation.run_evaluation', run_name='__main__')" \
  --questions evaluation/arxiv_next_questions_en.json \
  --kb-version arxiv-pilot-5-20261019 --candidate-k 60 --top-k 10 \
  --auxiliary-cache evaluation/results/independent_validation_20261019/auxiliary.json \
  --complete-evidence --completion-rounds 1 3 \
  --output-dir evaluation/results/new_rounds_run
```

输出请使用新目录。完整四套入口为 [run_comparison.py](../evaluation/results/completion_rounds_20261019/run_comparison.py)，以前的一轮日志和成绩保持原样。
