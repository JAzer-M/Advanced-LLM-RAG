# 五篇 arXiv 论文：离线检索先导实验

仅原问题 Dense + BM25 → RRF Top-60 → BGE Top-10；不调用分解或生成 API。
Gold 短引命中只表示证据定位，完整语义支持另行人工检查。手工小样本不代表总体准确率。

| 题目 | 类型 | Gold 可定位 | 全部 Gold 进入 Top-10 | 秒 |
| --- | --- | --- | --- | --- |
| q1 | single_document | True | False | 4.27 |
| q2 | single_document | True | True | 2.34 |
| q3 | single_document | True | True | 2.07 |
| q4 | single_document | True | True | 2.51 |
| q5 | multi_document | True | False | 3.98 |
| q6 | unanswerable | None | None | 2.96 |

## q1：Why does VGG use small 3x3 convolutional filters?

- [1] VGG.pdf，PDF p.1，chunk 224
- [2] VGG.pdf，PDF p.1，chunk 219
- [3] VGG.pdf，PDF p.4，chunk 250
- [4] VGG.pdf，PDF p.2，chunk 232
- [5] VGG.pdf，PDF p.2，chunk 241
- [6] VGG.pdf，PDF p.3，chunk 246
- [7] VGG.pdf，PDF p.3，chunk 248
- [8] VGG.pdf，PDF p.2，chunk 233
- [9] VGG.pdf，PDF p.6，chunk 281
- [10] VGG.pdf，PDF p.3，chunk 245

## q2：Why does the Transformer use positional encoding?

- [1] Attention is all you need.pdf，PDF p.5，chunk 45
- [2] Attention is all you need.pdf，PDF p.5，chunk 38
- [3] Attention is all you need.pdf，PDF p.9，chunk 81
- [4] Attention is all you need.pdf，PDF p.6，chunk 48
- [5] Attention is all you need.pdf，PDF p.2，chunk 20
- [6] Attention is all you need.pdf，PDF p.9，chunk 80
- [7] Attention is all you need.pdf，PDF p.2，chunk 17
- [8] Attention is all you need.pdf，PDF p.7，chunk 67
- [9] Attention is all you need.pdf，PDF p.2，chunk 12
- [10] Attention is all you need.pdf，PDF p.6，chunk 47

## q3：Why does the Transformer use scaled dot-product attention?

- [1] Attention is all you need.pdf，PDF p.1，chunk 6
- [2] Attention is all you need.pdf，PDF p.4，chunk 32
- [3] Attention is all you need.pdf，PDF p.5，chunk 40
- [4] Attention is all you need.pdf，PDF p.4，chunk 31
- [5] Attention is all you need.pdf，PDF p.2，chunk 12
- [6] Attention is all you need.pdf，PDF p.4，chunk 29
- [7] Attention is all you need.pdf，PDF p.2，chunk 15
- [8] Attention is all you need.pdf，PDF p.5，chunk 38
- [9] Attention is all you need.pdf，PDF p.9，chunk 82
- [10] Attention is all you need.pdf，PDF p.2，chunk 17

## q4：How does the DCNN paper use data augmentation to reduce overfitting?

- [1] DCNN.pdf，PDF p.4，chunk 162
- [2] DCNN.pdf，PDF p.1，chunk 103
- [3] DCNN.pdf，PDF p.4，chunk 163
- [4] DCNN.pdf，PDF p.5，chunk 167
- [5] DCNN.pdf，PDF p.4，chunk 153
- [6] DCNN.pdf，PDF p.4，chunk 164
- [7] DCNN.pdf，PDF p.2，chunk 121
- [8] DCNN.pdf，PDF p.5，chunk 174
- [9] DCNN.pdf，PDF p.1，chunk 114
- [10] DCNN.pdf，PDF p.7，chunk 197

## q5：How do VGG and DCNN differ in their use of convolutional filter sizes?

- [1] VGG.pdf，PDF p.2，chunk 238
- [2] VGG.pdf，PDF p.4，chunk 250
- [3] DCNN.pdf，PDF p.4，chunk 158
- [4] VGG.pdf，PDF p.2，chunk 233
- [5] VGG.pdf，PDF p.1，chunk 224
- [6] VGG.pdf，PDF p.3，chunk 248
- [7] DCNN.pdf，PDF p.4，chunk 157
- [8] VGG.pdf，PDF p.2，chunk 232
- [9] VGG.pdf，PDF p.2，chunk 234
- [10] DCNN.pdf，PDF p.2，chunk 117

## q6：What was NVIDIA's stock price on October 10, 2026?

- [1] VGG.pdf，PDF p.8，chunk 310
- [2] DCNN.pdf，PDF p.5，chunk 179
- [3] Attention is all you need.pdf，PDF p.7，chunk 64
- [4] VGG.pdf，PDF p.8，chunk 307
- [5] VGG.pdf，PDF p.5，chunk 274
- [6] DCNN.pdf，PDF p.7，chunk 200
- [7] DCNN.pdf，PDF p.5，chunk 178
- [8] DCNN.pdf，PDF p.4，chunk 153
- [9] VGG.pdf，PDF p.13，chunk 361
- [10] DCNN.pdf，PDF p.4，chunk 159
