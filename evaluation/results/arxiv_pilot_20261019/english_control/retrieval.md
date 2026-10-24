# 五篇 arXiv 论文：离线检索先导实验

仅原问题 Dense + BM25 → RRF Top-60 → BGE Top-10；不调用分解或生成 API。
Gold 短引命中只表示证据定位，完整语义支持另行人工检查。手工小样本不代表总体准确率。

| 题目 | 类型 | Gold 可定位 | 全部 Gold 进入 Top-10 | 秒 |
| --- | --- | --- | --- | --- |
| p1 | single_document | True | True | 2.49 |
| p2 | single_document | True | True | 3.01 |
| p3 | single_document | True | False | 2.94 |
| p4 | single_document | True | True | 2.46 |
| p5 | single_document | True | True | 2.57 |
| p6 | cross_document | True | False | 2.74 |

## p1：Which generator does the original RAG paper use, and how many parameters does it have?

- [1] 2310.11511v1.pdf，PDF p.1，chunk 551
- [2] 2005.11401v4.pdf，PDF p.18，chunk 542
- [3] 2005.11401v4.pdf，PDF p.3，chunk 368
- [4] 2401.15884v3.pdf，PDF p.3，chunk 864
- [5] 2310.11511v1.pdf，PDF p.2，chunk 569
- [6] 2005.11401v4.pdf，PDF p.2，chunk 359
- [7] 2005.11401v4.pdf，PDF p.3，chunk 361
- [8] 2005.11401v4.pdf，PDF p.2，chunk 353
- [9] 2005.11401v4.pdf，PDF p.1，chunk 341
- [10] 2005.11401v4.pdf，PDF p.3，chunk 372

## p2：What function does DPR use to compute similarity between question and passage vectors?

- [1] 2004.04906v3.pdf，PDF p.3，chunk 28
- [2] 2004.04906v3.pdf，PDF p.3，chunk 29
- [3] 2004.04906v3.pdf，PDF p.2，chunk 14
- [4] 2004.04906v3.pdf，PDF p.8，chunk 99
- [5] 2004.04906v3.pdf，PDF p.2，chunk 25
- [6] 2004.04906v3.pdf，PDF p.12，chunk 151
- [7] 2004.04906v3.pdf，PDF p.8，chunk 103
- [8] 2004.04906v3.pdf，PDF p.6，chunk 77
- [9] 2004.04906v3.pdf，PDF p.3，chunk 41
- [10] 2004.04906v3.pdf，PDF p.12，chunk 158

## p3：How does ColBERT MaxSim aggregate query-document token similarities into a document relevance score?

- [1] 2004.12832v2.pdf，PDF p.4，chunk 218
- [2] 2004.12832v2.pdf，PDF p.4，chunk 222
- [3] 2004.12832v2.pdf，PDF p.2，chunk 195
- [4] 2004.12832v2.pdf，PDF p.4，chunk 220
- [5] 2004.12832v2.pdf，PDF p.3，chunk 207
- [6] 2004.12832v2.pdf，PDF p.9，chunk 306
- [7] 2004.12832v2.pdf，PDF p.9，chunk 305
- [8] 2004.12832v2.pdf，PDF p.7，chunk 274
- [9] 2004.12832v2.pdf，PDF p.1，chunk 169
- [10] 2004.12832v2.pdf，PDF p.1，chunk 179

## p4：What are the four types of reflection tokens in Self-RAG, and what does each type evaluate?

- [1] 2310.11511v1.pdf，PDF p.4，chunk 587
- [2] 2401.15884v3.pdf，PDF p.7，chunk 918
- [3] 2310.11511v1.pdf，PDF p.4，chunk 594
- [4] 2310.11511v1.pdf，PDF p.3，chunk 580
- [5] 2310.11511v1.pdf，PDF p.4，chunk 592
- [6] 2310.11511v1.pdf，PDF p.1，chunk 556
- [7] 2310.11511v1.pdf，PDF p.2，chunk 565
- [8] 2310.11511v1.pdf，PDF p.1，chunk 550
- [9] 2310.11511v1.pdf，PDF p.1，chunk 555
- [10] 2310.11511v1.pdf，PDF p.10，chunk 667

## p5：What are the three confidence judgments from the CRAG retrieval evaluator that trigger subsequent actions?

- [1] 2401.15884v3.pdf，PDF p.4，chunk 877
- [2] 2401.15884v3.pdf，PDF p.3，chunk 873
- [3] 2401.15884v3.pdf，PDF p.5，chunk 897
- [4] 2401.15884v3.pdf，PDF p.2，chunk 851
- [5] 2401.15884v3.pdf，PDF p.10，chunk 952
- [6] 2401.15884v3.pdf，PDF p.5，chunk 890
- [7] 2401.15884v3.pdf，PDF p.1，chunk 841
- [8] 2401.15884v3.pdf，PDF p.5，chunk 896
- [9] 2401.15884v3.pdf，PDF p.15，chunk 1009
- [10] 2401.15884v3.pdf，PDF p.2，chunk 852

## p6：How do DPR and ColBERT differ in question and document representations and relevance scoring?

- [1] 2004.12832v2.pdf，PDF p.1，chunk 170
- [2] 2004.12832v2.pdf，PDF p.5，chunk 236
- [3] 2004.12832v2.pdf，PDF p.7，chunk 277
- [4] 2004.12832v2.pdf，PDF p.7，chunk 280
- [5] 2004.04906v3.pdf，PDF p.7，chunk 81
- [6] 2004.12832v2.pdf，PDF p.9，chunk 311
- [7] 2004.04906v3.pdf，PDF p.12，chunk 154
- [8] 2005.11401v4.pdf，PDF p.3，chunk 369
- [9] 2004.12832v2.pdf，PDF p.7，chunk 274
- [10] 2005.11401v4.pdf，PDF p.2，chunk 352
