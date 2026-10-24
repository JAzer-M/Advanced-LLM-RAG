# 问题分解修复与 evaluation 日志

2026-10-19。接续[五篇论文先导实验](ARXIV_PILOT_2026-10-19.md)，修复四个子问题被丢弃、跨论文证据漏选、中文拒答及引用格式问题。使用 Matt Pocock diagnosing-bugs 建立真实响应回放和失败测试，按 Karpathy 规范限定改动；未增加运行依赖。

本文的七题 evaluation 使用 `run_answer_evaluation.py`，属于答案评估。用户澄清需要原 `run_evaluation.py` 的量化检索分数后，已另行实际运行；七组 Precision/Recall/MAP/MRR@5、逐题结果及用量见[检索量化评估日志](RETRIEVAL_EVALUATION_2026-10-19.md)。

**主要结果：跨篇题的四个核心要点已齐备，预设关键引文从 1/3 覆盖到 3/3；最终拒答为简短中文。** 完成一轮 7 题真实主流程，再对 4 个输出样例固定证据复核；42 个本地测试通过。仍有少量题外补充与 L2 措辞精度问题，不能把这七题写成总体准确率或严格全通过。

## 基线与对照方式

- 始终使用 `arxiv-pilot-5-20261019`：5 篇、88 页、1,019 片段、384 维。题目、Gold、索引和分块没有改写或重建。
- 默认三篇库仍为 `semantic-mac-20261019`。前一轮结果、索引、指针和 API 私有配置保留；除本轮明确改动的代码外，41 个已登记基线文件哈希未变。
- 先把前轮 p6 的真实四子问题响应固定，在旧/新校验器与真实本机检索模型上回放。分解响应不重新生成，生成步骤使用明确标记的替身，**该对照不调用 API，也不评价生成答案**。
- 再运行七题真实主流程：原有 API 分解、检索、重排、证据整理、生成与引用检查全部执行。后续仅修改输出规则时，对 p1/p3/p6/p7 使用同一份已保存上下文重新生成，不重复分解或检索。
- 核心要点验收标准在调用新 API 前写入 [protocol.json](../evaluation/results/decomposition_fix_20261019/protocol.json)。Gold/reference_answer/评分标准没有传给模型。人工核对真实引用段落，引用编号结构与语义正确性分别判断。

## 修复了什么

### 1. 保留四个合法子问题，显式记录拒绝原因

前轮 p6 返回 `needs_decomposition=true` 和四个合法子问题，旧代码却只接受二至三个，并静默退回“不分解”。真实响应回归测试在旧代码上失败，已保存[失败输出](../evaluation/results/decomposition_fix_20261019/before_tests.txt)。

`src/query_decomposer.py` 现在统一提示和校验上限：接受 **2～4 个有效、不重复的子问题**，去除首尾空白和重复查询。格式错误、空项、超过上限等返回 `status=rejected` 和原因；正常无需分解为 `status=not_needed`，两者不再混为一谈。API 失败仍向上传递，没有隐式重试或额外模型修复调用。

四个上限对应最多 `60 × (1 + 4) = 300` 条融合候选，再按片段去重；并非无限制增加搜索预算。

### 2. 修复“召回了，但最终丢掉”的证据选择

仅放宽四子问题校验后，候选由 60 增至 141，但最终 Top-10 仍缺 ColBERT 的 MaxSim 说明。这一[中间失败结果](../evaluation/results/decomposition_fix_20261019/replay_comparison_validation_only.json)保留，没有把“修复校验”等同于“答案改善”。

对照还发现：新论文来源名是 arXiv 编号，关键片段正文未必出现模型名称；补充清单中已有的论文标题后，ColBERT 打分关键段在对应子问题下升至第三位。单独增加标题仍不足以让原问题的全局 Top-10 覆盖两篇要点。

最终改动：

1. `src/reranker.py` 向重排器提供已有标题；标题已包含在文件名中时不重复添加。Dense/BM25 的索引文本和向量没有改变。
2. `main.py` 对每个子问题的候选做局部重排，取前三条作为优先证据，至少保留每个子问题的首条；其余位置按原问题的全局顺序填充。最终仍最多 **10 个片段**，并保持原问题的全局排序顺序。
3. 不直接比较不同子问题的重排分数。重复片段先映射到去重后的规范 ID，避免同一正文的不同 ID 占用名额或导致少选片段。
4. 结果 JSON 增加 `retrieval_diagnostics`，记录全局 Top-10、子题优先证据、保留 ID 和候选数，可检查具体替换了什么。

### 3. 中文输出、拒答范围和引用别名

- 默认简体中文，明确要求其他语言时遵循问题；术语保持原名。
- 只回答实际要求的范围。资料支持主要区别时直接回答，不因未提问的维度/配置细节先宣称无法回答。
- 完全缺少证据时，简短说明缺什么，不补其他硬件的实验数字。
- 原始七题运行中 p1 输出 `[citation:6]`，旧检查器未把它识别为格式错误；模型修复还保留了该别名。已通过真实输出测试复现。现在检查器会标记该格式；合法范围内的数字别名直接规范为 `[6]`，保持原正文和原来源 ID，保留原始答案，无需模型调用。越界别名不能被静默接受。**格式规范化不证明来源语义正确。**

## evaluation 结果

### 固定真实四子问题响应：前后对照

| 检查项 | 修复前 | 仅修分解校验 | 最终检索策略 |
| --- | --- | --- | --- |
| 执行子问题数 | 0 | 4 | 4 |
| 去重候选数 | 60 | 141 | 141 |
| 最终片段预算 | 10 | 10 | 10 |
| p6 三条预设关键引文进入 Top-10 | 1/3 | 1/3 | **3/3** |
| 两篇的关键证据片段 | 仅 DPR | 仅 DPR | DPR + ColBERT |

DPR 的片段 28 和 ColBERT 的片段 219 在最终列表分别为第 5、第 4 位；片段 219 包含两条预设短引。这个结果来自同一问题、同一响应、同一索引与模型的检索对照，不受重新生成分解结果的影响。[对照 JSON](../evaluation/results/decomposition_fix_20261019/replay_comparison.json)。

质量改善增加了本地计算：在本轮受控单线程、缓存模型的单次离线回放中，旧方案约 **3.12 秒**、新方案约 **19.46 秒**。包含本地检索/重排和证据整理，不含真实 API 或模型冷启动，不能当作服务延迟基准。局部子题重排带来了额外 CPU 工作，最终上下文仍保持十条；当前没有完成这部分性能优化。

### 七题答案与人工核对

“核心要点齐备”与“每一句严格无瑕疵”分开记录。最终答案取四道固定证据复核结果，以及未需复核的 p2/p4/p5 原始完整运行；未覆盖或修改原始答案。

| 题目 | 核对结果 | 最终答案 |
| --- | --- | --- |
| p1 RAG 生成器与参数 | 2/2 核心点；BART-large、406M，引用参数附录。正文约 400M 的预设段落未入选，但附录为直接替代证据 | [p1](../evaluation/results/decomposition_fix_20261019/refined_answers/p1.md) |
| p2 DPR 相似度 | 点积和公式有来源；额外列出其他度量/损失可省略 | [p2](../evaluation/results/decomposition_fix_20261019/answers/p2.md) |
| p3 ColBERT MaxSim | 每查询 token 最大匹配后求和两点齐备；没有再把不同度量选项说成聚合规则的例外，仍有可省略的 GPU 细节 | [p3](../evaluation/results/decomposition_fix_20261019/refined_answers/p3.md) |
| p4 Self-RAG tokens | 四类名称与职责 4/4，对应 Table 1 | [p4](../evaluation/results/decomposition_fix_20261019/answers/p4.md) |
| p5 CRAG 判断 | Correct / Incorrect / Ambiguous 三点齐备，有正文/图注支持 | [p5](../evaluation/results/decomposition_fix_20261019/answers/p5.md) |
| p6 DPR / ColBERT 比较 | **从缺少 ColBERT 打分说明改善为 4/4 核心点齐备**；严格评价保留瑕疵：末尾仍补充了未要求的维度缺证据说明，L2 括号未区分距离与相似度方向，不标为严格无瑕疵通过 | [p6](../evaluation/results/decomposition_fix_20261019/refined_answers/p6.md) |
| p7 本机测速缺失 | 中文简短拒答，没有编造排名/毫秒数，也没有再附其他硬件数字 | [p7](../evaluation/results/decomposition_fix_20261019/refined_answers/p7.md) |

当前六道可答题中五道的全部预设 Gold 出现在生产 Top-10；p1 使用参数附录替代。这个结果包含真实问题分解，与初轮“仅原问题、无 API 分解”的 2/6 指定段落指标不是单变量对照；不拿它们相减宣称准确率收益。核心改进以上面的固定响应 p6 对照和实际答案为依据。

最终七份答案的编号结构检查 **7/7**；这不替代人工语义评价。完整原文、最终答案索引与保留的措辞问题见[人工审阅](../evaluation/results/decomposition_fix_20261019/manual_review.json)。

### 旧库回归与本地测试

旧三篇库的六道原问题离线检索，最终前后 **6/6 道 Top-10 ID 完全相同**。五道有 Gold 的短引命中分别为 6/7、2/2、3/3、5/5、3/8，前后不变；这些旧题并非全部证据齐备，也未重新生成旧六题答案。[旧库对照](../evaluation/results/decomposition_fix_20261019/legacy_retrieval/after/retrieval.md)。

标题处理最初曾使 q1 少命中一条短引，查明是重复加入文件名已有标题。增加去重条件后恢复；对 378 个旧片段验证输入与原始重排器逐字一致，对 1,019 个新片段验证输入与本轮已测新语料逐字一致。[输入等价检查](../evaluation/results/decomposition_fix_20261019/reranker_input_equivalence.json)。

本地测试从 25 项增至 **42 项，全部通过**：新增真实四子题回放、2～4 范围、重复/空项/非法响应及显式拒绝、API 不重试、实际主流程的子题证据保留、固定预算/去重/规范 ID、引用别名与越界、旧标题兼容性。[测试输出](../evaluation/results/decomposition_fix_20261019/final_tests.txt)。

旧题 q6 没有 `gold_evidence` 字段，首次旧库检查因此在出题过程中退出；评估入口改用可选空 Gold 后重跑成功，失败日志与部分结果保留。该失败未调用生成 API。

## 实际用量与复现

| 运行 | 问题数 | 生成 API 次数 | 输入 token | 输出 token | 合计 |
| --- | --- | --- | --- | --- | --- |
| 真实完整主流程 | 7 | 15（7 次分解、7 次回答、1 次旧格式修复） | 17,909 | 1,707 | 19,616 |
| 固定证据输出复核 | 4 | 4 | 7,647 | 713 | 8,360 |
| 合计 | 7 个不同问题 | **19** | **25,556** | **2,420** | **27,976** |

全部响应为 `stop`，未自动重试。使用本机 DeepSeek 代理及已缓存 CPU 模型；不根据代理 credit 字段换算金额。固定响应回放、探针、旧库检索和单元测试的生成 API 次数均为零。[总核验](../evaluation/results/decomposition_fix_20261019/verification.json)。

在项目根目录，以下命令会新调用 API；使用新的输出目录以保留本轮结果：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -u -c "import runpy, torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); runpy.run_module('evaluation.run_answer_evaluation', run_name='__main__')" \
  --questions evaluation/arxiv_pilot_questions.json \
  --kb-version arxiv-pilot-5-20261019 \
  --output-dir evaluation/results/new_evaluation
```

本轮使用受控线程，默认线程崩溃根因仍未定位。没有换模型、扩充/重建数据、改默认知识库、提交或推送 Git。下一步优先增加独立跨篇题验证策略是否泛化，记录 CPU 开销，并继续收紧题外补充与距离/相似度措辞；当前七题是开发集，不是最终能力证明。
