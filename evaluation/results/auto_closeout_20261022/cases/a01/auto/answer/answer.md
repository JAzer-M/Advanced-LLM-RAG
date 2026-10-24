在 Attention Is All You Need 中，共享同一权重矩阵的三个对象是：两个 embedding 层以及 pre-softmax 线性变换（[1]）。在 embedding 层中，这些权重会乘以 √dmodel（[1]）。
