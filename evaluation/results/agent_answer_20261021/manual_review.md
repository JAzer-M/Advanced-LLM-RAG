# P2.4 已知样例逐条原文核对

日期：2026-10-21。核对者：本次代码代理。依据为当前同版本原文，不是独立人员盲评，也没有把Gold或旧答案传给模型。

## h10：比较正确性判据

原题：For short-answer open-domain QA, how does the correctness criterion reported by RAG differ from the criterion used by Self-RAG for PopQA and TriviaQA?

[最终答案](network_followup/h10/answer.md)：

> RAG在开放域问答任务上报告Exact Match (EM)分数作为正确性准则[26]。Self-RAG对PopQA和TriviaQA则依据金标准答案是否包含在模型生成内容中来评测，而不严格要求精确匹配[2]。因此二者差异在于：RAG采用精确匹配，Self-RAG采用答案包含式判定[2][26]。

编号属于本次26段原文的顺序，出处如下；完整正文在[实际输入](network_followup/h10/inputs.json)中，`passages`同时保存citation、source、page、chunk_id和text。

| 需求或断言 | 本次引用 | 原文身份 | 核对结果 |
| --- | --- | --- | --- |
| RAG报告EM | [26] | 2005.11401v4.pdf，p.4，chunk765 | 原文含“report Exact Match (EM) scores”，支持 |
| Self-RAG对PopQA/TriviaQA用包含判据 | [2] | 2310.11511v1.pdf，p.7，chunk1003 | 同段分别点名两数据集，并说明检查gold answers是否included in model generations、而非strictly requiring exact matching，支持 |
| 两者判据差异 | [2][26] | 上述两段 | 可由两项事实综合，不要求存在跨论文比较原句，支持 |

RAG的开放域QA任务语境可在保留的chunk763/764看到；Self-RAG的短问答任务介绍在chunk1002，[2]本身也点名PopQA和TriviaQA，因此本题不必机械补引1002。最终表述没有把Self-RAG的数据集条件移给RAG，没有声称知道EM的归一化、标点处理或额外数值，也没有引入性能优劣结论。本次题目所要求的核心事实与比较已覆盖。

## 首次复核为何被拒绝

首次复核给r1的answer_quote为：

> RAG在开放域问答上报告Exact Match (EM)分数作为正确性准则[26]。...RAG采用精确匹配

它不是草稿中的连续原句。复核还列出[16]，但草稿没有[16]；不能把复核自己补充的证据算作草稿已引用。原始响应见[实际调用](network_followup/h10/actual_chat_calls.json)第2条。程序在第一项不合格处拒绝，给一次修订后重新复核；第二次复核的答句及原文引句均匹配，编号2/26合法。修订前后事实结论基本一致，不能用这一次实验声称“多调用一定提高答案质量”。

## h11：缺少目标论文

保存的原题询问Mamba论文中的训练数据规模和隐藏状态维度。当前八篇目录不含Mamba；保存状态为missing，无支持引句。[本次边界输出](run/h11/answer.md)明确说明缺少该论文与具体设定，没有猜测数值；[调用账本](run/h11/actual_chat_calls.json)为空列表。该分支未请求模型。

## 未验证范围

本轮只对已知h10/h11做上述核对。部分证据、冲突、遗漏、错误数值、错误主体、条件错误、引用越界、复核伪造引句、网络失败/截断、预算与中断续接均有离线控制测试；这些测试不等于真实模型对所有情况都能正确判断。新留出泛化和固定RAG对照仍待P2.5。
