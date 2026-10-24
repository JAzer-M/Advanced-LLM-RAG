# QASPER 52题三模式评测与执行记录

2026-10-24（Asia/Shanghai）。代码基线 `c324ef8`，独立知识库 `qasper-test50-20261024`：15篇论文、52题、1612个片段。三模式各52条结果及156条模型判分均已完成；未修改生产问答代码、原评测脚本或旧实验分数。

**本轮 Auto 的 Answer F1 最高，生成 token 是 RAG 的3.51倍；Agent 的证据 F1 更高，但回答 F1 与 RAG 接近，且有15条失败。** 这是小样本、模型轮换、修订输入后的外部题集实测，不能宣称单一模型下的普遍收益或完全盲评。模型判分只作补充。

## 1. 本轮实际测了什么

题目和参考答案来自QASPER v0.3测试集；按原固定种子20261024整篇纳入至至少50题，实际15篇52题。原数据包、15份PDF、索引和片段哈希均核对通过。论文为arXiv当前PDF，可能与数据集使用的全文版本不同；不直接与官方论文或榜单比较。

原脚本把“What metric is considered?”等问题直接交给15篇混合库，没有告诉系统问题所属论文。已保存的首题RAG上下文不含目标1703.10152，回答列举了其他论文的指标，因此中断这一轮。例证见[input_binding_failure_examples.json](input_binding_failure_examples.json)。按原协议“发现问题另起一轮、保留旧结果”，在新目录运行前冻结[论文绑定输入协议](paper_bound_deepseek_v41_flash/protocol.md)。

新轮仅在原问题前加固定的公开元数据：`For the paper "{paper_title}" (arXiv: {paper_id}), answer this question: {original_question}`。52个题号、顺序、原始问题、参考答案、PDF、库和评分规则均不变，参考答案不进入作答请求。实际输入及原问题分别保存在[本轮样本](paper_bound_deepseek_v41_flash/frozen_sample.json)的`question`、`original_question`字段。首题上下文已正确绑定为目标论文的10段原文。

本系统按题名提示在15篇PDF混合库检索，并非直接给定目标论文全文。输入修订发生前已有6题的三模式输出被观察，因此不称为完全未观察过题目的盲评；没有基于结果调整生产检索、提示词、工具或预算。

## 2. 52题主结果（失败保留在分母）

F1按0—100显示；Evidence F1依赖冻结的近似段落对齐，不等同引用事实正确率。检索命中率只对有标注证据的49题计算。

| 模式 | Answer F1 | Evidence F1（近似） | 检索至少命中一段Gold | completed / degraded / failed | 模型判分 correct / partial / incorrect |
| --- | ---: | ---: | ---: | --- | --- |
| RAG | 14.83 | 28.24 | 20/49（40.82%） | 52 / 0 / 0 | 25 / 11 / 16 |
| Agent | 14.81 | 41.22 | 27/49（55.10%） | 37 / 0 / 15 | 25 / 6 / 21 |
| Auto | 21.39 | 33.00 | 25/49（51.02%） | 45 / 5 / 2 | 28 / 8 / 16 |

原始[summary.json](paper_bound_deepseek_v41_flash/summary.json)、[逐题评分](paper_bound_deepseek_v41_flash/scores/per_question.json)、[补充汇总](paper_bound_deepseek_v41_flash/extended_summary.json)可复核。`completed`并非正确性标签，例如RAG的52条均完成，但判分模型只将25条判为correct。判分与作答为同一请求模型，有同源偏差；未另做独立人工准确率评分。

三个模式的Answer F1、Evidence F1均与压缩包内官方评测脚本一致，最大浮点差约`5.6e-17`，无缺失预测。见[官方输出](paper_bound_deepseek_v41_flash/scores/official_evaluator.json)、[交叉核对](paper_bound_deepseek_v41_flash/official_crosscheck.json)。这证明评分实现和输入转换后的官方复算一致，不证明拒答转换或证据对齐在语义上完全正确。

### 按答案类型

以下采用官方脚本的分型：按取得最大Answer F1的参考答案类型归组；不能与原脚本`summary.json`按“该题是否含此类标注”的多标签均值混用。

| 模式 | 抽取式F1 | 概括式F1 | 是非题F1 | 不可答F1 |
| --- | ---: | ---: | ---: | ---: |
| RAG | 18.51 | 10.09 | 1.50 | 50.00 |
| Agent | 17.78 | 12.71 | 2.72 | 33.33 |
| Auto | 22.81 | 12.83 | 2.24 | 100.00 |

这些分型的分母受多标注类型及最大值归组影响，不可答F1也不是多数标注不可答题的拒答准确率。样本中多数标注不可答仅2题，不能据此推广拒答能力。

## 3. 反代故障与模型分组

用户事先授权：反代模型限额时切换可用模型。原GLM第二条运行遇HTTP429；正式轮遇3次HTTP503。均先保存当前结果再暂停，不自动重试或覆盖失败。503的具体服务端原因未能从现有客户端进一步区分，不将它们当作已证实的单模型额度耗尽。

正式轮的切换点均在一题三模式记录齐全之后；52题逐题模型一致，未在同一题内混用模型。全部判分也逐条匹配作答请求模型，156/156无不匹配。总体表是模型轮换条件下的配对结果，不能称单模型52题实验。

| 请求模型 | 题数 | RAG Answer F1 | Agent Answer F1 | Auto Answer F1 |
| --- | ---: | ---: | ---: | ---: |
| cn:deepseek-v4.1-flash | 39 | 15.62 | 16.67 | 23.64 |
| cn:deepseek-v4-flash | 10 | 12.91 | 7.91 | 13.52 |
| cn:glm-5.3-flash | 3 | 11.00 | 13.56 | 18.26 |

模型分组与题目难度没有随机平衡，不能用本表比较不同模型的能力。请求ID、服务报告ID、调用时间、usage及失败见每条结果的`execution`、`eval_api_calls`及[sessions](paper_bound_deepseek_v41_flash/sessions/)。服务报告ID不独立证明上游权重。切换过程见[01](model_switch_01.json)、[02](model_switch_02.json)、[03](model_switch_03.json)、[04](model_switch_04.json)。

3次503均发生于Auto路径；执行顺序固定为RAG→Agent→Auto，不能据此断言Auto本身更容易触发反代故障。主表保留全部52题和失败。仅作故障敏感性诊断，事后对三模式共同去掉这3道故障题，余49题的Answer F1为RAG15.34、Agent14.88、Auto22.62；这一子集不替代主成绩，也不是预注册的新总体成绩。

## 4. 拒答、低F1与真实缺陷

按冻结的拒答识别规则：RAG/Agent/Auto在2道多数标注不可答题中分别拒答1/1/2题；在50道多数标注可答题中分别有9/5/8条被规则标为拒答。这些是启发式标签，不能当作精确人工拒答统计。

Codex阅读了全部26条`prediction_kind=declined`输出，并抽查9条低F1但被模型判为correct的回答，核对参考答案与代表性引用原文，见[核对记录](manual_review.md)。发现：

- 正确Yes/No后跟长解释，会被词级F1明显压低；语义表达否定而没有独立“No”词时甚至F1为0。
- 一条英文ASL问题得到中文Agent答案，核心内容与参考及引用匹配，但语言未遵循输入，词级F1为0。本轮没有因此宣称所有模型的语言跟随均已可靠。
- `50c1bf8b92…/rag`已经给出accuracy，但因句首否定“通用指标”，被误转为Unanswerable；判分模型也将它识别为部分作答而非拒答。
- 首题RAG的中文“当前证据不足”没有被拒答正则覆盖，是漏标；另有“缺少best model细节但给出95%”的混合型回答，不能简单等同纯拒答。
- 个别题有相互冲突的人工参考，官方取任一参考最大值可能让少数标注支持的拒答得到满分。例如手工特征题多数参考列出特征，另一个参考为Unanswerable。

冻结分数、判分和后处理均保留，没有按抽查结果改分或重跑。拒答启发式及语言不一致限制了Answer F1和拒答数量的解释。模型判分为补充信号，9条抽查也不是全体人工准确率估计。

Agent的15条失败包括：5次决策修正额度用尽、5次最终复核失败、3次需求引文范围校验失败、2次原文引文不匹配；均保留实际成本。Auto有2条失败、5条降级，其中3次网关503分布为2次失败和1次有草稿的降级；其他规划/引文校验失败也保留。详见[逐条非正常结果](paper_bound_deepseek_v41_flash/extended_summary.json)。

## 5. 实际请求、token与耗时

| 模式 | 模型请求 | 生成token合计 | 每题平均token | 每条平均秒数 |
| --- | ---: | ---: | ---: | ---: |
| RAG | 104 | 161,057 | 3,097.25 | 11.49 |
| Agent | 331 | 943,372 | 18,141.77 | 26.08 |
| Auto | 228 | 565,288 | 10,870.92 | 20.06 |
| 正式生成合计 | 663 | 1,669,717 | — | — |

平均耗时包含本地检索与模型等待；顺序固定、CPU检索模型缓存复用，重启及服务波动不同，不是P95或独立速度收益实验。Agent生成token为RAG的5.86倍，Auto为3.51倍。

| 执行部分 | 已留档模型请求 | 已报告token |
| --- | ---: | ---: |
| 原GLM尝试（含1次429） | 3 | 3,022 |
| 未绑定论文的DeepSeek旧轮（18条已保存） | 63 | 116,041 |
| 正式轮156条生成 | 663 | 1,669,717 |
| 正式轮156条判分 | 156 | 70,379 |
| 已留档合计 | 885 | 1,859,159 |

以上有4次HTTP失败未返回usage；旧轮在下一条RAG本地重排时中断，至少已完成1次分解请求，其用量未落盘。因此885是已留档请求数，实际模型请求至少886次，1,859,159是已报告token之和，不是完整账单总量。另有1次成功的`/models`读取，不计为生成请求。正式轮加判分为819次请求、1,740,096 token；不能只报正式轮而隐去中断成本。未获得计费单价，不推算货币费用。早先约1.2M token为估算，已被本轮实测修正。

## 6. 交付、验证与剩余边界

- 原[protocol.md](protocol.md)、原[frozen_sample.json](frozen_sample.json)、`evaluation/qasper_eval.py`逐字节保留；新轮输入在独立目录冻结。
- `run_supervised.py`只为原脚本增加逐次模型/usage留档、反代故障后暂停和判分模型匹配。执行层首次离线检查暴露临时目录相对路径错误，失败摘要保留；修复后及新增判分匹配检查共3项通过。未改变生产问答、检索、评分或判分提示词。
- 156条作答、156条判分和官方复算完整；知识库配对文件、源PDF、样本、代码和两个原有知识库指针核对见[verification.json](verification.json)。本轮没有重跑与改动无关的旧345项后端/42项网页测试，不将旧通过数说成本次新测。
- 本次文件修改前的README、PROGRESS、PROJECT_METRICS和NEXT_STEPS已保存在[source_before](source_before/)。模型配置仅保存在本机私有文件，当前选择为`cn:deepseek-v4.1-flash`。
- 如要作更强结论，应另行冻结单一模型、更多新题和可靠的拒答/语言处理口径。当前不重跑这些已观察题来修饰成绩。Windows v0.2.0发布、可选Mac重新打包、简历与面试材料仍是后续工作。

离线复算不调用模型：在项目根目录运行 `QASPER_OUTPUT_DIR=evaluation/results/qasper_20261024/paper_bound_deepseek_v41_flash .venv/bin/python evaluation/results/qasper_20261024/run_supervised.py score`，再运行同一命令的`report`步骤及 `.venv/bin/python evaluation/results/qasper_20261024/analyze_results.py`。PDF、数据缓存和知识库只在本机保留，其他机器需要配对资产才能复算证据对齐。
