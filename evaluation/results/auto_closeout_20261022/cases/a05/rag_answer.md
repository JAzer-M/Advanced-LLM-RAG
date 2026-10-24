根据提供的证据：

- **主 DPR retriever**：训练 batch size 为 128，并为每个问题额外加入一个 BM25 负样本段落 [2]；学习率为 10⁻⁵，使用 Adam，并配有 linear scheduling with warm-up 和 dropout rate 0.1 [9]。
- **ColBERT 微调**：batch size 为 32，学习率为 3 × 10⁻⁶ [1]。
