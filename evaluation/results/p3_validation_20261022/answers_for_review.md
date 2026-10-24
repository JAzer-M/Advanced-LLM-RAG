# 冻结新题：真实输出与引用，语义待人工核对


## n01 / agent_off / completed

在《Attention Is All You Need》中，位置前馈网络由两次线性变换组成，中间夹一个 ReLU 激活，即 FFN(x)=max(0, xW1 + b1)W2 + b2 [1]。其输入和输出维度为 dmodel = 512，内层维度为 dff = 2048 [1]。该网络对每个位置分别且相同地应用 [4]。

引用[1] Attention is all you need.pdf p.5 id=42

This consists of two linear transformations with a ReLU activation in between. FFN(x) = max(0, xW1 + b1)W2 + b2 (2) While the linear transformations are the same across different positions, they use different parameters from layer to layer. Another way of describing this is as two convolutions with kernel size 1. The dimensionality of input and output is dmodel = 512, and the inner-layer has dimensionality dff = 2048.

引用[4] Attention is all you need.pdf p.5 id=41

3.3 Position-wise Feed-Forward Networks In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is applied to each position separately and identically.

## n01 / agent_on / completed

位置前馈网络由两个线性变换组成，中间夹以 ReLU 激活，即 FFN(x) = max(0, xW1 + b1)W2 + b2 [1]；其内层维度为 dff = 2048 [1]。

引用[1] Attention is all you need.pdf p.5 id=42

This consists of two linear transformations with a ReLU activation in between. FFN(x) = max(0, xW1 + b1)W2 + b2 (2) While the linear transformations are the same across different positions, they use different parameters from layer to layer. Another way of describing this is as two convolutions with kernel size 1. The dimensionality of input and output is dmodel = 512, and the inner-layer has dimensionality dff = 2048.

## n02 / agent_on / completed

根据VGG，卷积步长固定为1像素[1]；对于3×3卷积层，输入的空间补边使卷积后空间分辨率得以保持，即补边为1像素[1]。

引用[1] VGG.pdf p.2 id=233

In one of the conﬁgurations we also utilise 1 × 1 convolution ﬁlters, which can be seen as a linear transformation of the input channels (followed by non-linearity). The convolution stride is ﬁxed to 1 pixel; the spatial padding of conv. layer input is such that the spatial resolution is preserved after convolution, i.e. the padding is 1 pixel for 3 × 3 conv. Spatial pooling is carried out by ﬁve max-pooling layers, which follow some of the conv. layers (not all the conv.

## n02 / agent_off / completed

VGG 的 3×3 卷积层卷积步长固定为 1 像素，输入的空间填充为 1 像素，以在卷积后保持空间分辨率[1]。

引用[1] VGG.pdf p.2 id=233

In one of the conﬁgurations we also utilise 1 × 1 convolution ﬁlters, which can be seen as a linear transformation of the input channels (followed by non-linearity). The convolution stride is ﬁxed to 1 pixel; the spatial padding of conv. layer input is such that the spatial resolution is preserved after convolution, i.e. the padding is 1 pixel for 3 × 3 conv. Spatial pooling is carried out by ﬁve max-pooling layers, which follow some of the conv. layers (not all the conv.

## n03 / agent_off / completed

当前证据不足，无法可靠回答以下需求：
- RoFormer：According to the RoFormer paper, how does its positional encoding incorporate absolute position and relative-position dependence in self-attention?；缺少 RoFormer 原始论文，无法确定其位置编码在自注意力中融合绝对位置与相对位置依赖的具体机制。

## n03 / agent_on / completed

根据RoFormer论文，其位置编码方法RoPE用旋转矩阵编码绝对位置，同时在自注意力公式中引入显式的相对位置依赖[12][14]。理论上，相对位置通过自注意力中的向量乘积自然表达，绝对位置信息则通过旋转矩阵编码[13]。与以往工作中加性的位置嵌入不同，该方法是乘性的，并通过旋转矩阵乘积自然地纳入相对位置信息，而非修改加性位置编码展开式中的项[15][16]。

来源：
[12] 2104.09864v5.pdf，p.2；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[13] 2104.09864v5.pdf，p.12；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[14] 2104.09864v5.pdf，p.1；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[15] 2104.09864v5.pdf，p.5；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[16] 2104.09864v5.pdf，p.5；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)

引用[12] 2104.09864v5.pdf p.2 id=1402

 encoding from the
perspective of Neural ODE Chen et al. [2018a], and the authors of Wang et al. [2020] have proposed to model the
position information in complex space. Despite the effectiveness of these approaches, they commonly add the position
information to the context representation and thus render them unsuitable for the linear self-attention architecture.
In this paper, we introduce a novel method, namely Rotary Position Embedding(RoPE), to leverage the positional
information into the learning process of PLMS. Specifically, RoPE encodes the absolute position with a rotation matrix
and meanwhile incorporates the explicit relative position dependency in self-attention formulation. Note that the
proposed RoPE is prioritized over the existing methods through valuable properties, including the sequence length
flexibility, decaying inter-token dependency with increasing relative distances, and the capability of equipping the
linear self-attention with relative position encoding. Experimental results on various long text classification benchmark
datasets show that the enhanced transformer with rotary position embedding, namely RoFormer, can give better
performance compared to base

引用[13] 2104.09864v5.pdf p.12 id=1456

5
Conclusions
In this work, we proposed a new position embedding method that incorporates explicit relative position dependency in
self-attention to enhance the performance of transformer architectures. Our theoretical analysis indicates that relative
position can be naturally formulated using vector production in self-attention, with absolution position information
being encoded through a rotation matrix. In addition, we mathematically illustrated the advantageous properties of
the proposed method when applied to the Transformer. Finally, experiments on both English and Chinese benchmark
datasets demonstrate that our method encourages faster convergence in pre-training. The experimental results also show
that our proposed RoFormer can achieve better performance on long texts task.
References
Jonas Gehring, Michael Auli, David Grangier, Denis Yarats, and Yann N Dauphin. Convolutional sequence to sequence
learning. In International Conference on Machine Learning, pages 1243–1252. PMLR, 2017.
Md. Amirul Islam, Sen Jia, and Neil D. B. Bruce. How much position information do convolutional neural networks
encode? ArXiv, abs/2001.08248, 2020.
Ashish Vaswani, Noam Shazeer, Niki Parmar, Ja

引用[14] 2104.09864v5.pdf p.1 id=1397

ROFORMER: ENHANCED TRANSFORMER WITH ROTARY
POSITION EMBEDDING
Jianlin Su
Zhuiyi Technology Co., Ltd.
Zhuiyi Technology Co., Ltd.
Shenzhen
arXiv:2104.09864v5  [cs.CL]  8 Nov 2023
bojonesu@wezhuiyi.com
julianlu@wezhuiyi.com
Ahmed Murtadha
Zhuiyi Technology Co., Ltd.
Zhuiyi Technology Co., Ltd.
Shenzhen
mengjiayi@wezhuiyi.com
brucewen@wezhuiyi.com
November 9, 2023
Position encoding recently has shown effective in the transformer architecture. It enables valuable
supervision for dependency modeling between elements at different positions of the sequence. In
this paper, we first investigate various methods to integrate positional information into the learning
process of transformer-based language models. Then, we propose a novel method named Rotary
Position Embedding(RoPE) to effectively leverage the positional information. Specifically, the
proposed RoPE encodes the absolute position with a rotation matrix and meanwhile incorporates
the explicit relative position dependency in self-attention formulation. Notably, RoPE enables
valuable properties, including the flexibility of sequence length, decaying inter-token dependency
with increasing relative distances, and the capability of equip

引用[15] 2104.09864v5.pdf p.5 id=1418

3.2.2
General form
In order to generalize our results in 2D to any xi ∈Rd where d is even, we divide the d-dimension space into d/2
sub-spaces and combine them in the merit of the linearity of the inner product, turning f{q,k} into:
f{q,k}(xm, m) = Rd
where
−sin mθ1
cos mθ1

sin mθ1
cos mθ1

0
0
cos mθ2


0
0
sin mθ2
Rd

Θ,m =

...
...



0
0

0
0
is the rotary matrix with pre-defined parameters Θ = {θi = 10000−2(i−1)/d, i ∈[1, 2, ..., d/2]}. A graphic illustration
of RoPE is shown in Figure (1). Applying our RoPE to self-attention in Equation (2), we obtain:
Θ,mW qxm)⊺(Rd
q⊺
mkn = (Rd
Θ,m)⊺Rd
Θ,n−m = (Rd
where Rd
Θ,n. Note that Rd
Θ is an orthogonal matrix, which ensures stability during the process of
encoding position information. In addition, due to the sparsity of Rd
Equation (16) is not computationally efficient; we provide another realization in theoretical explanation.
In contrast to the additive nature of position embedding method adopted in the previous works, i.e., Equations (3)
to (10), our approach is multiplicative. Moreover, RoPE naturally incorporates relative position information through
rotation matrix product instead of altering terms in the expanded fo

引用[16] 2104.09864v5.pdf p.5 id=1419

multiplicative. Moreover, RoPE naturally incorporates relative position information through
rotation matrix product instead of altering terms in the expanded formulation of additive position encoding when applied
with self-attention.
θ1
Constant
(x1, x2)
Query / Key
m
Position
d=2
θ1
θ2
θd/2-1 θd/2
Enhanced
Transformer
with
Rotary
Position
Embedding
Query / Key
Figure 1: Implementation of Rotary Position Embedding(RoPE).

## n03 / auto_on / completed

RoFormer 的 RoPE 用旋转矩阵编码绝对位置，同时在自注意力公式中引入显式的相对位置依赖[12][14]。与以往工作采用的加性位置嵌入不同，该方法是乘法式的；RoPE 通过旋转矩阵乘积自然地纳入相对位置信息，而不是在自注意力中修改加性位置编码展开式里的项[15][16]。其结论也说明，绝对位置信息通过旋转矩阵编码，相对位置可利用自注意力中的向量乘积自然表达[13]。

来源：
[12] 2104.09864v5.pdf，p.2；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[13] 2104.09864v5.pdf，p.12；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[14] 2104.09864v5.pdf，p.1；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[15] 2104.09864v5.pdf，p.5；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)
[16] 2104.09864v5.pdf，p.5；[固定版本PDF](https://arxiv.org/pdf/2104.09864v5)

引用[12] 2104.09864v5.pdf p.2 id=1402

 encoding from the
perspective of Neural ODE Chen et al. [2018a], and the authors of Wang et al. [2020] have proposed to model the
position information in complex space. Despite the effectiveness of these approaches, they commonly add the position
information to the context representation and thus render them unsuitable for the linear self-attention architecture.
In this paper, we introduce a novel method, namely Rotary Position Embedding(RoPE), to leverage the positional
information into the learning process of PLMS. Specifically, RoPE encodes the absolute position with a rotation matrix
and meanwhile incorporates the explicit relative position dependency in self-attention formulation. Note that the
proposed RoPE is prioritized over the existing methods through valuable properties, including the sequence length
flexibility, decaying inter-token dependency with increasing relative distances, and the capability of equipping the
linear self-attention with relative position encoding. Experimental results on various long text classification benchmark
datasets show that the enhanced transformer with rotary position embedding, namely RoFormer, can give better
performance compared to base

引用[13] 2104.09864v5.pdf p.12 id=1456

5
Conclusions
In this work, we proposed a new position embedding method that incorporates explicit relative position dependency in
self-attention to enhance the performance of transformer architectures. Our theoretical analysis indicates that relative
position can be naturally formulated using vector production in self-attention, with absolution position information
being encoded through a rotation matrix. In addition, we mathematically illustrated the advantageous properties of
the proposed method when applied to the Transformer. Finally, experiments on both English and Chinese benchmark
datasets demonstrate that our method encourages faster convergence in pre-training. The experimental results also show
that our proposed RoFormer can achieve better performance on long texts task.
References
Jonas Gehring, Michael Auli, David Grangier, Denis Yarats, and Yann N Dauphin. Convolutional sequence to sequence
learning. In International Conference on Machine Learning, pages 1243–1252. PMLR, 2017.
Md. Amirul Islam, Sen Jia, and Neil D. B. Bruce. How much position information do convolutional neural networks
encode? ArXiv, abs/2001.08248, 2020.
Ashish Vaswani, Noam Shazeer, Niki Parmar, Ja

引用[14] 2104.09864v5.pdf p.1 id=1397

ROFORMER: ENHANCED TRANSFORMER WITH ROTARY
POSITION EMBEDDING
Jianlin Su
Zhuiyi Technology Co., Ltd.
Zhuiyi Technology Co., Ltd.
Shenzhen
arXiv:2104.09864v5  [cs.CL]  8 Nov 2023
bojonesu@wezhuiyi.com
julianlu@wezhuiyi.com
Ahmed Murtadha
Zhuiyi Technology Co., Ltd.
Zhuiyi Technology Co., Ltd.
Shenzhen
mengjiayi@wezhuiyi.com
brucewen@wezhuiyi.com
November 9, 2023
Position encoding recently has shown effective in the transformer architecture. It enables valuable
supervision for dependency modeling between elements at different positions of the sequence. In
this paper, we first investigate various methods to integrate positional information into the learning
process of transformer-based language models. Then, we propose a novel method named Rotary
Position Embedding(RoPE) to effectively leverage the positional information. Specifically, the
proposed RoPE encodes the absolute position with a rotation matrix and meanwhile incorporates
the explicit relative position dependency in self-attention formulation. Notably, RoPE enables
valuable properties, including the flexibility of sequence length, decaying inter-token dependency
with increasing relative distances, and the capability of equip

引用[15] 2104.09864v5.pdf p.5 id=1418

3.2.2
General form
In order to generalize our results in 2D to any xi ∈Rd where d is even, we divide the d-dimension space into d/2
sub-spaces and combine them in the merit of the linearity of the inner product, turning f{q,k} into:
f{q,k}(xm, m) = Rd
where
−sin mθ1
cos mθ1

sin mθ1
cos mθ1

0
0
cos mθ2


0
0
sin mθ2
Rd

Θ,m =

...
...



0
0

0
0
is the rotary matrix with pre-defined parameters Θ = {θi = 10000−2(i−1)/d, i ∈[1, 2, ..., d/2]}. A graphic illustration
of RoPE is shown in Figure (1). Applying our RoPE to self-attention in Equation (2), we obtain:
Θ,mW qxm)⊺(Rd
q⊺
mkn = (Rd
Θ,m)⊺Rd
Θ,n−m = (Rd
where Rd
Θ,n. Note that Rd
Θ is an orthogonal matrix, which ensures stability during the process of
encoding position information. In addition, due to the sparsity of Rd
Equation (16) is not computationally efficient; we provide another realization in theoretical explanation.
In contrast to the additive nature of position embedding method adopted in the previous works, i.e., Equations (3)
to (10), our approach is multiplicative. Moreover, RoPE naturally incorporates relative position information through
rotation matrix product instead of altering terms in the expanded fo

引用[16] 2104.09864v5.pdf p.5 id=1419

multiplicative. Moreover, RoPE naturally incorporates relative position information through
rotation matrix product instead of altering terms in the expanded formulation of additive position encoding when applied
with self-attention.
θ1
Constant
(x1, x2)
Query / Key
m
Position
d=2
θ1
θ2
θd/2-1 θd/2
Enhanced
Transformer
with
Rotary
Position
Embedding
Query / Key
Figure 1: Implementation of Rotary Position Embedding(RoPE).

## n04 / agent_on / completed

原始 FlashAttention 论文指出，IO 减少涉及的 GPU 内存层级为 GPU 高带宽内存（HBM）与 GPU 片上 SRAM，并通过 tiling 技术减少这两者之间的内存读写/传输[12]。该论文进一步说明，tiling 可避免在（相对较慢的）GPU HBM 上物化大型 N×N 注意力矩阵[14]。

来源：
[12] 2205.14135v2.pdf，p.1；[固定版本PDF](https://arxiv.org/pdf/2205.14135v2)
[14] 2205.14135v2.pdf，p.2；[固定版本PDF](https://arxiv.org/pdf/2205.14135v2)

引用[12] 2205.14135v2.pdf p.1 id=1397

FlashAttention: Fast and Memory-Eﬃcient Exact Attention
with IO-Awareness
Tri Dao†, Daniel Y. Fu†, Stefano Ermon†, Atri Rudra‡, and Christopher Ré†
†Department of Computer Science, Stanford University
‡Department of Computer Science and Engineering, University at Buﬀalo, SUNY
arXiv:2205.14135v2  [cs.LG]  23 Jun 2022
{trid,danfu}@cs.stanford.edu, ermon@stanford.edu, atri@buffalo.edu,
chrismre@cs.stanford.edu
June 24, 2022
Transformers are slow and memory-hungry on long sequences, since the time and memory complexity
of self-attention are quadratic in sequence length. Approximate attention methods have attempted
to address this problem by trading oﬀmodel quality to reduce the compute complexity, but often do
not achieve wall-clock speedup. We argue that a missing principle is making attention algorithms IO-
aware—accounting for reads and writes between levels of GPU memory. We propose FlashAttention,
an IO-aware exact attention algorithm that uses tiling to reduce the number of memory reads/writes
between GPU high bandwidth memory (HBM) and GPU on-chip SRAM. We analyze the IO complexity
of FlashAttention, showing that it requires fewer HBM accesses than standard attention, and is
opt

引用[14] 2205.14135v2.pdf p.2 id=1401

KT: d x N
Q: N x d
QKT: N x N
SRAM: 19 TB/s (20 MB)
GPU
SRAM
GPU
HBM: 1.5 TB/s (40 GB)
Inner Loop
HBM
Copy
Main Memory
DRAM: 12.8 GB/s
(>1 TB)
(CPU DRAM)
Memory Hierarchy with
Bandwidth & Memory Size
sm(QKT)V: N x d
Figure 1: Left: FlashAttention uses tiling to prevent materialization of the large 𝑁× 𝑁attention matrix
(dotted box) on (relatively) slow GPU HBM. In the outer loop (red arrows), FlashAttention loops through
blocks of the K and V matrices and loads them to fast on-chip SRAM. In each block, FlashAttention
loops over blocks of Q matrix (blue arrows), loading them to SRAM, and writing the output of the attention
computation back to HBM. Right: Speedup over the PyTorch implementation of attention on GPT-2.
FlashAttention does not read and write the large 𝑁× 𝑁attention matrix to HBM, resulting in an 7.6×
speedup on the attention computation.
GPUs, compute speed has out-paced memory speed [61, 62, 63], and most operations in Transformers are
bottlenecked by memory accesses [43]. IO-aware algorithms have been critical for similar memory-bound
operations, when reading and writing data can account for a large portion of the runtime—such as database
joins [71], image processing [

## n04 / agent_off / completed

当前证据不足，无法可靠回答以下需求：
- FlashAttention：According to the original FlashAttention paper, which two GPU memory levels are involved in the IO reduction, and which implementation technique reduces those transfers?；缺少原始 FlashAttention 论文中关于参与 IO 归约的两个 GPU 内存层级（如 HBM 与 SRAM）以及减少传输的实现技术（如分块/平铺）的说明。

## n04 / auto_on / degraded

补查未完成，以下仅依据初检证据回答，仍保留原有缺口：
当前证据不足。提供的上下文未包含 FlashAttention 原论文中关于 IO 缩减所涉及的两个 GPU 内存层级以及减少传输的实现技术的信息；[1] 仅提到 Self-RAG 使用 FlashAttention 提升长上下文训练效率，未涉及你所问的具体机制。

引用[1] 2310.11511v1.pdf p.19 id=1128

We use Deepspeed stage 3 (Rajbhandari et al., 2020) to conduct multi-GPU distributed training, with training precision Bfloat16 enabled. FlashAttention (Dao et al., 2022) is used to make the long-context training more efficient. We run inference of our trained models using 1-2 Quadro RTX 6000 GPUs with 24GB memory.

## n05 / agent_off / completed

当前证据不足，无法可靠回答以下需求：
- RoFormer：According to the original RoFormer paper, what was the exact total cloud-compute bill in US dollars for its pretraining experiments?；缺少原始 RoFormer 论文中关于预训练实验的云计算账单总额（美元）的任何信息；该主题的论文不在本地库存中。

## n05 / agent_on / completed

当前证据不足，无法可靠回答以下需求：
- RoFormer：According to the original RoFormer paper, what was the exact total cloud-compute bill in US dollars for its pretraining experiments?；RoFormer原始论文中预训练实验的确切云计算总费用（美元）未在所提供片段中出现；该财务/计算成本信息可能在实验或致谢部分，但当前片段未覆盖。
本轮检索预算已用完，仍有上述内容未核实。

## n06 / agent_on / failed

ValueError: External paper title must name the bound requirement subject.

## n06 / agent_off / completed

当前证据不足，无法可靠回答以下需求：
- original FlashAttention：According to the original FlashAttention paper, what was the total measured energy consumption in kWh for all of its reported training experiments?；原始FlashAttention论文本身不在本地文献清单中，且现有段落中没有任何一处给出该论文全部训练实验的总能耗（kWh）数值。
