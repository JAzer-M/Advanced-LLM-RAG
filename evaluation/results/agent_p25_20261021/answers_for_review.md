# P2.5 实际答案与冻结评分点

## b01 / single_document

Which optimizer and beta1, beta2, and epsilon values does the Transformer in Attention Is All You Need use?

冻结评分点：

- The optimizer is Adam.
- beta1=0.9, beta2=0.98 and epsilon=10^-9.

固定RAG：

Transformer 使用的是 Adam 优化器，β1 = 0.9、β2 = 0.98、ϵ = 10⁻⁹ [7]。

Agent：

《Attention Is All You Need》中的Transformer使用Adam优化器，β1 = 0.9，β2 = 0.98，ϵ = 10−9 [7]。

Agent阶段：completed / review_passed；停止：answer_ready；错误：None

## b02 / single_document

How does DCNN initialize neuron biases in different layers, and why does it use positive biases in selected layers?

冻结评分点：

- Biases are 1 in convolutional layers 2, 4, 5 and fully connected hidden layers.
- Biases in the remaining layers are 0.
- Positive initial biases accelerate early learning by supplying ReLUs with positive inputs.

固定RAG：

DCNN 将第二、第四、第五卷积层以及全连接隐藏层的神经元偏置初始化为常数 1 [1]；其余层的神经元偏置初始化为常数 0 [2]。使用正偏置的目的是为 ReLU 提供正输入，从而加速学习初期阶段 [1]。

Agent：

(无答案)

Agent阶段：failed / None；停止：None；错误：ValueError: Requirement question_quote must name its own subject and show its scope.

## b03 / single_document

In VGG multi-scale training, how is the training scale S sampled, what crop size is used, and how is the multi-scale model initialized?

冻结评分点：

- Each image samples S from [256,512]; S is the shortest side of the isotropically rescaled image.
- The input crop remains 224x224.
- All layers of a same-configuration single-scale model pretrained at S=384 are fine-tuned.

固定RAG：

在多尺度训练中，每张训练图像会通过对 S 在一定范围 [Smin, Smax] 内随机采样进行单独缩放，文中使用的范围是 Smin = 256、Smax = 512（[1]）。裁剪尺寸固定为 224 × 224（[2]）。多尺度模型主要是通过微调（fine-tuning）一个相同配置的单尺度模型的所有层来训练的，该单尺度模型以固定 S = 384 预训练（[4]）。

Agent：

(无答案)

Agent阶段：failed / None；停止：None；错误：ValueError: Requirement question_quote is not in the user question.

## b04 / single_document

After the token embeddings are projected in ColBERT, how are they normalized, and what equivalence and value range does this give to their dot products?

冻结评分点：

- Each output embedding is normalized to L2 norm 1.
- The dot product of two normalized embeddings equals cosine similarity and lies in [-1,1].

固定RAG：

在 ColBERT 中，输出嵌入会被归一化，使每个嵌入的 L2 范数等于 1 [1]。这样任意两个嵌入的点积就等价于它们的余弦相似度，取值落在 [−1, 1] 区间内 [1]。

Agent：

ColBERT 对投影后的 token 嵌入进行归一化，使每个嵌入的 L2 范数等于 1 [1][2]。由此，任意两个嵌入的点积等价于其余弦相似度，取值范围为 [−1, 1] [1]。

Agent阶段：completed / review_passed；停止：answer_ready；错误：None

## b05 / cross_document

Which checkpoints are averaged for Transformer base and big models, and how does this differ from the way VGG combines multiple model predictions?

冻结评分点：

- Transformer base uses one model formed by averaging its last 5 checkpoints; big averages its last 20 checkpoints.
- VGG averages softmax class posteriors from several models.
- The distinction is averaging model checkpoints versus averaging model output probabilities.

固定RAG：

Transformer base 模型平均的是最后 5 个 checkpoint（这些 checkpoint 以 10 分钟间隔写入）；big 模型平均的是最后 20 个 checkpoint [1]。VGG 则是通过平均多个模型的 softmax 类别后验概率来组合输出，从而利用模型间的互补性提升性能 [2]。

Agent：

Transformer base模型平均最后5个checkpoint（以10分钟间隔写入），big模型平均最后20个checkpoint[1]。VGG则通过平均多个模型的soft-max类别后验概率来组合预测[2]，这与Transformer按时间顺序选取末尾checkpoint做权重的平均方式不同。

Agent阶段：completed / review_passed；停止：answer_ready；错误：None

## b06 / cross_document

What do DCNN and VGG report about the usefulness of local response normalization, and what computational costs does VGG mention?

冻结评分点：

- DCNN reports that response normalization improves generalization and reduces top-1/top-5 errors (1.4/1.2 percentage points if numbers are supplied).
- VGG finds no performance improvement and generally omits LRN, with the A-LRN comparison as an exception.
- VGG says LRN increases memory consumption and computation time.

固定RAG：

关于局部响应归一化（Local Response Normalization, LRN）：

- **DCNN**：报告称该归一化方案有助于泛化，具体使 top-1 和 top-5 错误率分别降低 1.4% 和 1.2%（[6]）。
- **VGG**：总体上认为 LRN 并不能提升 ILSVRC 数据集上的性能，反而会增加内存消耗和计算时间（[3]）；在单尺度评估中，使用 LRN 的 A-LRN 网络相比不含归一化层的模型 A 没有提升（[10]）。需注意，VGG 在架构上"除一个网络外"均不含 LRN（[3]）。

关于 VGG 提到的计算成本：

- VGG 指出 LRN 会增加内存消耗和计算时间（[3]）。除此之外，所给证据未提及 VGG 的其他计算成本细节。

Agent：

(无答案)

Agent阶段：failed / None；停止：None；错误：ValueError: A requirement scope cannot include another declared subject; extract separate clauses.

## b07 / cross_document

What does DPR's top-k retrieval accuracy count, and which metrics does Self-RAG use for correctness, fluency, and citations on ASQA?

冻结评分点：

- DPR counts the fraction of questions whose top-k retrieved passages contain an answer span.
- Self-RAG uses str-em for ASQA correctness.
- Self-RAG uses MAUVE for ASQA fluency.
- Self-RAG uses citation precision and recall for ASQA citations.

固定RAG：

DPR 的 top-k 检索准确率按“top 20/100 检索到的段落中包含答案的百分比”来衡量[8]。

Self-RAG 在 ASQA 上使用的指标为：正确性用 str-em（官方 correctness 指标），流畅性用基于 MAUVE 的指标，引用方面用 citation precision 和 recall[1]。

Agent：

DPR的top-k检索准确率计为top 20/100检索到的段落中包含答案的百分比[8]。Self-RAG在ASQA上使用str-em衡量正确性、MAUVE衡量流畅度、citation precision和recall衡量引用[1]。

Agent阶段：completed / review_passed；停止：answer_ready；错误：None

## b08 / cross_document

What hardware and approximate training duration do the Transformer base model and DCNN report for their own experiments?

冻结评分点：

- Transformer base trains on 8 NVIDIA P100 GPUs for 100000 steps or about 12 hours.
- DCNN trains on 2 NVIDIA GTX 580 GPUs with 3GB each for about 5-6 days.

固定RAG：

Transformer base model：使用 8 块 P100 GPU，训练约 12 小时（100,000 步）[8][9]。DCNN：使用两块 GTX 580 3GB GPU，训练约 5–6 天（约 90 个训练周期）[2][3]。

Agent：

Transformer base模型使用8块P100 GPU训练，约12小时（100,000步）[8][9]。DCNN在2块GTX 580 3GB GPU上训练约5–6天，约90个训练周期[2][3]。

Agent阶段：completed / review_passed；停止：answer_ready；错误：None

## b09 / cross_document

How does RAG-Sequence's Thorough Decoding score a candidate absent from a document's beam, and how does Self-RAG use critique-token probabilities to score output segments?

冻结评分点：

- RAG-Sequence runs an extra forward pass for each document whose beam did not contain the candidate.
- It multiplies generator probability by retriever probability and sums across documents for the marginal.
- Self-RAG uses segment-level beam search and a weighted linear sum of normalized critique-token probabilities to update segment scores.

固定RAG：

关于 RAG-Sequence 的 Thorough Decoding：对某个候选假设 y，若它未出现在某文档 z 的 beam 中，则对该文档额外做一次前向计算，将生成器概率与 pη(z|x) 相乘，再跨各 beam 求和得到边际概率（[7]）。

关于 Self-RAG 的评审 token 概率评分：对每个评审 token 组 G（如 ISREL），以最理想反思 token 的生成概率在该组所有 token 概率中的占比作为该组得分 sG t（[3]）；段得分由生成概率 p(yt|x, d, y<t) 加上各评审组得分的加权线性和 S(Critique)=Σ_{G∈G} wG·sG t（G={ISREL, ISSUP, ISUSE}）构成（[3]）。该加权线性和的段得分用于段级 beam search，从而按用户偏好定制模型行为（[4]）。

Agent：

RAG-Sequence的Thorough Decoding对未出现在某文档beam中的候选y，会额外运行一次前向传播，将该生成器概率与pη(z|x)相乘，再跨beam求和得到边缘概率[7]。Self-RAG对每个critique token组G，以最理想反思token ˆr的生成概率sG t（即pt(ˆr)除以该组NG个token概率之和）按权重wG线性求和得到S(Critique)，再与生成概率相加得到分段得分f(yt,d,Critique)[3]。

Agent阶段：completed / review_passed；停止：answer_ready；错误：None

## b10 / cross_document

How does Self-RAG obtain reflection-token supervision for its own critic, and how does CRAG use ChatGPT before a web search?

冻结评分点：

- Self-RAG prompts GPT-4 for reflection-token labels and distills that supervision into its own critic.
- CRAG uses ChatGPT to rewrite the input question into a keyword-based search query.

固定RAG：

Self-RAG 通过提示 GPT-4 生成 reflection tokens，并将这些知识蒸馏到一个内部 critic 模型 C 中来获得监督信号，从而无需在训练期间托管 critic 模型（[2]、[5]）。具体而言，它为每组 reflection token 从原始训练数据中随机采样实例，并针对不同 token 组使用不同的指令提示，以其示例中的 Retrieve 为例（[5]）。

CRAG 在接入大规模网络搜索之前，使用 ChatGPT 将输入改写为由关键词组成的查询，以模拟搜索引擎的日常使用方式（[8]）。

Agent：

Self-RAG通过提示GPT-4生成reflection token来收集监督数据，再将这些知识蒸馏到内部critic模型中[2][4][5]。CRAG在web search之前使用ChatGPT将输入改写为由关键词组成的查询[8]。

Agent阶段：completed / review_passed；停止：answer_ready；错误：None

## b11 / unanswerable

Using only the supplied corpus, what training-token count and context-window length are specified for Mistral 7B in the Mistral 7B paper?

冻结评分点：

- The Mistral 7B primary paper is absent from the eight-paper corpus; the requested specifications cannot be established and must not be guessed.

固定RAG：

当前证据不足。提供的语料中没有 Mistral 7B 论文，也没有任何关于 Mistral 7B 的训练 token 数量或上下文窗口长度的信息。

Agent：

当前证据不足，无法可靠回答以下需求：
- Mistral 7B：what training-token count and context-window length are specified for Mistral 7B in the Mistral 7B paper?；缺少 Mistral 7B 论文中关于训练 token 数量和上下文窗口长度的具体数值。

Agent阶段：completed / insufficient_evidence；停止：model_stop；错误：None

## b12 / unanswerable

What exact annual index-refresh cost in US dollars and fixed index-refresh interval does the original RAG paper report?

冻结评分点：

- The RAG paper does not specify an annual USD cost or a fixed refresh interval; explain the missing measurements without inventing either value.

固定RAG：

当前证据不足：所提供的上下文只提到 RAG 使用 2016 年 12 月和 2018 年 12 月的 Wikipedia 索引进行比较[10]，并给出不同索引匹配下的准确率[6]，未报告任何以美元计的年索引刷新成本或固定的索引刷新间隔。

Agent：

当前证据不足，无法可靠回答以下需求：
- original RAG paper：What exact annual index-refresh cost in US dollars and fixed index-refresh interval does the original RAG paper report?；缺少原RAG论文报告的年度索引刷新成本（US dollars）与固定索引刷新间隔这两个具体数值。

Agent阶段：completed / insufficient_evidence；停止：model_stop；错误：None

