在《Attention Is All You Need》中，位置前馈网络由两次线性变换组成，中间夹一个 ReLU 激活，即 FFN(x)=max(0, xW1 + b1)W2 + b2 [1]。其输入和输出维度为 dmodel = 512，内层维度为 dff = 2048 [1]。该网络对每个位置分别且相同地应用 [4]。
