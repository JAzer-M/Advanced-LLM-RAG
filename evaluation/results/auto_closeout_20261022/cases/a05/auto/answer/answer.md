对于 DPR 主实验的 retriever，训练使用 in-batch negative 设置，batch size 为 128，并附加每条问题一个 BM25 负例段落[2]。DPR 在联合训练部分的训练 batch size 设为 16，每条问题有效获得 1,600 个段落用于计算 retriever loss[6]。学习率方面，DPR 的问题和段落编码器最多训练 40 个 epoch（大数据集）或 100 个 epoch（小数据集），学习率为 10⁻⁵，使用 Adam、带 warm-up 的线性调度和 0.1 的 dropout[9]。

对于 ColBERT 微调，所有 ColBERT 模型使用学习率 3 × 10⁻⁶、batch size 32[1]。

因此，ColBERT 微调的 batch size 与学习率分别为 32 和 3 × 10⁻⁶[1]；DPR 的报告配置中，主实验 retriever 的 batch size 为 128[2]，而联合训练部分报告的训练 batch size 为 16[6]，学习率为 10⁻⁵[9]。
