# run_evaluation 检索量化评估

本篇保留优化前的中文 Top-5 基线。后续已完成英文题集、Top-5/10/20 对照与主流程评估对齐，最新结果见[英文检索优化日志](RETRIEVAL_OPTIMIZATION_2026-10-19.md)。

2026-10-19。按用户澄清，实际运行项目原有的 `evaluation/run_evaluation.py`，输出 Precision@5、Recall@5、MAP@5、MRR@5。此前[问题分解修复日志](DECOMPOSITION_EVALUATION_2026-10-19.md)中的七题运行是 `run_answer_evaluation.py` 的答案评估，两者分开记录。

**本轮七种方法中，改写后检索再重排最好：Recall@5 = 0.5000，MAP@5 = 0.3889，MRR@5 = 0.3889。分解组 Recall@5 = 0.2500，未超过普通混合重排。当前检索分数仍有明显提升空间。**

## 本轮做了什么

- 为原入口增加可选 `--questions`，使其可评价五篇论文题集；不传参数仍使用原有 `evaluation/questions.json`。
- 原有七组方法、检索预算和评分函数保持不变：Dense/BM25 各取 20，RRF 保留 20，最终评价前 5，RRF 的 k 为 60。重排器仍是 CPU 上的 `BAAI/bge-reranker-base`。
- 明确指定 `arxiv-pilot-5-20261019`：RAG、DPR、ColBERT、Self-RAG、CRAG 五篇，共 1,019 个分块；题集使用 `evaluation/arxiv_pilot_questions.json`。
- 保存原入口快照和 32 个相关文件的运行前哈希。审计包装器调用真实 `evaluation.run_evaluation.main()`，只观察并保存 API、逐题 ID 和分数，不替换检索结果或模型输出。
- 没有重复生成七题答案；本次 API 仅用于分解和改写。

六道可答题的所有 Gold 引文都匹配成功，Gold 片段集合分别为 p1 `[372]`、p2 `[28]`、p3 `[219]`、p4 `[587]`、p5 `[873]`、p6 `[28, 219]`。p7 没有 Gold，按原脚本规则跳过，**没有计为答对**。

## 汇总分数

每项均是六道有 Gold 问题的平均值，数值越大越好。

| 方法 | Precision@5 | Recall@5 | MAP@5 | MRR@5 |
| --- | ---: | ---: | ---: | ---: |
| Dense | 0.0333 | 0.1667 | 0.1667 | 0.1667 |
| BM25 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Hybrid | 0.0333 | 0.1667 | 0.0417 | 0.0417 |
| Hybrid + Reranker | 0.0667 | 0.2500 | 0.1944 | 0.2222 |
| Rewritten Hybrid + Reranker | **0.1000** | **0.5000** | **0.3889** | **0.3889** |
| Multi-Query + Reranker | 0.0667 | 0.3333 | 0.2222 | 0.2222 |
| Decomposition + Hybrid + Reranker | 0.0667 | 0.2500 | 0.1875 | 0.2083 |

在这次同题方法对照中，改写后检索重排相较普通 Hybrid + Reranker，Recall@5 从 25% 到 50%，MAP@5 从 0.1944 到 0.3889。但不是所有题都改善，不能据此直接打开主流程的默认改写开关。

### 逐题 Gold 召回

| 题目 | Hybrid + Reranker | 改写后检索重排 | 分解后检索重排 |
| --- | ---: | ---: | ---: |
| p1 RAG 生成器与参数 | 0/1 | 0/1 | 0/1 |
| p2 DPR 相似度 | 1/1 | 1/1 | 1/1 |
| p3 ColBERT MaxSim | 0/1 | 1/1 | 0/1 |
| p4 Self-RAG tokens | 0/1 | 1/1 | 0/1 |
| p5 CRAG 判断 | 0/1 | 0/1 | 0/1 |
| p6 DPR / ColBERT 比较 | 1/2 | 0/2 | 1/2 |

改写组在 p3 把 Gold 219 排到第三、p4 把 Gold 587 排到第一；p6 却丢掉了普通混合重排已有的 DPR Gold。分解器在 p6 实际接受四个子问题，证明上轮校验修复生效，但原评估分支最终仍只保留 DPR 片段，没有取得双篇 Gold 全覆盖。

## 如何解读

- **Precision@5**：前五条中有多少属于预设 Gold。每题只标一个或两个 Gold 片段，所以这组题即使全部召回，平均 Precision@5 的理论上限也是 **0.2333**。
- **Recall@5**：预设 Gold 有多少进入前五条，是本轮需要优先关注的指标。低 Precision 上限不能解释低 Recall；当前最佳 Recall 仍只有 50%。
- **MAP@5 / MRR@5**：同时关注 Gold 排得是否靠前。AP 继续使用原函数，以该题全部 Gold 片段数量作为分母，没有调整公式提高分数。
- 这是指定片段匹配评价；一个片段承载多条短引时只算一个 Gold。包含等价答案的其他段落没有自动计分。该局限保留，没有修改 Gold 或把替代段落补成正确答案。
- **这是修复后代码上的方法对照，不是修复前后对照。** 原评估的分解分支只合并子题候选，再按原问题全局重排；它尚未使用 `main.py` 的子题局部 Top-3 优先及首条保护策略。主流程候选为 Top-60、最终 Top-10，不能拿本表直接声称当前主流程修复有效或无效。
- 原三篇库的历史成绩使用其他题集和语料，不与本表相减计算收益。这六道题是开发题，尚未验证泛化。

优先后续工作是让评估覆盖当前主流程的选证据策略，在相同题集、候选和最终条数下做前后对照；再检查 p1/p5 漏掉指定 Gold、改写使 p6 退步的原因，并增加独立跨篇题。

## Mac 运行与用量

本轮使用已缓存模型、CPU、受控单线程，脚本运行约 **48.81 秒**，含模型加载、检索重排及辅助 API 调用；这不是单查询性能基准。

| API 用途 | 次数 |
| --- | ---: |
| 问题分解 | 6 |
| 查询改写 | 6 |
| 答案生成 / 引用修复 | 0 |
| 合计 | **12** |

代理报告输入 **5,356**、输出 **339**、合计 **5,695 token**。全部响应正常 `stop`，没有重试；返回模型为 `deepseek-v4.1-flash`，不据此推断金额。

复现时，在项目根目录执行以下命令会重新调用 API；原始结果已保存，无需为查看分数重复运行：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -u -c "import runpy, torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); runpy.run_module('evaluation.run_evaluation', run_name='__main__')" \
  --questions evaluation/arxiv_pilot_questions.json \
  --kb-version arxiv-pilot-5-20261019
```

## 验证与产物

独立从逐题 ID 重算六题 × 七方法共 42 组结果的四项指标，全部匹配；七张原脚本 stdout 汇总表与 JSON 保留四位小数后一致。AST 比对确认原检索与评分辅助函数未变。32 个运行前登记文件中，仅 `run_evaluation.py` 为可选题集参数发生改动；其余 31 个保持原哈希，包括题集、Gold、两套索引、主流程和 API 私有配置。当前默认库仍为 `semantic-mac-20261019`。未提交或推送 Git。

- [原脚本完整输出](../evaluation/results/retrieval_metrics_20261019/run_evaluation.log)
- [逐题分数、改写/分解响应、API 用量及配置](../evaluation/results/retrieval_metrics_20261019/results.json)
- [独立核验](../evaluation/results/retrieval_metrics_20261019/verification.json)
- [审计运行入口](../evaluation/results/retrieval_metrics_20261019/run_audited.py)
- [修改前的原入口](../evaluation/results/retrieval_metrics_20261019/before_run_evaluation.py)

报告和产物已检查不含配置中的 API Key。本轮没有修改算法或新增测试；验收依据是原入口的实际完整运行、逐题指标重算及基线哈希核对。
