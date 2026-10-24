# 新题检索、模型知识对照与有限优化日志

2026-10-19。执行用户批准的三项：冻结当前版本并新增英文评测题；比较闭卷、正确证据、无关证据；只做有限优化尝试，收益不稳就保留。沿用 Karpathy 的精准改动与 Matt Pocock diagnosing-bugs 的固定输入、失败回放和有限假设验证流程。

**结论：保留当前检索排序，不采用两种排序候选。新十道可答题 Recall@10=0.4833、MAP@10=0.2144，跨篇召回仅 0.2222，前轮六题的 1.0000 不代表泛化。** 本轮只修复了一个明确的元数据传递缺口：把已有真实论文标题带入生成上下文。标题复核改善了一题，另一题仍过度拒答；没有继续花调用反复调提示。

## 1. 冻结与新题

- 已保存运行前代码快照、47 个基线文件 SHA-256，以及[实验协议](../evaluation/results/independent_validation_20261019/protocol.json)。保留旧成绩、索引、Gold、API 私有配置及当前默认库指针。
- 新题集 [arxiv_next_questions_en.json](../evaluation/arxiv_next_questions_en.json)：4 道单篇、6 道跨篇、2 道项目测量缺失题。问题、原文 source/page/quote、人工核对点在模型调用前确定；计分点不传给模型。
- 新题来自同五篇论文，部分依据相互重叠，也与已有知识点有关，是新编验证集，不是外部盲测或统计独立样本。n08 对两个方法的“不必要／错误”条件归属存在可读歧义，保留原题和分数并在人工记录中标注，没有事后删除低分题。
- 明确使用五篇版本 `arxiv-pilot-5-20261019`，1,019 块。模型不变、每路候选 60、最终 10。每道可答题只新生成一次分解；改写关闭，匹配 `main.py` 的当前设置。实际调用原 `evaluation.run_evaluation.main()`，使用缓存后禁止任何生成 API。
- n11、n12 没有 Gold，从检索分数中跳过，**没有计为答对**。生成对照只抽测了其中 n11，n12 尚未生成答案。

## 2. 新题检索结果

数值是十道有 Gold 问题的宏平均；同题各方法对照，四项公式与 Gold 保持原样。

| 方法 | Precision@10 | Recall@10 | MAP@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: |
| Dense | 0.0300 | 0.2000 | 0.0600 | 0.0667 |
| BM25 | 0.0800 | 0.4500 | 0.1946 | 0.2397 |
| Hybrid | 0.0500 | 0.2667 | 0.1525 | 0.1625 |
| Hybrid + Reranker | 0.0900 | 0.5500 | 0.2299 | 0.3079 |
| Decomposition + Global Reranker (legacy) | 0.1000 | 0.6000 | 0.2370 | 0.3283 |
| Decomposition + Hybrid + Reranker | 0.0700 | 0.4833 | 0.2144 | 0.3061 |

缓存里的 rewritten_query 等于原问题，明确标为 disabled_to_match_main。因此输出中的 Rewritten/Multi-Query 行只是禁用改写的原问题路径，不宣称做了新的改写实验。

当前主流程按类型：单篇 Recall **0.8750**，跨篇 **0.2222**；全部指定 Gold 齐备为 **4/10** 道，跨篇 **1/6** 道。前轮六题是开发集，新题难度、所需片段数量和内容不同，不能把两个集合相减当作同题性能下降；新结果确实暴露出跨篇能力不足。

| 题目 | 类型 | 指定 Gold 命中 | AP@10 | RR@10 |
| --- | --- | ---: | ---: | ---: |
| n01 | 单篇 | 1/1 | 0.1111 | 0.1111 |
| n02 | 单篇 | 1/1 | 1.0000 | 1.0000 |
| n03 | 单篇 | 1/2 | 0.1250 | 0.2500 |
| n04 | 单篇 | 1/1 | 0.2000 | 0.2000 |
| n05 | 跨篇 | 2/2 | 0.3750 | 0.5000 |
| n06 | 跨篇 | 1/3 | 0.3333 | 1.0000 |
| n07 | 跨篇 | 0/2 | 0.0000 | 0.0000 |
| n08 | 跨篇 | 0/3 | 0.0000 | 0.0000 |
| n09 | 跨篇 | 0/2 | 0.0000 | 0.0000 |
| n10 | 跨篇 | 0/2 | 0.0000 | 0.0000 |

### 失败在哪一步

- n03：查询 mask 补全段落 224 已入选，但“文档不追加 mask”的 231 排在合并候选全局第 40，最终缺失。
- n06：ColBERT loss 段落 236 在第一位，DPR loss 36 曾在全局第五，却被子题优先选择替换出去。DPR 训练负例有段落 57 作为替代支持，但不替代损失定义。
- n07：ColBERT 的指定段落 237 在全局第九，但最终被替换；仍有 236/240/243 支持其离线文档表示。RAG 的指定离线索引说明 383 没进合并池，RAG 这一半确实缺证据。
- n08：有 Self-RAG token 定义、CRAG confidence 的替代段落，但对“不检索时的生成”及 Incorrect 丢弃后 web fallback 没有完整支持。指定段落 590 本在全局第九，也被替换。
- n09：DPR 的具体 Wikipedia 日期缺失；CRAG 网页补充有替代段落 906，但精确触发条件不足。
- n10：缺少所问 CLS 提取及 Q/D 输入标记细节；只有向量表示的背景段落。

因此有两类真实问题：部分证据没有召回，部分已召回却在最终选择中被挤掉。指定 Gold 零命中也不等于没有任何可用信息；替代支持与剩余缺口见[实际证据人工核对](../evaluation/results/independent_validation_20261019/retrieved_evidence_review.json)，**没有回写 Gold 提高分数**。

原问题混合重排 Recall=0.5500、分解后仅全局重排为 0.6000，均高于当前保留策略在新题的 0.4833；但它们在旧六题的覆盖也较低，尚无一个简单固定规则稳定优于现有基线。

## 3. 两种有限排序尝试：均不采用

执行前限定两个候选，只重排已经选定的十条，绝不改变入选集合或借 Gold 选段落：

- A：全局 CE 排名、原 RRF 排名、各子题局部排名作 RRF 投票，固定 k=60。
- B：原问题检索首条及子题首条排前，其余保持当前全局顺序。

事先的采用门槛：新题 MAP 至少 +0.03、MRR 至少 +0.02；新跨篇均值不下降；每套旧题 MAP/MRR 不下降超过 0.01。对照共 26 道新旧可答题，不调用 API、不重跑模型。

| 方案 | 新题 MAP | 新题 MRR | 旧六题 MAP | 旧五验证题 MAP | 旧三篇题 MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| 保留基线 | 0.2144 | 0.3061 | 0.3998 | 0.8000 | 0.7667 |
| A：多排名 RRF 投票 | 0.2111 | 0.2869 | 0.4185 | 0.6619 | 0.6500 |
| B：保护证据优先排前 | 0.1761 | 0.2061 | 0.5532 | 0.8000 | 0.7333 |

两种方法只在部分旧题上变好，新题反而下降，均未通过门槛。**保留原排序，不部署候选。** 原 p1 关键证据仍在第十，真实函数回放的[失败断言](../evaluation/results/independent_validation_20261019/ranking_red.log)保留，不声称已解决排序问题。[全部候选、采用条件及逐题 ID](../evaluation/results/independent_validation_20261019/rank_probes.json)。

## 4. DeepSeek 自身知识与证据约束

选 n03（ColBERT augmentation）、n05（RAG/DPR 编码器）、n08（Self-RAG/CRAG 行为）、n11（本项目未给出的延迟），每题三条件，共十二个原始回答：

1. 闭卷：允许模型用自身知识，未知项目数据应承认不知道。
2. 正确证据：给实际预标注 Gold 段落，要求只按证据作答并引用。这是 **oracle 正向控制**，不是实际检索答案；n11 没有 Gold，输入为空。
3. 无关证据：同一 evidence-only 提示，换成不支持该题的其他论文段落。

闭卷与 evidence-only 的知识使用指令有意不同；不能宣称这是只改变上下文、其他条件完全相同的因果实验。模型、问题、生成选项不变；正确/无关证据两组的规则一致。没有用 LLM 自评，没有引用修复重试。人工评价是本轮作者核对，非盲审，不把四题汇总成总体准确率。

| 题目 | 闭卷 | 原始正确证据 | 无关证据 |
| --- | --- | --- | --- |
| n03 | mask 补全与文档不对称两点有，但把 Q 标记与 query augmentation 混为一谈，存在具体细节错误 | 完整，引用分别支持 mask 补全与文档不追加 mask | 正确拒答 |
| n05 | BERT-base 双编码器与 CLS 等主要内容基本正确，未说明 uncased 细节 | 部分回答，但错误否认编号论文是 DPR | 正确拒答 |
| n08 | 主要机制有；额外修订/拒绝生成等说法未在本对照原文核验 | 部分回答，遗漏 web fallback，且未确认 CRAG 身份 | 正确拒答，带了可省略的无关概述 |
| n11 | 承认不知道项目测量，不编造毫秒数 | 空证据时正确拒答 | 正确拒答 |

**观察支持模型本身确实知道这些论文的相当一部分内容，也显示闭卷可能混淆技术细节。** 无关证据四题均没有编造所问答案，说明本次 evidence-only 约束有作用；不代表任何输入下都可靠。没有证据证明“此前所有好答案都来自模型自身”。

### 发现并修复：生成上下文丢失论文标题

初次正向实验的来源头只有 arXiv 数字文件名，两题响应直接以“不能识别这篇是哪篇论文”为由拒绝连接事实。检查发现，重排器已经能看到 title，`main.build_context()` 却没有向生成器展示这个现有元数据。

新增一条可选 Title 来源头；标题已包含在文件名中时不重复添加。正文、题目、Gold、引用编号及选证据集合都不变，标题只表明文档身份，不自动证明段落中任何第三方模型的归属。真实缺失标题测试先失败，修复后通过。

为此在原 22 次调用计划之外，**追加两次明确限定的元数据诊断复核**，先记录协议补充；只在 n05/n08 原正向提示中插入真实标题，其他字节、模型和原文保持一致，原十二份输出保留：

- n08：补标题后，Self-RAG no-retrieval、CRAG confidence、Incorrect 丢弃与 web fallback 全部有对应引用。
- n05：现在能识别 DPR 和 CLS，但仍以“证据不足”开头，并给出前后矛盾的范围说明；**未记严格通过**，停止继续调整提示或付费采样。

这是两题定向复核，不能冒充新跑了一整套三条件矩阵，也不是生产完整提示下的端到端生成验收。[原十二份回答](../evaluation/results/independent_validation_20261019/grounding/n03_closed_book.md)、[标题复核 n05](../evaluation/results/independent_validation_20261019/grounding_metadata/n05_gold_evidence.md)、[n08](../evaluation/results/independent_validation_20261019/grounding_metadata/n08_gold_evidence.md)、[人工审阅](../evaluation/results/independent_validation_20261019/grounding_review.json)。

## 5. 验证、用量与停止决定

- **50 项本地测试全部通过。** 新增三个上下文元数据/兼容性测试；原测试、排序实现均保留。
- 100 组新题逐方法分数独立从 ID 重算一致，26 道排序对照的分数及集合一致性通过，两个候选均按预设条件拒绝采用。
- 47 个原登记文件中，46 个保持原哈希。生产代码仅 `main.build_context` 改动；其余 main AST 节点、检索/选择函数、指标、旧题/Gold、索引、私有 API 配置及默认指针不变。
- 378 个旧库片段的生成上下文逐字与原函数相同；1,019 个新库片段只增加已有真实标题，原文不变。[上下文等价检查](../evaluation/results/independent_validation_20261019/context_equivalence.json)。没有再重跑昂贵旧题模型评测。
- 新题检索是在补标题前冻结代码上实测；补标题不改变检索路径，已用 AST 与输入哈希验证，不能把标题改动写成检索涨分。

| 调用阶段 | 次数 | 输入 token | 输出 token | 合计 |
| --- | ---: | ---: | ---: | ---: |
| 分解 | 10 | 6,440 | 597 | 7,037 |
| 原始三条件生成 | 12 | 2,801 | 1,224 | 4,025 |
| 标题定向复核 | 2 | 829 | 295 | 1,124 |
| 总计 | **24** | **10,070** | **2,116** | **12,186** |

全部正常 stop，无自动重试，不估算金额。候选排序和固定查询的检索评估均没有生成 API 调用；来源标题两个复核单列，避免隐瞒额外成本。[总核验](../evaluation/results/independent_validation_20261019/verification.json)。

**最终保留当前排序与 60→10 参数，仅保留真实标题传递修复。** 不换模型、不重建索引、不继续参数搜索。原排序在独立跨篇题上仍弱，n05 受控生成仍过度拒答，本轮不声称固定 RAG 的泛化或生成忠实度全面验收通过。

后续可用 n07～n10 的真实失败建立证据缺口识别与有限补检索小原型，分别判断“尚未召回”“最终选证据丢失”“已给足证据仍过度拒答”，再决定是否扩展 Agent。此轮没有实现 Agent、联网或 UI，没有提交/推送 Git。

## 复现与产物

查看分数无需再调用 API。下列命令在项目根目录使用现有缓存运行检索，输出应使用新目录；受控单线程配置继续保留。

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -u -c "import runpy, torch; torch.set_num_threads(1); torch.set_num_interop_threads(1); runpy.run_module('evaluation.run_evaluation', run_name='__main__')" \
  --questions evaluation/arxiv_next_questions_en.json \
  --kb-version arxiv-pilot-5-20261019 --candidate-k 60 --top-k 10 \
  --auxiliary-cache evaluation/results/independent_validation_20261019/auxiliary.json \
  --output-dir evaluation/results/new_independent_run
```

- [新题原始检索 JSON](../evaluation/results/independent_validation_20261019/retrieval/results.json)、[原脚本 stdout](../evaluation/results/independent_validation_20261019/retrieval.log)
- [分解响应、提示与用量](../evaluation/results/independent_validation_20261019/decomposition_calls.json)
- [实验运行入口](../evaluation/results/independent_validation_20261019/run_experiment.py)、[有限排序尝试](../evaluation/results/independent_validation_20261019/rank_experiments.py)、[核验脚本](../evaluation/results/independent_validation_20261019/verify_results.py)
- [原测试输出](../evaluation/results/independent_validation_20261019/tests_final.log)、[元数据修复前失败测试](../evaluation/results/independent_validation_20261019/context_metadata_red.log)
