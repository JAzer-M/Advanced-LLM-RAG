# 固定样本原文抽查

由Codex核对，**不是独立人工准确率评测**。判分前固定取新样本前四篇论文的首题，检查原版/修正版三模式共24份完整答案，参照Gold和实际引用的已保存原文；未按分数挑选案例。选择见 [manual_sample.json](manual_sample.json)，逐项结论见 [manual_review.json](manual_review.json)。

| 题目 | 核对结果 | 说明 |
| --- | --- | --- |
| `da077b385d...`：QBM是否使用神经网络 | 六份答案的核心Yes/CNN事实均有原文支持 | 修正版RAG把引言称作结论，有附带的章节归属错误；修正版Agent仍写成一个长段，短结论提示未保证执行 |
| `e057fa254e...`：模型架构 | 原版遗漏参考答案中的logistic regression；修正版三模式补到该分类器 | 修正版Auto却把前人方法的“两套双向RNN”写成本方法；原文chunk513明确本方法为单个双向RNN，chunk515是前人方法的续句。原版Agent还用中文回答英文题 |
| `c2ce25878a...`：训练/测试数据来源 | 原版RAG/Auto答出CCPC1.0；原版Agent及修正版三模式拒答 | **修正版出现真实退步。** 含CCPC1.0的chunk1393仍在修正版候选池，却被排到第68位；前十段主要是预处理和训练格式，不能把错误拒答解释成“库里没有答案” |
| `22225ba18a...`：是否利用外部金融知识 | Gold同时标Yes和No；原版Auto给Yes并引用外部Factiva语料/word2vec，修正版Auto给No | 原文确实有外部金融语料；缺少公司/aspect建模不推出没有外部金融信息。若“knowledge”专指显式知识库，需要说明该定义，修正版No的推理没有建立它。两种结论都可能匹配一位标注者，无法据此证明论证正确 |

核对用的关键原文均保留在对应JSON的`ledger.citation_registry`及Agent运行输入中；ID只在`qasper-holdout-20261025`库内有效。例：[架构修正版Auto](runs/revised/e057fa254ea7a4335de22fd97a0f08814b88aea4/auto.json)、[数据来源修正版RAG](runs/revised/c2ce25878a17760c79031a426b6f38931cd854b2/rag.json)、[金融知识原版Auto](runs/baseline/22225ba18a6efe74b1315cc08405011d5431498e/auto.json)。

这组固定抽查说明：来源过滤不能防止同篇相关工作串用，首段F1不能代表完整解释正确，处理完成也不代表拒答正确。新样本有3题的二元参考答案互相矛盾，见 [conflicting_binary_references.json](conflicting_binary_references.json)。判分模型只看问题、参考答案和完整系统答案，未逐条读原文，不能替代这些来源核对。

另有5道有Gold的题按冻结0.5阈值近似映射不到Gold段落，实际可能仍含关键事实。比如上述架构题的分类器原文存在，数字空格、PDF断词、公式和段落边界却会使映射失配。见 [对齐诊断](diagnostics/new_unaligned_gold.json)。因此Evidence F1与Gold命中都按“近似段落映射”解释，不据对齐失败断言原文不存在。
