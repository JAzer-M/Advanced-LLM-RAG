# 首批五篇 arXiv 论文：选择依据与先导题目

核对日期：2026-10-19（Asia/Shanghai）。通过官方 arXiv 摘要页、许可链接和 PDF 文本核对。本文只记录来源与题目依据；本机下载、解析、建库、检索及生成结果由实际实验报告记录。

## 选择范围

这五篇由项目主题手工选择，覆盖 RAG、稠密检索、细粒度交互、按需检索与检索纠错，用于检查新论文能否被正确下载、解析、检索和引用。这是先导实验，不是随机抽样或独立统计评测，不据此宣称系统在通用论文问答上达到某个准确率。

论文介绍的方法仅作为知识库内容。下载 Self-RAG、CRAG 或 ColBERT 论文，不表示本项目已经实现、训练或运行这些方法。

## 已核对的论文元数据

日期均为官方提交历史中的 UTC 日期；固定版本是核对当日摘要页显示的最新版本。PDF 页数含参考文献和附录。

| 简称与标题 | 固定 arXiv 版本 | 首次提交 / 固定版本日期 | PDF 页数 | 官方来源 |
| --- | --- | --- | --- | --- |
| RAG — Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 2005.11401v4 | 2020-05-22 / 2021-04-12 | 19 | [摘要及提交历史](https://arxiv.org/abs/2005.11401v4) · [固定版本 PDF](https://arxiv.org/pdf/2005.11401v4) |
| DPR — Dense Passage Retrieval for Open-Domain Question Answering | 2004.04906v3 | 2020-04-10 / 2020-09-30 | 13 | [摘要及提交历史](https://arxiv.org/abs/2004.04906v3) · [固定版本 PDF](https://arxiv.org/pdf/2004.04906v3) |
| ColBERT — ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT | 2004.12832v2 | 2020-04-27 / 2020-06-04 | 10 | [摘要及提交历史](https://arxiv.org/abs/2004.12832v2) · [固定版本 PDF](https://arxiv.org/pdf/2004.12832v2) |
| Self-RAG — Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | 2310.11511v1 | 2023-10-17 / 2023-10-17 | 30 | [摘要及提交历史](https://arxiv.org/abs/2310.11511v1) · [固定版本 PDF](https://arxiv.org/pdf/2310.11511v1) |
| CRAG — Corrective Retrieval Augmented Generation | 2401.15884v3 | 2024-01-29 / 2024-10-07 | 16 | [摘要及提交历史](https://arxiv.org/abs/2401.15884v3) · [固定版本 PDF](https://arxiv.org/pdf/2401.15884v3) |

完整作者名单按官方摘要页顺序记录：

- RAG：Patrick Lewis、Ethan Perez、Aleksandra Piktus、Fabio Petroni、Vladimir Karpukhin、Naman Goyal、Heinrich Küttler、Mike Lewis、Wen-tau Yih、Tim Rocktäschel、Sebastian Riedel、Douwe Kiela。[来源](https://arxiv.org/abs/2005.11401v4)
- DPR：Vladimir Karpukhin、Barlas Oğuz、Sewon Min、Patrick Lewis、Ledell Wu、Sergey Edunov、Danqi Chen、Wen-tau Yih。[来源](https://arxiv.org/abs/2004.04906v3)
- ColBERT：Omar Khattab、Matei Zaharia。[来源](https://arxiv.org/abs/2004.12832v2)
- Self-RAG：Akari Asai、Zeqiu Wu、Yizhong Wang、Avirup Sil、Hannaneh Hajishirzi。[来源](https://arxiv.org/abs/2310.11511v1)
- CRAG：Shi-Qi Yan、Jia-Chen Gu、Yun Zhu、Zhen-Hua Ling。[来源](https://arxiv.org/abs/2401.15884v3)

许可链接的实际目标：

- RAG、DPR、ColBERT、CRAG 的摘要页均指向 [arXiv 非独占分发许可](https://arxiv.org/licenses/nonexclusive-distrib/1.0/license.html)。这是提交者对 arXiv 的授权，不能直接当作本项目再发布全文的许可。
- Self-RAG 指向 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。
- 本次用于本机研究。公开项目应提供论文元数据、官方链接与下载入口；全文再发布按每篇实际许可处理。[arXiv 内容使用说明](https://info.arxiv.org/help/api/tou.html)

## 先导题目与原文依据

以下页码是从 PDF 文件第一页开始计数的一基页码，不是零基解析索引。短引仅保留用于定位的少量文字；中文答案为归纳。落入本地分块后的实际 chunk ID 和原文一致性，需要下载后再核对。

### p1：RAG 的生成器

- 中文问题：原始 RAG 论文采用什么生成器？其参数规模是多少？
- 预期答案：BART-large，约 400M（4 亿）参数。
- 依据：PDF 第 3 页，§2.3 Generator: BART。
- 原文短引：“We use BART-large”；“with 400M parameters”。
- [固定版本原文，第 3 页](https://arxiv.org/pdf/2005.11401v4#page=3)

### p2：DPR 的相似度

- 中文问题：DPR 使用什么函数计算问题向量和段落向量的相似度？
- 预期答案：计算两个向量的点积，即问题编码与段落编码的内积。
- 依据：PDF 第 3 页，§3.1 Overview，公式（1）。
- 原文短引：“using the dot product of their vectors”。
- [固定版本原文，第 3 页](https://arxiv.org/pdf/2004.04906v3#page=3)

### p3：ColBERT 的 MaxSim

- 中文问题：ColBERT 的 MaxSim 如何把查询词与文档词的相似度合成为文档得分？
- 预期答案：对每个查询 token 的向量，取它与文档 token 向量之间的最大相似度，再把所有查询 token 对应的最大值相加。论文主要说明余弦相似度，也评估了平方 L2 距离。
- 依据：PDF 第 4 页，§3.1 Architecture。
- 原文短引：“maximum cosine similarity”；“combine the outputs via summation”。
- [固定版本原文，第 4 页](https://arxiv.org/pdf/2004.12832v2#page=4)

### p4：Self-RAG 的反思 token

- 中文问题：Self-RAG 的四类 reflection tokens 分别是什么，各负责判断什么？
- 预期答案：Retrieve 判断是否需要检索；ISREL 判断段落是否与问题相关；ISSUP 判断生成内容得到段落支持的程度；ISUSE 判断回答对输入的整体有用程度。
- 依据：PDF 第 4 页，Table 1。
- 原文短引：“Four types of reflection tokens used in SELF-RAG”。
- [固定版本原文，第 4 页](https://arxiv.org/pdf/2310.11511v1#page=4)

### p5：CRAG 的三类判断

- 中文问题：CRAG 的 retrieval evaluator 将检索质量划分为哪三种置信判断，用于触发后续行动？
- 预期答案：Correct、Incorrect、Ambiguous，分别对应可用、不可靠和不确定的检索结果。
- 依据：PDF 第 3 页，§4.1 Overview；第 5 页 Algorithm 1 也明确列出三个值。
- 原文短引：“{Correct, Incorrect, Ambiguous}”。
- [固定版本原文，第 3 页](https://arxiv.org/pdf/2401.15884v3#page=3)

### p6：跨论文比较

- 中文问题：DPR 和 ColBERT 在问题／文档的向量表示以及相关性打分上有什么主要区别？
- 预期答案：DPR 把问题和段落各编码为一个向量，使用点积打分；ColBERT 保留多个上下文化 token 向量，经 MaxSim 为每个查询 token 取最佳文档匹配，再求和。两篇论文均允许预先计算文档侧表示，但打分粒度不同。
- 依据：[DPR 第 2–3 页 §3.1](https://arxiv.org/pdf/2004.04906v3#page=3)、[ColBERT 第 4 页 §3.1–3.2](https://arxiv.org/pdf/2004.12832v2#page=4)。复用 p2、p3 的短引，不额外摘录全文。
- 验收时应同时找到两篇的支撑段落，不能只因答案正确就视为跨论文检索成功。

### p7：库外信息拒答

- 中文问题：这五种方法在本项目这台 Mac 上，哪一种响应最快？请给出各自的毫秒数。
- 预期行为：说明这五篇论文没有提供本项目这台 Mac 的实测数据，不能据此排名或编造延迟；若要比较，需要单独实现并在相同条件下测量。
- 依据边界：这是有意构造的本地测量缺失题，无正向 Gold 段落。论文中的其他硬件、数据集或实验数字不能当成本机测量。

## 下载与元数据接口约束

官方 API 用户手册支持 `id_list`，指定版本时在 ID 后附 `vN`；元数据的 `published` 表示首版日期，`updated` 表示被返回版本日期；应缓存重复查询。[API 用户手册](https://info.arxiv.org/help/api/user-manual.html)

官方使用条款对 legacy APIs（包括 arXiv API、OAI-PMH、RSS）要求请求间隔不少于 3 秒、同时只有一个连接，并按使用方所有机器整体计算。五篇可用一个 `id_list` 请求获取元数据，无需逐篇并行请求。[API 使用条款](https://info.arxiv.org/help/api/tou.html)

为减轻下载负载，本次 PDF 下载也建议串行、缓存已完成文件、在请求间留至少 3 秒，并对限流及服务错误进行有限重试。这是本次实现选择；不把 legacy API 的配额表述为所有 PDF 接口的统一正式配额。arXiv 明确反对无选择地递归下载整个站点。[Robots Beware](https://info.arxiv.org/help/robots.html)

## 已核对与待实测的边界

- 已核对：五篇身份、作者顺序、版本、日期、官方 PDF 入口、许可目标及上述题目对应的官方 PDF 页码／内容。
- 待主实验实测：本地 PDF 文件哈希与页数、双栏解析顺序、分块中文本完整性、Gold 短引与实际 chunk 匹配、Top-10 覆盖、跨论文证据齐备程度、API 回答与引用质量、拒答表现。
- 本文没有调用生成 API，也没有下载论文到项目数据目录、变更代码或切换活动知识库。
