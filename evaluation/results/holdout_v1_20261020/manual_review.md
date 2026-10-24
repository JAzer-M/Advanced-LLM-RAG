# P1 留出集 v1：逐题人工语义核对

评审为本助手；标准在模型运行前冻结。partial/missing/wrong 都不计完整覆盖，不冒充第三方盲评。

## h01：严格通过=True；核心点=2/2

核心完整，无新增错误。

[原始答案与全部上下文](h01.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| Label smoothing epsilon is 0.1. | covered | [1] | 明确 epsilon=0.1。 |
| It hurts perplexity (the model is more unsure) but improves accuracy and BLEU. | covered | [2] | 明确 perplexity 变差，accuracy/BLEU 改善，并解释模型更不确定。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| epsilon=0.1 | [1] | supported |
| 更不确定使 perplexity 受损 | [2] | supported |
| accuracy 与 BLEU 改善 | [2] | supported |

## h02：严格通过=False；核心点=2/3

漏答粒度。Gold 1279 不在初始候选，也未进最终/生成上下文；不能归咎为单纯生成遗漏。

[原始答案与全部上下文](h02.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| A one- or two-sentence result is a strip; longer results are split into smaller units of a few sentences according to length. | partial | [1, 3] | 回答切成条带/独立信息，但缺少一两句结果保留为一条、长结果按几句切分的粒度规则。 |
| The fine-tuned retrieval evaluator scores the relevance of each strip and filters irrelevant strips. | covered | [3] | 微调检索评估器逐条带打相关性分并过滤。 |
| Relevant strips are concatenated in their original order to form internal knowledge. | covered | [3] | 相关条带按原顺序拼接为 internal knowledge。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| Correct 后执行分解、过滤、重组 | [2] | supported |
| 相关文档切成内部条带，每条假定含独立信息 | [1, 3] | supported |
| 微调检索评估器计算每条带相关性并过滤无关条带 | [3] | supported |
| 相关条带按顺序拼接形成内部知识 | [3] | supported |
| 相关文档仍可能有噪声，精炼用于提取关键条带 | [4] | supported |

## h03：严格通过=True；核心点=2/2

核心完整，额外多 GPU/图6信息也由实际引用支持。

[原始答案与全部上下文](h03.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| Documents are sorted by length in groups and encoded in batches of comparable lengths, padding only to the batch maximum. | covered | [7] | 组内按长度排序、相近长度组批、仅补到批内最大长度；B/b 示例也正确。 |
| Independent text preprocessing, especially WordPiece tokenization, is parallelized across CPU cores. | covered | [2] | 明确 WordPiece 等独立预处理跨 CPU 核心并行。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| 分组按长度排序并组相近长度的批，补到批最大长度；B=100000/b=128 为示例 | [7] | supported |
| WordPiece 等独立预处理跨 CPU 核心并行 | [2] | supported |
| 可用时多 GPU 并行编码文档批 | [7] | supported |
| 图6列有 per-batch maximum length 与 length-based bucketing 吞吐优化 | [3] | supported |

## h04：严格通过=False；核心点=2/3

Gold 266/267 均在上下文，模型还实际引用了包含翻转平均的[9]，却漏答该核心点。

[原始答案与全部上下文](h04.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| Convert the first fully connected layer to a 7x7 convolution and the final two to 1x1 convolutions, then apply the network to the whole uncropped image. | covered | [1] | 第一 FC->7x7，后两 FC->1x1，应用于整张未裁剪图像。 |
| Spatially average (sum-pool, in the paper wording) the class score map to a fixed-size vector. | covered | [9] | 对类别分数图做空间平均，保留原文 sum-pooling 说法。 |
| Average softmax class posteriors of the original and horizontally flipped images. | missing | [] | 没有回答原图与水平翻转图的 softmax 类别概率平均。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| FC 转为 7x7/1x1 卷积后应用整张未裁剪图像 | [1] | supported |
| 分数图通道等于类别数、空间分辨率随输入大小变化 | [9] | supported |
| 空间平均得到固定大小类别分数向量 | [9] | supported |

## h05：严格通过=False；核心点=2/3

主要初始化比较正确；保留 A 的前置训练步骤遗漏。VGG 原文确写 variance，不能凭常识把该回答记成标准差混淆。

[原始答案与全部上下文](h05.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| VGG first trains the shallower configuration A with random initialization, then copies its first four convolutional and last three fully connected layers into deeper networks; intermediate layers are random. | partial | [1] | 拷贝的层范围及中间层随机都正确，但未交代先随机初始化并训练浅层配置 A 这一前置步骤；按冻结的完整核心点记 partial。 |
| The copied VGG layers continue learning without a reduced learning rate. | covered | [1] | 明确预初始化层不降低学习率并继续训练。 |
| DCNN initializes weights in each layer from a zero-mean Gaussian with standard deviation 0.01. | covered | [2] | DCNN 每层零均值 Gaussian、标准差0.01。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| VGG 拷贝 A 的前四卷积层和后三全连接层，中间随机；拷贝层不降低学习率且继续学习 | [1] | supported |
| VGG 随机权重零均值、variance 10^-2，bias=0 | [7] | supported |
| DCNN 每层零均值 Gaussian、标准差0.01 | [2] | supported |
| DCNN 第二/四/五卷积层与全连接隐藏层 bias=1，其余=0 | [2, 8] | supported |

## h06：严格通过=True；核心点=3/3

跨篇综合完整。

[原始答案与全部上下文](h06.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| DCNN places roughly half the kernels/neurons on each of two GPUs; communication is restricted to selected layers (layer 3 sees both GPUs, layer 4 only its own). | covered | [3, 5] | DCNN 两 GPU 各放一半 kernel/神经元，只在部分层跨卡通信，第三/四层例子正确。 |
| VGG uses data parallelism by splitting each image batch into GPU batches. | covered | [1] | VGG 拆分图像 batch 做数据并行。 |
| VGG synchronously averages GPU gradients to obtain the full-batch gradient, equivalent to the single-GPU computation. | covered | [1] | 同步平均各 GPU 梯度，得到整批梯度，与单 GPU 对应计算一致。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| DCNN 两 GPU 各一半 kernel/神经元，仅特定层通信；第三层跨卡、第四层同卡 | [3] | supported |
| DCNN 图2上下两个层部件分属两 GPU | [5] | supported |
| VGG 拆 batch 到各 GPU 并行，平均梯度为完整 batch 梯度 | [1] | supported |
| VGG 梯度计算同步，结果与单 GPU 相同 | [1] | supported |

## h07：严格通过=True；核心点=3/3

核心与比较完整。开头“仅能部分回答”和结尾对额外预热的保留措辞多余，但未拒绝或遗漏题目所需答案；不按关键词将其误计为实质过度拒答。

[原始答案与全部上下文](h07.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| Transformer increases the learning rate linearly during 4000 warmup steps. | covered | [1] | 线性 warmup 4000 步。 |
| After warmup Transformer decreases learning rate proportionally to inverse square root of step number. | covered | [1] | 之后按 step_num 的平方根倒数下降，以训练步数控制。 |
| DCNN manually divides the learning rate by 10 when validation error stops improving (starting at 0.01, reduced three times). | covered | [8] | DCNN 验证误差停滞时手动除10，初值0.01、下降三次均给出。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| Transformer 前4000步线性增加，之后按步数平方根倒数下降 | [1] | supported |
| Transformer 调度由训练步数而非验证误差触发 | [1] | supported |
| DCNN 各层同学习率，验证误差停滞时手动除10，初值0.01、下调三次 | [8] | supported |
| 两篇降学习率的控制依据不同 | [1, 8] | supported |

## h08：严格通过=False；核心点=2/3

缺少最终选择规则；Gold 465 未进上下文。末段强调缺少显式跨篇比较句，属于不必要的比较保留措辞；前文已实际说明输出约束差异，因此不把它算作完全拒绝比较。

[原始答案与全部上下文](h08.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| DPR uses an extractive reader and restricts answers to spans in retrieved passages. | covered | [6] | DPR reader 从检索段落抽取答案片段，明确输出受段落 span 约束。 |
| The reader scores passages and spans, then chooses the best span from the passage with the highest passage-selection score. | partial | [6] | 给出 passage-selection/span 两种评分，但缺少从 passage-selection 最高的段落选择其中最佳 span 的最终决策规则。 |
| RAG supports free-form abstractive answer generation beyond copying a passage span. | covered | [2] | RAG 可以自由形式抽象生成，不限于拷贝片段，文中明确说能力不同。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| DPR 对至多100段给段落选择分及抽取 span 的分数 | [6] | supported |
| DPR 答案为检索段落中的 span | [6] | supported |
| RAG 支持超越抽取的自由形式抽象生成 | [2] | supported |

## h09：严格通过=False；核心点=1/3

高层区别正确且替代证据549/667支持全库检索，但冻结标准中的 lambda=1.1 与 FAISS 两阶段细节均遗漏。相应 Gold 438/627/628 未进入上下文。

[原始答案与全部上下文](h09.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| DPR takes the union of top-2000 BM25 and top-2000 DPR passages and reranks by BM25(q,p) + lambda*sim(q,p), with lambda 1.1 selected on development accuracy. | partial | [1] | top-2000各路、并集、线性公式正确，但未给出开发集选择 lambda=1.1 的细节。 |
| ColBERT re-ranking scores candidates returned by another retriever, typically a term-based model. | covered | [8] | 重排另一检索器（通常基于词项）返回的候选。 |
| ColBERT can alternatively retrieve directly from the full collection using a FAISS embedding index and approximate filtering followed by refinement. | partial | [9, 10] | 说明全库向量索引直接检索，但没有 FAISS 及近似过滤->精炼两个阶段。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| DPR 合并 BM25/DPR 各自 top-2000，以 BM25+lambda*sim 重排并集 | [1] | supported |
| ColBERT 可重排另一词项检索器候选或直接全库检索 | [8] | supported |
| ColBERT 全库模式用向量相似度索引 | [9] | supported |
| 文中 MS MARCO 全库设置从8.8M文档直接取每题 top-1000 | [10] | supported |

## h10：严格通过=False；核心点=0/2

可答题部分拒答源于上下文缺少 RAG EM 原文，不是证据已齐的实质过度拒答。分解额外把 PopQA 绑定到原始 RAG（原题只把 PopQA/TriviaQA 指向 Self-RAG）；该漂移已观察到，但未做消融，不能宣称已证明因果。Gold 765 初始漏召、补查候选已有，最终仍未入选。

[原始答案与全部上下文](h10.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| RAG reports Exact Match scores for its open-domain QA evaluation. | missing | [] | 未得到 RAG 的 Exact Match 判据；实际上下文没有 Gold 765。 |
| Self-RAG judges whether a gold answer is included in the generated text instead of strictly requiring exact matching; the raw scores therefore have different criteria. | partial | [2] | Self-RAG 的 gold-answer inclusion 与不要求 strict exact match 已答对，但完整核心点还要求说明两篇得分标准不同；答案明确表示无法比较，因此该复合点按冻结规则记 partial。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| Self-RAG 用 gold answer 是否包含在生成中，而非 strict exact matching | [2] | supported |
| 所引 RAG [5] 只描述 TriviaQA 答案候选过滤 | [5] | supported |
| 所引 RAG [9] 描述负对数似然训练及抽取式 QA 对比，未给出评测判据 | [9] | supported |

## h11：严格通过=True；核心点=1/1

正确拒答；八篇 PDF 清单与全文 Mamba 扫描在运行前已核对，未依赖检索失败来定义不可答。

[原始答案与全部上下文](h11.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| State that the Mamba paper/model specification is absent from this corpus and the two requested values cannot be established; do not guess numbers. | covered | [] | 明确八篇资料不含 Mamba/所需训练数据量与隐藏状态维度，未猜数字。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| 当前八篇库中没有 Mamba 论文与所需模型规格，无法据此回答 | [] | supported |

## h12：严格通过=False；核心点=1/1

拒答内容正确，附带的27.0%也由真实上下文285支持；保留追加数值缺引用的问题，严格引用标准下不通过，不把它误报成数值幻觉。

[原始答案与全部上下文](h12.md)

| 预定核心点 | 判断 | 引用 | 理由 |
| --- | --- | --- | --- |
| Explain that the corpus does not report the requested controlled ImageNet experiment for the original Transformer; do not substitute a BLEU score, a VGG result, or a later vision Transformer result. | covered | [] | 拒绝推断原始 Transformer 的同协议 ImageNet 准确率，没有拿 BLEU 或 VGG 数字替代所问结果。 |

| 实际重要断言 | 引用 | 语义支撑 |
| --- | --- | --- |
| 所给上下文没有所问原始 Transformer 同协议 ImageNet 结果，无法推断 | [] | supported |
| VGG D 在256尺度的 top-1 验证误差为27.0% | [] | supported |
| Transformer 翻译结果与 VGG 图像分类结果属于不同任务/数据集 | [] | supported |

