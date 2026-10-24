# P2.5 逐题原文与语义核对

评分点与判定在semantic_review.json；此文列实际答案、原因和实际引用原文。

## b01

Which optimizer and beta1, beta2, and epsilon values does the Transformer in Attention Is All You Need use?

### rag: 通过

Transformer 使用的是 Adam 优化器，β1 = 0.9、β2 = 0.98、ϵ = 10⁻⁹ [7]。

评分：covered, covered

依据：Adam及三个常数完整，引用[7]的66原文逐项支持。

[7] Attention is all you need.pdf p.7 / chunk66

> 5.3 Optimizer We used the Adam optimizer [17] with β1 = 0.9, β2 = 0.98 and ϵ = 10−9. We varied the learning rate over the course of training, according to the formula: lrate = d−0.5 model · min(step_num−0.5, step_num · warmup_steps−1.5) (3) This corresponds to increasing the learning rate linearly for the ﬁrst warmup_steps training steps, and decreasing it thereafter proportionally to the inverse square root of the step number. We used warmup_steps = 4000.

### agent: 通过

《Attention Is All You Need》中的Transformer使用Adam优化器，β1 = 0.9，β2 = 0.98，ϵ = 10−9 [7]。

评分：covered, covered

依据：与固定RAG相同的事实与引用；复核通过不额外计分。

[7] Attention is all you need.pdf p.7 / chunk66

> 5.3 Optimizer We used the Adam optimizer [17] with β1 = 0.9, β2 = 0.98 and ϵ = 10−9. We varied the learning rate over the course of training, according to the formula: lrate = d−0.5 model · min(step_num−0.5, step_num · warmup_steps−1.5) (3) This corresponds to increasing the learning rate linearly for the ﬁrst warmup_steps training steps, and decreasing it thereafter proportionally to the inverse square root of the step number. We used warmup_steps = 4000.

## b02

How does DCNN initialize neuron biases in different layers, and why does it use positive biases in selected layers?

### rag: 通过

DCNN 将第二、第四、第五卷积层以及全连接隐藏层的神经元偏置初始化为常数 1 [1]；其余层的神经元偏置初始化为常数 0 [2]。使用正偏置的目的是为 ReLU 提供正输入，从而加速学习初期阶段 [1]。

评分：covered, covered, covered

依据：正确区分卷积2/4/5与FC隐藏层偏置1、其余0，并说明ReLU正输入促进早期学习；[1]/[2]对应177/178。

[1] DCNN.pdf p.5 / chunk177

> We initialized the weights in each layer from a zero-mean Gaussian distribution with standard deviation 0.01. We ini- tialized the neuron biases in the second, fourth, and fifth convolutional layers, as well as in the fully connected hidden layers, with the constant 1. This initialization accelerates the early stages of learning by providing the ReLUs with positive inputs.

[2] DCNN.pdf p.5 / chunk178

> We initialized the neuron biases in the remaining lay- ers with the constant 0. We used an equal learning rate for all layers, which we adjusted manually throughout training. The heuristic which we followed was to divide the learning rate by 10 when the vali- dation error rate stopped improving with the current learning rate. The learning rate was initialized at 0.01 and reduced three times prior to termination.

### agent: 未通过

(无交付答案)

评分：missing, missing, missing

依据：规划第二需求摘录why does it...，未包含DCNN主体；当前校验拒绝，未生成答案。

## b03

In VGG multi-scale training, how is the training scale S sampled, what crop size is used, and how is the multi-scale model initialized?

### rag: 未通过

在多尺度训练中，每张训练图像会通过对 S 在一定范围 [Smin, Smax] 内随机采样进行单独缩放，文中使用的范围是 Smin = 256、Smax = 512（[1]）。裁剪尺寸固定为 224 × 224（[2]）。多尺度模型主要是通过微调（fine-tuning）一个相同配置的单尺度模型的所有层来训练的，该单尺度模型以固定 S = 384 预训练（[4]）。

评分：partial, covered, covered

依据：给出[256,512]、224x224与S=384初始化/微调所有层；冻结第1点同时要求说明S为等比例缩放后的最短边，实际未说明，按合取评分点记partial。

[1] VGG.pdf p.4 / chunk262

> In our experiments, we evaluated models trained at two ﬁxed scales: S = 256 (which has been widely used in the prior art (Krizhevsky et al., 2012; Zeiler & Fergus, 2013; Sermanet et al., 2014)) and S = 384. Given a ConvNet conﬁguration, we ﬁrst trained the network using S = 256. To speed-up training of the S = 384 network, it was initialised with the weights pre-trained with S = 256, and we used a smaller initial learning rate of 10−3. The second approach to setting S is multi-scale training, where each training image is individually rescaled by randomly sampling S from a certain range [Smin, Smax] (we used Smin = 256 and Smax = 512).

[2] VGG.pdf p.4 / chunk260

> Let S be the smallest side of an isotropically-rescaled training image, from which the ConvNet input is cropped (we also refer to S as the training scale). While the crop size is ﬁxed to 224 × 224, in principle S can take on any value not less than 224: for S = 224 the crop will capture whole-image statistics, completely spanning the smallest side of a training image; for S ≫224 the crop will correspond to a small part of the image, containing a small object or an object part.

[4] VGG.pdf p.5 / chunk264

> Published as a conference paper at ICLR 2015 model is trained to recognise objects over a wide range of scales. For speed reasons, we trained multi-scale models by ﬁne-tuning all layers of a single-scale model with the same conﬁguration, pre-trained with ﬁxed S = 384.

### agent: 未通过

(无交付答案)

评分：missing, missing, missing

依据：规划摘录不在原问题中，被逐字引文校验拒绝；未生成答案。

## b04

After the token embeddings are projected in ColBERT, how are they normalized, and what equivalence and value range does this give to their dot products?

### rag: 通过

在 ColBERT 中，输出嵌入会被归一化，使每个嵌入的 L2 范数等于 1 [1]。这样任意两个嵌入的点积就等价于它们的余弦相似度，取值落在 [−1, 1] 区间内 [1]。

评分：covered, covered

依据：单位L2范数、点积=余弦、[-1,1]均由[1]608支持。

[1] 2004.12832v2.pdf p.4 / chunk608

> Finally, the output embeddings are normalized so each has L2 norm equal to one. Te result is that the dot-product of any two embeddings becomes equivalent to their cosine similarity, falling in the [−1, 1] range.

### agent: 通过

ColBERT 对投影后的 token 嵌入进行归一化，使每个嵌入的 L2 范数等于 1 [1][2]。由此，任意两个嵌入的点积等价于其余弦相似度，取值范围为 [−1, 1] [1]。

评分：covered, covered

依据：同样完整；[1]608支持数值/相似度，[2]611的Normalize公式补充表示处理顺序。

[1] 2004.12832v2.pdf p.4 / chunk608

> Finally, the output embeddings are normalized so each has L2 norm equal to one. Te result is that the dot-product of any two embeddings becomes equivalent to their cosine similarity, falling in the [−1, 1] range.

[2] 2004.12832v2.pdf p.4 / chunk611

> In summary, given q = q0q1...ql and d = d0d1...dn, we compute the bags of embeddings Eq and Ed in the following manner, where # refers to the [mask] tokens: Eq := Normalize( CNN( BERT(“[Q]q0q1...ql##...#”) ) ) (1) Ed := Filter( Normalize( CNN( BERT(“[D]d0d1...dn”) ) ) ) (2) 3.3 Late Interaction Given the representation of a query q and a document d, the rel- evance score of d to q, denoted as Sq,d, is estimated via late in- teraction between their bags of contextualized embeddings.

## b05

Which checkpoints are averaged for Transformer base and big models, and how does this differ from the way VGG combines multiple model predictions?

### rag: 通过

Transformer base 模型平均的是最后 5 个 checkpoint（这些 checkpoint 以 10 分钟间隔写入）；big 模型平均的是最后 20 个 checkpoint [1]。VGG 则是通过平均多个模型的 softmax 类别后验概率来组合输出，从而利用模型间的互补性提升性能 [2]。

评分：covered, covered, covered

依据：5/20检查点与VGG多个模型softmax后验平均分别正确，句间则字表达操作对象差异；[1]/[2]为73/296。

[1] Attention is all you need.pdf p.8 / chunk73

> The Transformer (big) model trained for English-to-French used dropout rate Pdrop = 0.1, instead of 0.3. For the base models, we used a single model obtained by averaging the last 5 checkpoints, which were written at 10-minute intervals. For the big models, we averaged the last 20 checkpoints. We used beam search with a beam size of 4 and length penalty α = 0.6 [31]. These hyperparameters were chosen after experimentation on the development set.

[2] VGG.pdf p.7 / chunk296

> In this part of the exper- iments, we combine the outputs of several models by averaging their soft-max class posteriors. This improves the performance due to complementarity of the models, and was used in the top ILSVRC submissions in 2012 (Krizhevsky et al., 2012) and 2013 (Zeiler & Fergus, 2013; Sermanet et al., 2014).

### agent: 通过

Transformer base模型平均最后5个checkpoint（以10分钟间隔写入），big模型平均最后20个checkpoint[1]。VGG则通过平均多个模型的soft-max类别后验概率来组合预测[2]，这与Transformer按时间顺序选取末尾checkpoint做权重的平均方式不同。

评分：covered, covered, covered

依据：5/20与类别后验平均正确，显式说明checkpoint权重平均和预测后验平均的区别，未编造跨任务性能优势。

[1] Attention is all you need.pdf p.8 / chunk73

> The Transformer (big) model trained for English-to-French used dropout rate Pdrop = 0.1, instead of 0.3. For the base models, we used a single model obtained by averaging the last 5 checkpoints, which were written at 10-minute intervals. For the big models, we averaged the last 20 checkpoints. We used beam search with a beam size of 4 and length penalty α = 0.6 [31]. These hyperparameters were chosen after experimentation on the development set.

[2] VGG.pdf p.7 / chunk296

> In this part of the exper- iments, we combine the outputs of several models by averaging their soft-max class posteriors. This improves the performance due to complementarity of the models, and was used in the top ILSVRC submissions in 2012 (Krizhevsky et al., 2012) and 2013 (Zeiler & Fergus, 2013; Sermanet et al., 2014).

## b06

What do DCNN and VGG report about the usefulness of local response normalization, and what computational costs does VGG mention?

### rag: 通过

关于局部响应归一化（Local Response Normalization, LRN）：

- **DCNN**：报告称该归一化方案有助于泛化，具体使 top-1 和 top-5 错误率分别降低 1.4% 和 1.2%（[6]）。
- **VGG**：总体上认为 LRN 并不能提升 ILSVRC 数据集上的性能，反而会增加内存消耗和计算时间（[3]）；在单尺度评估中，使用 LRN 的 A-LRN 网络相比不含归一化层的模型 A 没有提升（[10]）。需注意，VGG 在架构上"除一个网络外"均不含 LRN（[3]）。

关于 VGG 提到的计算成本：

- VGG 指出 LRN 会增加内存消耗和计算时间（[3]）。除此之外，所给证据未提及 VGG 的其他计算成本细节。

评分：covered, covered, covered

依据：DCNN错误率改善、VGG无收益且A-LRN例外、内存与时间开销均完整；末尾关于未提供其他成本的说明多余，但没有遗漏所问事实。

[3] VGG.pdf p.2 / chunk235

> The conﬁguration of the fully connected layers is the same in all networks. All hidden layers are equipped with the rectiﬁcation (ReLU (Krizhevsky et al., 2012)) non-linearity. We note that none of our networks (except for one) contain Local Response Normalisation (LRN) normalisation (Krizhevsky et al., 2012): as will be shown in Sect. 4, such normalisation does not improve the performance on the ILSVRC dataset, but leads to increased memory con- sumption and computation time.

[6] DCNN.pdf p.3 / chunk146

> Response normalization reduces our top-1 and top-5 error rates by 1.4% and 1.2%, respectively. We also verified the effectiveness of this scheme on the CIFAR-10 dataset: a four-layer CNN achieved a 13% test error rate without normalization and 11% with normalization.c

[10] VGG.pdf p.6 / chunk279

> 4.1 SINGLE SCALE EVALUATION We begin with evaluating the performance of individual ConvNet models at a single scale with the layer conﬁgurations described in Sect. 2.2. The test image size was set as follows: Q = S for ﬁxed S, and Q = 0.5(Smin + Smax) for jittered S ∈[Smin, Smax]. The results of are shown in Table 3. First, we note that using local response normalisation (A-LRN network) does not improve on the model A without any normalisation layers.

### agent: 未通过

(无交付答案)

评分：missing, missing, missing

依据：模型为两方法各抽取同一What do DCNN and VGG...片段，包含另一已声明主体，被主体隔离校验拒绝。

## b07

What does DPR's top-k retrieval accuracy count, and which metrics does Self-RAG use for correctness, fluency, and citations on ASQA?

### rag: 未通过

DPR 的 top-k 检索准确率按“top 20/100 检索到的段落中包含答案的百分比”来衡量[8]。

Self-RAG 在 ASQA 上使用的指标为：正确性用 str-em（官方 correctness 指标），流畅性用基于 MAUVE 的指标，引用方面用 citation precision 和 recall[1]。

评分：partial, covered, covered, covered

依据：ASQA三类指标完整；DPR回答复述表2注434的passages措辞，未明确第2节400定义的“以问题为单位、Top-k至少一段含答案跨度”，冻结第1点评partial。434表注本身措辞有歧义，这不是无来源编造；保留为评审敏感案例。

[1] 2310.11511v1.pdf p.7 / chunk1004

> (2023); Schick et al. Long-form generation tasks include a biography generation task (Min et al., 2023) and a long-form QA task ALCE-ASQA Gao et al. (2023); Stelmakh et al. We use FactScore (Min et al., 2023) to evaluate biographies, and we use official metrics of correctness (str-em), fluency based on MAUVE (Pillutla et al., 2021), and citation precision and recall (Gao et al., 2023) for ASQA.

[8] 2004.04906v3.pdf p.5 / chunk434

> Training Retriever Top-20 NQ TriviaQA WQ None BM25 59.1 66.9 55.0 78.4 79.4 73.2 DPR Single BM25 + DPR 76.6 79.8 71.0 79.4 75.0 DPR 78.8 Multi 79.9 BM25 + DPR 78.0 74.7 Table 2: Top-20 & Top-100 retrieval accuracy on test sets, measured as the percentage of top 20/100 retrieved passages that contain the answer. Single and Multi denote that our Dense Passage Retriever (DPR) was trained using individial or combined training datasets (all the datasets excluding SQuAD).

### agent: 未通过

DPR的top-k检索准确率计为top 20/100检索到的段落中包含答案的百分比[8]。Self-RAG在ASQA上使用str-em衡量正确性、MAUVE衡量流畅度、citation precision和recall衡量引用[1]。

评分：partial, covered, covered, covered

依据：与固定RAG相同：ASQA完整，DPR引用434却未澄清问题层面分母；复核通过不能消除此定义缺口。表注文字支持其表述，因此不标为凭空断言。

[1] 2310.11511v1.pdf p.7 / chunk1004

> (2023); Schick et al. Long-form generation tasks include a biography generation task (Min et al., 2023) and a long-form QA task ALCE-ASQA Gao et al. (2023); Stelmakh et al. We use FactScore (Min et al., 2023) to evaluate biographies, and we use official metrics of correctness (str-em), fluency based on MAUVE (Pillutla et al., 2021), and citation precision and recall (Gao et al., 2023) for ASQA.

[8] 2004.04906v3.pdf p.5 / chunk434

> Training Retriever Top-20 NQ TriviaQA WQ None BM25 59.1 66.9 55.0 78.4 79.4 73.2 DPR Single BM25 + DPR 76.6 79.8 71.0 79.4 75.0 DPR 78.8 Multi 79.9 BM25 + DPR 78.0 74.7 Table 2: Top-20 & Top-100 retrieval accuracy on test sets, measured as the percentage of top 20/100 retrieved passages that contain the answer. Single and Multi denote that our Dense Passage Retriever (DPR) was trained using individial or combined training datasets (all the datasets excluding SQuAD).

## b08

What hardware and approximate training duration do the Transformer base model and DCNN report for their own experiments?

### rag: 通过

Transformer base model：使用 8 块 P100 GPU，训练约 12 小时（100,000 步）[8][9]。DCNN：使用两块 GTX 580 3GB GPU，训练约 5–6 天（约 90 个训练周期）[2][3]。

评分：covered, covered

依据：Transformer base的8 P100/100000步/12小时与DCNN的2 GTX580 3GB/5-6天完整；额外90周期有179支持，未计算跨任务加速比。

[2] DCNN.pdf p.2 / chunk122

> In the end, the network’s size is limited mainly by the amount of memory available on current GPUs and by the amount of training time that we are willing to tolerate. Our network takes between 5 and 6 days to train on two GTX 580 3GB GPUs.

[3] DCNN.pdf p.5 / chunk179

> We trained the network for roughly 90 cycles through the training set of 1.2 million images, which took 5–6 days on two NVIDIA GTX 580 3GB GPUs.

[8] Attention is all you need.pdf p.2 / chunk12

> In this work we propose the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output. The Transformer allows for signiﬁcantly more parallelization and can reach a new state of the art in translation quality after being trained for as little as twelve hours on eight P100 GPUs.

[9] Attention is all you need.pdf p.7 / chunk65

> For our base models using the hyperparameters described throughout the paper, each training step took about 0.4 seconds. We trained the base models for a total of 100,000 steps or 12 hours. For our big models,(described on the bottom line of table 3), step time was 1.0 seconds. The big models were trained for 300,000 steps (3.5 days).

### agent: 通过

Transformer base模型使用8块P100 GPU训练，约12小时（100,000步）[8][9]。DCNN在2块GTX 580 3GB GPU上训练约5–6天，约90个训练周期[2][3]。

评分：covered, covered

依据：与固定RAG相同，12/65及122/179原文支持硬件、步数和训练时间；未作同条件速度排名。

[2] DCNN.pdf p.2 / chunk122

> In the end, the network’s size is limited mainly by the amount of memory available on current GPUs and by the amount of training time that we are willing to tolerate. Our network takes between 5 and 6 days to train on two GTX 580 3GB GPUs.

[3] DCNN.pdf p.5 / chunk179

> We trained the network for roughly 90 cycles through the training set of 1.2 million images, which took 5–6 days on two NVIDIA GTX 580 3GB GPUs.

[8] Attention is all you need.pdf p.2 / chunk12

> In this work we propose the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output. The Transformer allows for signiﬁcantly more parallelization and can reach a new state of the art in translation quality after being trained for as little as twelve hours on eight P100 GPUs.

[9] Attention is all you need.pdf p.7 / chunk65

> For our base models using the hyperparameters described throughout the paper, each training step took about 0.4 seconds. We trained the base models for a total of 100,000 steps or 12 hours. For our big models,(described on the bottom line of table 3), step time was 1.0 seconds. The big models were trained for 300,000 steps (3.5 days).

## b09

How does RAG-Sequence's Thorough Decoding score a candidate absent from a document's beam, and how does Self-RAG use critique-token probabilities to score output segments?

### rag: 通过

关于 RAG-Sequence 的 Thorough Decoding：对某个候选假设 y，若它未出现在某文档 z 的 beam 中，则对该文档额外做一次前向计算，将生成器概率与 pη(z|x) 相乘，再跨各 beam 求和得到边际概率（[7]）。

关于 Self-RAG 的评审 token 概率评分：对每个评审 token 组 G（如 ISREL），以最理想反思 token 的生成概率在该组所有 token 概率中的占比作为该组得分 sG t（[3]）；段得分由生成概率 p(yt|x, d, y<t) 加上各评审组得分的加权线性和 S(Critique)=Σ_{G∈G} wG·sG t（G={ISREL, ISSUP, ISUSE}）构成（[3]）。该加权线性和的段得分用于段级 beam search，从而按用户偏好定制模型行为（[4]）。

评分：covered, covered, covered

依据：RAG遗漏beam候选的额外前向、检索概率加权边际及Self-RAG归一化critique加权/段级beam均完整；[7]757、[3]996、[4]946支持。

[3] 2310.11511v1.pdf p.6 / chunk996

> For each critique token group G (e.g., ISREL ), we denote its score at timestamp t as sG t , and we compute a segment score as follows: f(yt, d, Critique ) = p(yt|x, d, y<t)) + S( Critique ), where (3) S( Critique ) = X G∈G wGsG t for G = { ISREL , ISSUP , ISUSE }, (4) where sG t = pt(ˆr) PNG i=1 pt(ri) stands for the generation probability of the most desirable reflection token ˆr (e.g., ISREL =Relevant) for the critique token type G with N G distinct tokens (that represent different possible values for G).

[4] 2310.11511v1.pdf p.2 / chunk946

> In particular, our inference-time algorithm enables us to (1) flexibly adjust retrieval frequency for different downstream applications and (2) customize models’ behaviors to user preferences by leveraging reflection tokens through segment-level beam search using the weighted linear sum of the reflection token probabilities as segment score.

[7] 2005.11401v4.pdf p.4 / chunk757

> To estimate the probability of an hypothesis y we run an additional forward pass for each document z for which y does not appear in the beam, multiply generator probability with pη(z|x) and then sum the probabilities across beams for the marginals. We refer to this decoding procedure as “Thorough Decoding.” For longer output sequences, |Y | can become large, requiring many forward passes.

### agent: 未通过

RAG-Sequence的Thorough Decoding对未出现在某文档beam中的候选y，会额外运行一次前向传播，将该生成器概率与pη(z|x)相乘，再跨beam求和得到边缘概率[7]。Self-RAG对每个critique token组G，以最理想反思token ˆr的生成概率sG t（即pt(ˆr)除以该组NG个token概率之和）按权重wG线性求和得到S(Critique)，再与生成概率相加得到分段得分f(yt,d,Critique)[3]。

评分：covered, covered, partial

依据：RAG两个机制完整，Self-RAG归一化、加权和与生成概率相加的公式正确，但未提冻结第3点中的segment-level beam search；按主评分点记partial。此beam要求比题面直接问的score更细，另作公开的事后敏感性说明，不将其说成公式错误。

[3] 2310.11511v1.pdf p.6 / chunk996

> For each critique token group G (e.g., ISREL ), we denote its score at timestamp t as sG t , and we compute a segment score as follows: f(yt, d, Critique ) = p(yt|x, d, y<t)) + S( Critique ), where (3) S( Critique ) = X G∈G wGsG t for G = { ISREL , ISSUP , ISUSE }, (4) where sG t = pt(ˆr) PNG i=1 pt(ri) stands for the generation probability of the most desirable reflection token ˆr (e.g., ISREL =Relevant) for the critique token type G with N G distinct tokens (that represent different possible values for G).

[7] 2005.11401v4.pdf p.4 / chunk757

> To estimate the probability of an hypothesis y we run an additional forward pass for each document z for which y does not appear in the beam, multiply generator probability with pη(z|x) and then sum the probabilities across beams for the marginals. We refer to this decoding procedure as “Thorough Decoding.” For longer output sequences, |Y | can become large, requiring many forward passes.

## b10

How does Self-RAG obtain reflection-token supervision for its own critic, and how does CRAG use ChatGPT before a web search?

### rag: 通过

Self-RAG 通过提示 GPT-4 生成 reflection tokens，并将这些知识蒸馏到一个内部 critic 模型 C 中来获得监督信号，从而无需在训练期间托管 critic 模型（[2]、[5]）。具体而言，它为每组 reflection token 从原始训练数据中随机采样实例，并针对不同 token 组使用不同的指令提示，以其示例中的 Retrieve 为例（[5]）。

CRAG 在接入大规模网络搜索之前，使用 ChatGPT 将输入改写为由关键词组成的查询，以模拟搜索引擎的日常使用方式（[8]）。

评分：covered, covered

依据：GPT-4生成反思监督并蒸馏入critic、CRAG用ChatGPT改写关键词两点完整；额外分组采样有982支持。无需托管critic的附带句沿用944原文，只限该文离线标注/生成器训练语境，不扩展为critic从不训练。

[2] 2310.11511v1.pdf p.2 / chunk944

> This eliminates the need to host a critic model during training, reducing overhead. The critic model, in part, is supervised on a dataset of input, output, and corresponding reflection tokens collected by prompting a propriety LM (i.e., GPT-4; OpenAI 2023).

[5] 2310.11511v1.pdf p.5 / chunk982

> We create supervised data by prompting GPT-4 to generate reflection tokens and then distill their knowledge into an in-house C. For each group of reflection tokens, we randomly sample instances from the original training data: {Xsample, Y sample} ∼{X, Y }. As different reflection token groups have their own definitions and input, as shown in Table 1, we use different instruction prompts for them. Here, we use Retrieve as an example.

[8] 2401.15884v3.pdf p.6 / chunk1283

> Since retrieval from static and limited corpora can only return sub-optimal documents in terms of scope and diversity, large-scale web searches (Piktus et al., 2021; Komeili et al., 2022) are integrated as a strategic extension of RAG. Specifically, the inputs are rewritten into queries composed of keywords by ChatGPT to mimic the daily usage of search engine. The prompt for rewriting is shown in Appendix A.

### agent: 通过

Self-RAG通过提示GPT-4生成reflection token来收集监督数据，再将这些知识蒸馏到内部critic模型中[2][4][5]。CRAG在web search之前使用ChatGPT将输入改写为由关键词组成的查询[8]。

评分：covered, covered

依据：两种外部模型角色清晰，944/982/1113支持监督数据，1283支持关键词改写；无额外主体或条件转移。

[2] 2310.11511v1.pdf p.2 / chunk944

> This eliminates the need to host a critic model during training, reducing overhead. The critic model, in part, is supervised on a dataset of input, output, and corresponding reflection tokens collected by prompting a propriety LM (i.e., GPT-4; OpenAI 2023).

[4] 2310.11511v1.pdf p.18 / chunk1113

> Algorithm 2 SELF-RAG Training 1: Input input-output data D = {X, Y }, generator M, C θ 2: Initialize C with a pre-trained LM 3: Sample data {Xsample, Y sample} ∼{X, Y } ▷Training Critic LM (Section 3.2.1) 4: for (x, y) ∈(Xsample, Y sample) do ▷Data collections for C 5: Prompt GPT-4 to collect a reflection token r for (x, y) 6: Add {(x, y, r)} to Dcritic 7: Update C with next token prediction loss ▷Critic learning; Eq.

[5] 2310.11511v1.pdf p.5 / chunk982

> We create supervised data by prompting GPT-4 to generate reflection tokens and then distill their knowledge into an in-house C. For each group of reflection tokens, we randomly sample instances from the original training data: {Xsample, Y sample} ∼{X, Y }. As different reflection token groups have their own definitions and input, as shown in Table 1, we use different instruction prompts for them. Here, we use Retrieve as an example.

[8] 2401.15884v3.pdf p.6 / chunk1283

> Since retrieval from static and limited corpora can only return sub-optimal documents in terms of scope and diversity, large-scale web searches (Piktus et al., 2021; Komeili et al., 2022) are integrated as a strategic extension of RAG. Specifically, the inputs are rewritten into queries composed of keywords by ChatGPT to mimic the daily usage of search engine. The prompt for rewriting is shown in Appendix A.

## b11

Using only the supplied corpus, what training-token count and context-window length are specified for Mistral 7B in the Mistral 7B paper?

### rag: 通过

当前证据不足。提供的语料中没有 Mistral 7B 论文，也没有任何关于 Mistral 7B 的训练 token 数量或上下文窗口长度的信息。

评分：covered

依据：明确当前语料不含Mistral7B论文及两项规格，不猜数值；运行前PDF清单不含该主论文。

### agent: 通过

当前证据不足，无法可靠回答以下需求：
- Mistral 7B：what training-token count and context-window length are specified for Mistral 7B in the Mistral 7B paper?；缺少 Mistral 7B 论文中关于训练 token 数量和上下文窗口长度的具体数值。

评分：covered

依据：列出Mistral7B原文规格证据缺口，无训练token或窗口长度猜测；模型stop后在本地生成缺口说明，回答阶段0调用。

## b12

What exact annual index-refresh cost in US dollars and fixed index-refresh interval does the original RAG paper report?

### rag: 通过

当前证据不足：所提供的上下文只提到 RAG 使用 2016 年 12 月和 2018 年 12 月的 Wikipedia 索引进行比较[10]，并给出不同索引匹配下的准确率[6]，未报告任何以美元计的年索引刷新成本或固定的索引刷新间隔。

评分：covered

依据：明确缺少年度美元成本与固定刷新间隔，未把2016/2018索引快照差当刷新周期；额外快照/准确率描述分别由806/811支持。

[6] 2005.11401v4.pdf p.8 / chunk811

> RAG answers 70% correctly using the 2016 index for 2016 world leaders and 68% using the 2018 index for 2018 world leaders. Accuracy with mismatched indices is low (12% with the 2018 index and 2016 leaders, 4% with the 2016 index and 2018 leaders).

[10] 2005.11401v4.pdf p.7 / chunk806

> To demonstrate, we build an index using the DrQA [5] Wikipedia dump from December 2016 and compare outputs from RAG using this index to the newer index from our main results (December 2018).

### agent: 通过

当前证据不足，无法可靠回答以下需求：
- original RAG paper：What exact annual index-refresh cost in US dollars and fixed index-refresh interval does the original RAG paper report?；缺少原RAG论文报告的年度索引刷新成本（US dollars）与固定索引刷新间隔这两个具体数值。

评分：covered

依据：限定RAG搜索新增7段，再读806邻段新增4段，最终missing/stop；本地零回答调用列出两项真实缺口，没有猜年费或刷新周期。

