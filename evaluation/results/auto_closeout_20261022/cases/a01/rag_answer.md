在 Transformer 中，共享同一个权重矩阵的三部分是：两个嵌入层（embedding layers）以及 softmax 之前的线性变换（pre-softmax linear transformation）[1]。在嵌入层中，这些权重会乘以 √dmodel [1]。
