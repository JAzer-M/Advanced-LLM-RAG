# 五篇 arXiv 论文：离线检索先导实验

仅原问题 Dense + BM25 → RRF Top-60 → BGE Top-10；不调用分解或生成 API。
Gold 短引命中只表示证据定位，完整语义支持另行人工检查。手工小样本不代表总体准确率。

| 题目 | 类型 | Gold 可定位 | 全部 Gold 进入 Top-10 | 秒 |
| --- | --- | --- | --- | --- |
| p1 | single_document | True | False | 3.52 |
| p2 | single_document | True | True | 3.18 |
| p3 | single_document | True | False | 3.34 |
| p4 | single_document | True | True | 2.88 |
| p5 | single_document | True | False | 3.25 |
| p6 | cross_document | True | False | 3.18 |
| p7 | unanswerable | None | None | 3.27 |

## p1：原始 RAG 论文采用什么生成器？其参数规模是多少？

- [1] 2005.11401v4.pdf，PDF p.5，chunk 401
- [2] 2401.15884v3.pdf，PDF p.3，chunk 864
- [3] 2005.11401v4.pdf，PDF p.3，chunk 368
- [4] 2005.11401v4.pdf，PDF p.2，chunk 359
- [5] 2005.11401v4.pdf，PDF p.6，chunk 405
- [6] 2401.15884v3.pdf，PDF p.2，chunk 857
- [7] 2005.11401v4.pdf，PDF p.17，chunk 525
- [8] 2005.11401v4.pdf，PDF p.3，chunk 364
- [9] 2005.11401v4.pdf，PDF p.18，chunk 542
- [10] 2005.11401v4.pdf，PDF p.2，chunk 358

## p2：DPR 使用什么函数计算问题向量和段落向量的相似度？

- [1] 2004.04906v3.pdf，PDF p.3，chunk 28
- [2] 2004.04906v3.pdf，PDF p.8，chunk 103
- [3] 2004.04906v3.pdf，PDF p.3，chunk 29
- [4] 2004.04906v3.pdf，PDF p.3，chunk 41
- [5] 2004.04906v3.pdf，PDF p.12，chunk 151
- [6] 2004.04906v3.pdf，PDF p.8，chunk 99
- [7] 2004.04906v3.pdf，PDF p.5，chunk 61
- [8] 2005.11401v4.pdf，PDF p.5，chunk 401
- [9] 2004.04906v3.pdf，PDF p.2，chunk 14
- [10] 2004.04906v3.pdf，PDF p.8，chunk 100

## p3：ColBERT 的 MaxSim 如何把查询词与文档词的相似度合成为文档得分？

- [1] 2004.12832v2.pdf，PDF p.2，chunk 195
- [2] 2004.12832v2.pdf，PDF p.9，chunk 306
- [3] 2004.12832v2.pdf，PDF p.4，chunk 218
- [4] 2004.12832v2.pdf，PDF p.5，chunk 250
- [5] 2004.12832v2.pdf，PDF p.4，chunk 222
- [6] 2004.12832v2.pdf，PDF p.1，chunk 170
- [7] 2004.12832v2.pdf，PDF p.5，chunk 244
- [8] 2004.12832v2.pdf，PDF p.5，chunk 248
- [9] 2004.12832v2.pdf，PDF p.2，chunk 196
- [10] 2004.12832v2.pdf，PDF p.9，chunk 309

## p4：Self-RAG 的四类 reflection tokens 分别是什么，各负责判断什么？

- [1] 2310.11511v1.pdf，PDF p.1，chunk 556
- [2] 2310.11511v1.pdf，PDF p.4，chunk 587
- [3] 2310.11511v1.pdf，PDF p.3，chunk 580
- [4] 2310.11511v1.pdf，PDF p.10，chunk 667
- [5] 2310.11511v1.pdf，PDF p.1，chunk 551
- [6] 2310.11511v1.pdf，PDF p.4，chunk 594
- [7] 2310.11511v1.pdf，PDF p.6，chunk 614
- [8] 2310.11511v1.pdf，PDF p.2，chunk 567
- [9] 2310.11511v1.pdf，PDF p.6，chunk 613
- [10] 2310.11511v1.pdf，PDF p.1，chunk 550

## p5：CRAG 的 retrieval evaluator 将检索质量划分为哪三种置信判断，用于触发后续行动？

- [1] 2401.15884v3.pdf，PDF p.4，chunk 877
- [2] 2401.15884v3.pdf，PDF p.5，chunk 885
- [3] 2401.15884v3.pdf，PDF p.3，chunk 872
- [4] 2401.15884v3.pdf，PDF p.10，chunk 954
- [5] 2401.15884v3.pdf，PDF p.2，chunk 851
- [6] 2401.15884v3.pdf，PDF p.10，chunk 952
- [7] 2401.15884v3.pdf，PDF p.1，chunk 841
- [8] 2401.15884v3.pdf，PDF p.5，chunk 897
- [9] 2401.15884v3.pdf，PDF p.4，chunk 883
- [10] 2401.15884v3.pdf，PDF p.7，chunk 913

## p6：DPR 和 ColBERT 在问题／文档的向量表示以及相关性打分上有什么主要区别？

- [1] 2004.04906v3.pdf，PDF p.7，chunk 81
- [2] 2004.04906v3.pdf，PDF p.3，chunk 28
- [3] 2004.04906v3.pdf，PDF p.12，chunk 154
- [4] 2004.12832v2.pdf，PDF p.1，chunk 170
- [5] 2004.12832v2.pdf，PDF p.5，chunk 236
- [6] 2004.12832v2.pdf，PDF p.4，chunk 228
- [7] 2004.12832v2.pdf，PDF p.5，chunk 235
- [8] 2004.12832v2.pdf，PDF p.5，chunk 246
- [9] 2004.04906v3.pdf，PDF p.8，chunk 103
- [10] 2004.04906v3.pdf，PDF p.12，chunk 153

## p7：这五种方法在本项目这台 Mac 上，哪一种响应最快？请给出各自的毫秒数。

- [1] 2310.11511v1.pdf，PDF p.30，chunk 834
- [2] 2004.12832v2.pdf，PDF p.10，chunk 324
- [3] 2310.11511v1.pdf，PDF p.30，chunk 835
- [4] 2004.12832v2.pdf，PDF p.2，chunk 185
- [5] 2310.11511v1.pdf，PDF p.28，chunk 821
- [6] 2310.11511v1.pdf，PDF p.7，chunk 634
- [7] 2004.12832v2.pdf，PDF p.7，chunk 280
- [8] 2004.12832v2.pdf，PDF p.1，chunk 172
- [9] 2004.12832v2.pdf，PDF p.8，chunk 290
- [10] 2004.12832v2.pdf，PDF p.8，chunk 287
