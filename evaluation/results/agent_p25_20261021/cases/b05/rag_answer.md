Transformer base 模型平均的是最后 5 个 checkpoint（这些 checkpoint 以 10 分钟间隔写入）；big 模型平均的是最后 20 个 checkpoint [1]。VGG 则是通过平均多个模型的 softmax 类别后验概率来组合输出，从而利用模型间的互补性提升性能 [2]。
