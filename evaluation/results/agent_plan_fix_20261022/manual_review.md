# 修复后三道开发题的原文核对

本助手人工阅读实际答案与原文后记录标签；非独立第三方盲评。沿用原冻结评分点，未改写旧P2.5结果。

## b02

How does DCNN initialize neuron biases in different layers, and why does it use positive biases in selected layers?

DCNN将第二、第四、第五卷积层以及全连接隐藏层的神经元偏置初始化为常数1[1]；将其余层的神经元偏置初始化为常数0[2]。使用正偏置的原因是，这种初始化在早期学习阶段为ReLU提供正输入，从而加速学习[1]。

原冻结标准严格通过：True；核心完整点：3/3。

- 评分点1：covered；指定卷积层2/4/5及全连接隐藏层偏置为1。
- 评分点2：covered；其余层偏置为0。
- 评分点3：covered；正输入供给ReLU，加速早期学习。

本答案实际引用的当前库原文：

[1] → chunk 177，DCNN.pdf，第5页：

We initialized the weights in each layer from a zero-mean Gaussian distribution with standard deviation 0.01. We ini- tialized the neuron biases in the second, fourth, and fifth convolutional layers, as well as in the fully connected hidden layers, with the constant 1. This initialization accelerates the early stages of learning by providing the ReLUs with positive inputs.

[2] → chunk 178，DCNN.pdf，第5页：

We initialized the neuron biases in the remaining lay- ers with the constant 0. We used an equal learning rate for all layers, which we adjusted manually throughout training. The heuristic which we followed was to divide the learning rate by 10 when the vali- dation error rate stopped improving with the current learning rate. The learning rate was initialized at 0.01 and reduced three times prior to termination.

## b03

In VGG multi-scale training, how is the training scale S sampled, what crop size is used, and how is the multi-scale model initialized?

VGG多尺度训练中，每张训练图像通过从范围[Smin, Smax]随机采样S进行单独缩放，实验中取Smin = 256、Smax = 512 [1]；裁剪尺寸固定为224×224 [2]；多尺度模型通过微调一个相同配置、以固定S = 384预训练的单尺度模型的所有层来初始化 [4]。

原冻结标准严格通过：False；核心完整点：2/3。

- 评分点1：partial；范围[256,512]正确；未说明S为等比例缩放图像的最短边。
- 评分点2：covered；固定224×224裁剪。
- 评分点3：covered；相同配置、S=384预训练单尺度模型的全部层微调。

本答案实际引用的当前库原文：

[1] → chunk 262，VGG.pdf，第4页：

In our experiments, we evaluated models trained at two ﬁxed scales: S = 256 (which has been widely used in the prior art (Krizhevsky et al., 2012; Zeiler & Fergus, 2013; Sermanet et al., 2014)) and S = 384. Given a ConvNet conﬁguration, we ﬁrst trained the network using S = 256. To speed-up training of the S = 384 network, it was initialised with the weights pre-trained with S = 256, and we used a smaller initial learning rate of 10−3. The second approach to setting S is multi-scale training, where each training image is individually rescaled by randomly sampling S from a certain range [Smin, Smax] (we used Smin = 256 and Smax = 512).

[2] → chunk 260，VGG.pdf，第4页：

Let S be the smallest side of an isotropically-rescaled training image, from which the ConvNet input is cropped (we also refer to S as the training scale). While the crop size is ﬁxed to 224 × 224, in principle S can take on any value not less than 224: for S = 224 the crop will capture whole-image statistics, completely spanning the smallest side of a training image; for S ≫224 the crop will correspond to a small part of the image, containing a small object or an object part.

[4] → chunk 264，VGG.pdf，第5页：

Published as a conference paper at ICLR 2015 model is trained to recognise objects over a wide range of scales. For speed reasons, we trained multi-scale models by ﬁne-tuning all layers of a single-scale model with the same conﬁguration, pre-trained with ﬁxed S = 384.

## b06

What do DCNN and VGG report about the usefulness of local response normalization, and what computational costs does VGG mention?

DCNN报告局部响应归一化有助于泛化[4]，并将top-1和top-5错误率分别降低1.4%和1.2%[6]；该方案在CIFAR-10上也被验证有效（四层CNN无归一化时为13%测试错误率，有归一化时为11%）[6]。

VGG报告局部响应归一化在ILSVRC数据集上不提升性能[3]，且带局部响应归一化的A-LRN网络相较不含任何归一化层的模型A没有改进[10]。

关于计算成本，VGG提到这种归一化会增加内存消耗和计算时间[3]。

原冻结标准严格通过：False；核心完整点：2/3。

- 评分点1：covered；泛化收益、top-1/top-5改善及附加CIFAR-10事实均有原文支持；数值保留原文%写法。
- 评分点2：partial；无性能收益及A-LRN比较正确；未明确通常省略LRN、仅一个配置例外的架构事实。
- 评分点3：covered；内存消耗与计算时间均增加。

本答案实际引用的当前库原文：

[3] → chunk 235，VGG.pdf，第2页：

The conﬁguration of the fully connected layers is the same in all networks. All hidden layers are equipped with the rectiﬁcation (ReLU (Krizhevsky et al., 2012)) non-linearity. We note that none of our networks (except for one) contain Local Response Normalisation (LRN) normalisation (Krizhevsky et al., 2012): as will be shown in Sect. 4, such normalisation does not improve the performance on the ILSVRC dataset, but leads to increased memory con- sumption and computation time.

[4] → chunk 142，DCNN.pdf，第3页：

4.3. Local response normalization ReLUs have the desirable property that they do not require input normalization to prevent them from saturating. If at least some training examples produce a positive input to a ReLU, learning will happen in that neuron. However, we still find that the following local normalization scheme aids gen- x, y the activity of a neuron com- eralization.

[6] → chunk 146，DCNN.pdf，第3页：

Response normalization reduces our top-1 and top-5 error rates by 1.4% and 1.2%, respectively. We also verified the effectiveness of this scheme on the CIFAR-10 dataset: a four-layer CNN achieved a 13% test error rate without normalization and 11% with normalization.c

[10] → chunk 279，VGG.pdf，第6页：

4.1 SINGLE SCALE EVALUATION We begin with evaluating the performance of individual ConvNet models at a single scale with the layer conﬁgurations described in Sect. 2.2. The test image size was set as follows: Q = S for ﬁxed S, and Q = 0.5(Smin + Smax) for jittered S ∈[Smin, Smax]. The results of are shown in Table 3. First, we note that using local response normalisation (A-LRN network) does not improve on the model A without any normalisation layers.

