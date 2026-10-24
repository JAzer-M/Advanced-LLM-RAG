# 英文检索优化与 Top-k 量化日志

后续已完成十二道新题及闭卷/原文/无关证据对照：新十道可答题 Recall@10 为 0.4833，两个轻量排序未有稳定收益，保留原排序。本文六道开发题的全覆盖不代表泛化，最新结论见[新题验证日志](INDEPENDENT_VALIDATION_2026-10-19.md)。

2026-10-19。接续[原 run_evaluation 跑分](RETRIEVAL_EVALUATION_2026-10-19.md)。按用户要求使用英文问题，比较最终证据数 5、10、20，优化检索，并以原文证据而非 DeepSeek 回答流畅度验收。使用 Karpathy 规范及 Matt Pocock diagnosing-bugs：固定输入、失败复现、阶段排名定位、最小改动、成对回放；没有新增运行依赖。

**六道英文开发题的原始 Gold 均进入当前主流程实际返回的 Top-10。相同英文问题、相同分解候选池、相同十条预算下，Recall 从 0.6667 到 1.0000，MAP 从 0.3542 到 0.3998。** 这代表这六题的指定证据覆盖，不是答案准确率或泛化能力。关键片段仍排在列表后部，排序质量尚有提升空间。

## 如何排除“只靠生成模型答对”的混淆

- 主分数由实际检索 ID 与固定 source/page/quote 匹配得到的 Gold ID 计算。Precision、Recall、AP、RR 及平均公式没有修改，不使用 LLM 自评。
- 本轮最终答案 API 调用为 **0**。原问题 Dense/BM25/混合检索组也不需要辅助生成 API，可独立查看。
- DeepSeek 仅用于生成分解/改写查询，所有查询和响应都保留。Gold/reference_answer 未输入辅助模型；核验全部 14 个提示均没有包含预设 Gold 短引。
- 最终数值实验使用固定辅助查询离线回放，并硬性禁止 API。它证明实际找到了对应原文，不能单独判断此前某个生成答案究竟依靠上下文还是模型原有知识；后者需要另做有/无证据的生成对照。

## 基线、数据与复现失败

- 知识库始终为 `arxiv-pilot-5-20261019`，五篇、1,019 块、384 维。没有重建索引、换模型或修改旧 Gold。
- 英文题集复用先导实验已有六题翻译，补一题英文缺证据题，共七题；与中文题集的 Gold 完全一致。p7 无 Gold，跳过且不计为正确。英文题是诊断开发集，不是独立测试集。
- 同算法、同每路 20 个候选、同最终 5 条时，普通混合重排的 Recall：旧中文 0.2500，英文 0.6667。这一部分收益应归于语言变化，不能归于新代码。
- 冻结基线后执行 `baseline_probe.py --assert-complete`，英文 Top-10 完整覆盖断言实际失败；[失败日志](../evaluation/results/retrieval_optimization_20261019/baseline_probe.log)和[逐阶段基线](../evaluation/results/retrieval_optimization_20261019/english_before.json)保留。
- 集成回归测试复现评估与主流程不一致：同一组四子题，旧评估丢掉两条子题首要证据，输出末尾 8、9，预期应保留 10、11。[测试失败输出](../evaluation/results/retrieval_optimization_20261019/alignment_red.log)保留。

## 修改与依据

### 1. 统一评估与主流程的选证据实现

`src/reranker.py` 提供普通函数 `rank_evidence`、`select_evidence`，`main.py` 和 `evaluation/run_evaluation.py` 都调用它们。全局重排、各子题局部 Top-3、首条保护、规范片段 ID 和最终预算采用同一实现。保留“仅全局重排”和“没有原 RRF 保护”的对照行。

评估默认最终条数从 **5 改为 10**，每路 Dense/BM25 及 RRF 候选从 20 改为 **60**，与现有主流程一致；主流程原本已经是 60→10。CLI 支持同时比较 `--top-k 5 10 20` 和显式指定 `--candidate-k`。

### 2. 保留原问题 RRF 的第一条，防止重排丢失已找到的证据

英文 p1 的参数段落 372 已在原问题 RRF 排第一，却被 Cross-Encoder 降到第 14；分解合并后进一步降到第 19。继续增加候选没有解决它。

最终在同一个十条预算中保留原 RRF 首条，再保留各子题首条、优先填充子题局部前三，最后按全局顺序补齐。该规则使用检索排名，不检查 Gold，也没有按论文名或题号写特殊分支。最终仍按原问题全局顺序排列，不直接混比不同子题的分数。

这让 p1 指定参数段落进入最终第十位；排序仍不理想，但不会再从上下文中丢失。

### 3. 分解同时保留比较维度与向量检索术语

第一轮真实英文响应把跨篇题拆成两个复合子题，合并了表示与打分。第一次提示修订得到四子题，但泛化的“perform relevance scoring”仍找不到 ColBERT 指定段落，原始中间结果完整保留，未记成功。

随后进行零 API 的术语对照：相似度明确为 question/passage vectors 时 DPR Gold 排第一；ColBERT 的 query/document embeddings similarity 查询使 Gold 进入 RRF 第四、局部重排第三。[术语探针](../evaluation/results/retrieval_optimization_20261019/term_probe.json)。

最终提示增加通用规则：按实体 × 比较维度拆分，上限四个；表示问题保留 vectors/embeddings，打分问题表达为 query/document similarity；禁止预设具体打分函数。没有把 dot product、MaxSim 或任何 Gold 答案写进分解规则。

只对 p6 在两次明确提示变更后各重新生成一次分解；其他五题的分解与六个改写始终复用首轮响应，没有反复采样选高分输出。最终 p6 的 ColBERT Gold 进入合并候选池，但在全局排序仍仅第 35；DPR Gold 第 51。子题局部优先选择最终将它们保留在第 8、9 位。

## 同候选池、同最终十条的对照

下面各行复用相同最终英文辅助查询与真实模型排名，原问题及每个子题均使用 60 个候选；合并去重池大小也相同。只比较选证据策略，不把更多子题带来的额外总候选数当作策略收益。

| 策略 | Precision@10 | Recall@10 | MAP@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| 相同分解候选，仅全局重排 | 0.0667 | 0.6667 | 0.3542 | 0.3542 |
| 子题证据保留 | 0.1000 | 0.8333 | 0.3869 | 0.3780 |
| 子题保留 + 原 RRF 首条保护 | 0.1167 | 1.0000 | 0.3998 | 0.3917 |

六题各自的指定 Gold 覆盖为：

| 题目 | Gold 覆盖 | 在实际返回 Top-10 中的位置 |
| --- | ---: | --- |
| p1 | 1/1 | 372: 第10位 |
| p2 | 1/1 | 28: 第1位 |
| p3 | 1/1 | 219: 第8位 |
| p4 | 1/1 | 587: 第2位 |
| p5 | 1/1 | 873: 第2位 |
| p6 | 2/2 | 28: 第9位, 219: 第8位 |

## 最终证据预算 5、10、20

以下固定每路候选 60、固定辅助查询与模型，分别按各预算执行真实选证据策略。

| 最终证据条数 | Precision@k | Recall@k | MAP@k | MRR@k | 平均原文正文字符数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5 | 0.1667 | 0.7500 | 0.3833 | 0.4000 | 1987 |
| 10 | 0.1167 | 1.0000 | 0.3998 | 0.3917 | 3972 |
| 20 | 0.0583 | 1.0000 | 0.3771 | 0.3727 | 7729 |

**保留默认 10。** 本轮 20 条没有再提高指定证据召回，正文约为十条的 1.95 倍；字符数不等于 token 数，也不含来源头及证据提示。更长上下文会增加后续生成输入，但本轮没有为此调用答案 API。

这里每个预算独立选证据，并非对同一个长排序依次截断：十条结果的前五条不一定等于五条预算的结果，因此 MAP/MRR 可能随预算增大下降。另保存了[固定返回列表的标准前缀指标](../evaluation/results/retrieval_optimization_20261019/fixed_ranking_prefix_metrics.json)，避免混淆：**实际 Top-10 列表的前五条 Recall 为 0.5000，完整十条才达到 1.0000**。p1 在第十、p6 在第八/九，说明后续仍需改进排序。

每题只有一至两个指定 Gold，因此平均 Precision@10 的理论上限为 0.1167、@20 为 0.0583。没有把未标注的等价段落补进 Gold 来提高分数。

候选预算也单独对比：同最终十条，20 个候选的当前策略 Recall=0.7500，60 个候选为 1.0000。扩大候选会引入干扰并增加 CPU 工作，不能只扩候选而不检查排序。受控单线程、已加载缓存模型下，包含全部方法的离线六题批次约 31.48 秒与 88.28 秒，不能当作单次生产问答延迟。

## 新题验证与旧库回归

新增五道英文验证题，每篇一题，Gold 与原开发题的片段不重叠，问 RAG-Token 文档粒度、DPR 段落单位、ColBERT 实验配置、Self-RAG 训练标记、CRAG evaluator。题目在验证运行前保存，未根据成绩修改。它们由本轮手工编写，规模小，不宣称严格盲测或总体能力。

- 新五题原问题检索：无保护和加入原 RRF 保护时，Top-10 均 Recall=1.0000、MAP=0.8000，逐题四项指标相同。这只验证原问题路径与 RRF 保护，**没有为新题调用分解 API**，不能用于证明新分解提示的泛化。
- 原三篇库五道有 Gold 题：Top-10 前后 Recall=0.8417、MAP=0.5814、MRR=0.7667，逐题四项指标相同；第六道无 Gold 跳过。未重跑旧题生成。
- 实际 `main.py` 的 p6 用同一份分解、真实 CPU 模型回放检索，明确跳过生成；最终十个 ID 与 evaluation 完全一致。[主流程检索核验](../evaluation/results/retrieval_optimization_20261019/main_p6_final_replay.json)。不冒充新生成的答案。
- 当前 **47 项测试通过**；覆盖评估对齐、Top-k 预算、多预算不重复调用辅助查询、缓存问题匹配、离线回放及 RRF 首条保护。

## 调用、保留范围与复现

本轮新辅助 API 共 **14 次**：首轮六次分解 + 六次改写，以及 p6 两次提示修订后的单次分解。输入 **6,566**、输出 **494**、合计 **7,060 token**，全部正常 stop，无自动重试。不据此推断金额。最终答案调用为零；全部 Top-k、预算、新题及旧题回放 API 为零。

独立从 ID 重算 **510 组逐题结果**的四项分数，全部一致。33 个登记基线文件保持原哈希；改动只涉及主流程、重排/选择、分解提示、评估入口及对应测试。私有 API 配置、原题集/Gold、两套索引和默认库指针保留，默认仍是 `semantic-mac-20261019`。没有提交或推送 Git，也未新增运行依赖。

在项目根目录复现本次最终参数，使用新结果目录：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -u -c "import runpy, torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); runpy.run_module('evaluation.run_evaluation', run_name='__main__')" \
  --questions evaluation/arxiv_pilot_questions_en.json \
  --kb-version arxiv-pilot-5-20261019 --candidate-k 60 --top-k 5 10 20 \
  --auxiliary-cache evaluation/results/retrieval_optimization_20261019/auxiliary_final.json \
  --output-dir evaluation/results/new_english_run
```

带缓存不新调用 API；去掉 `--auxiliary-cache` 会生成新分解/改写，结果可能变化。`--no-auxiliary` 只评估原问题路径，完全不调用辅助 API。缓存用于固定输入对照，修改提示不会自动更新旧缓存。本轮最终缓存保留五题首轮结果，仅更新 p6，来源见审计响应。

- [最终 60 候选的全部方法与逐题指标](../evaluation/results/retrieval_optimization_20261019/verified_english_60/results.json)
- [20 候选对照](../evaluation/results/retrieval_optimization_20261019/verified_english_20/results.json)
- [新题验证](../evaluation/results/retrieval_optimization_20261019/validation_60/results.json)、[旧库回归](../evaluation/results/retrieval_optimization_20261019/legacy_60/results.json)
- [总核验及 API 用量](../evaluation/results/retrieval_optimization_20261019/verification.json)、[原始测试输出](../evaluation/results/retrieval_optimization_20261019/tests_final.log)

本轮尚未验证新代码的真实最终生成质量、无证据/错误证据时的生成依赖程度、新分解提示在独立跨篇题上的泛化，以及默认多线程稳定性。后续应先增加跨篇验证题并改善关键证据前排率，再继续扩论文数量。
