# 项目量化指标与证据入口

更新：2026-10-23（Asia/Shanghai）。最新n04/Auto、n06/Agent真实开发复验完整任务0/2：均通过标题核对后遇arXiv搜索429，1降级/1失败，未读PDF或进入最终回答复核。9模型POST/12278 token、2GET。书目修复的298项离线通过版本保持；原六题4/6、5/6及Auto 1/2不改，没有新的独立质量分数，整体收益未证明。

最终项目的量化数据应同时交代版本、题集、分母、比较条件、质量与成本。每次修复保留旧结果，新题转为开发回归后另建留出，不能把调试后的成绩继续称为新题泛化。

## 最新P3两条真实开发回归与收尾

先冻结源码、问题、公开模型选项及30模型请求/4公网GET预算，实际main各跑一次n04/Auto开启arXiv、n06/Agent开启arXiv；只复用真实CPU资源，模型/HTTP均真实，Gold与旧答案不进生产输入。两组初检上下文均与旧对应路径逐字节相同，后续模型主体有差异。

| 路径 | 完整任务 | 程序状态 | 模型POST | 输入/输出/总token | 搜索GET |
| --- | --- | --- | ---: | --- | --- |
| n04 / Auto-on | 未通过，必答0/3 | degraded，保留证据不足草稿 | 5 | 6860/546/7406 | 1，HTTP429 |
| n06 / Agent-on | 未通过，无最终拒答 | failed，无答案 | 4 | 4562/310/4872 | 1，HTTP429 |

两条计划完整任务0/2，属于已知开发用例，不是独立新题成绩。合计9模型POST、12278 token（输入11422/输出856），全部stop，模型HTTP失败/调用失败/usage缺失/自动重试0；另2搜索GET均429，PDF/Gold GET和最终回答复核调用0。没有读到外部原文，相关PDF核验标为不适用；不能用空登记表或日志missing状态算通过。

n04主体original FlashAttention paper实际通过修饰词分离，n06本次主体FlashAttention没有修饰词；原精确失败组合仍以此前离线回归为准。当前实际阻塞是外部来源可用性和工具失败后的交付，429具体原因未确认。本轮未改生产/测试，不重复298项整套测试，未重试或改写历史成绩。耗时34.817/15.212秒为顺序单次CPU预加载后值，非P95；不估算金额。[功能与瑕疵](../evaluation/results/p3_closeout_20261023/report.md)、[人工核对](../evaluation/results/p3_closeout_20261023/manual_review.md)、[结果与成本](../evaluation/results/p3_closeout_20261023/summary.json)、[文件核验](../evaluation/results/p3_closeout_20261023/verification.json)。

## 此前P3书目修复与离线开发回归

原n04-auto、n06-agent-on的完整FlashAttention标题正确，误拒绝源于主体中的original/paper。生产只改`src/arxiv_evidence.py`：在两处书目标题核对中分离边缘修饰词，原subject/need和全局主体匹配保持；错误论文、方法连字符/版本混淆和空名称仍拒绝。

| 本次验证 | 结果 | 模型/公网请求 |
| --- | --- | --- |
| 修复前新增7项行为回归 | 复现6个失败子场景，错误0 | 0/0 |
| 修复后定向集 | 26项通过，失败/错误0 | 0/0 |
| 修复后全套离线 | 298项通过，失败/错误/跳过/网络尝试0 | 0/0 |
| 原两组subject/title离线核对 | 正确标题均通过，错论文及FlashAttention-2均拒绝 | 0/0 |

该修复轮main回归保留PDF解析、原文身份/引文和回答复核代码，替换模型/HTTP/CPU资源，因此只验程序行为。旧题被分析并参与修复后属于开发回归：用于验证已知问题和防止复发，不能重算成独立新题准确率。该轮没有新的真实模型运行，不将原5/6、1/2改写为修复后的分数；下方冻结结果完整保留。[修复报告](../evaluation/results/p3_subject_fix_20261022/report.md)、[全套测试](../evaluation/results/p3_subject_fix_20261022/offline_test_summary.json)、[原失败组合](../evaluation/results/p3_subject_fix_20261022/saved_failure_pairs_after.json)、[文件核验](../evaluation/results/p3_subject_fix_20261022/verification.json)。

## 此前P3六题对照与Auto次级验收

2本地/2缺原论文正例/2精确数值未报告反例，问题/Gold/评分/代码先冻结，随后一次运行真实main的Agent关闭/开启arXiv；n03/n04另跑Auto开启。各路径独立模型请求，只有CPU资源共享。六题初检在Agent两组中完全相同，后续本地行动仍有差异。

| 指标 | Agent-off，6题 | Agent-on，6题 | Auto-on，仅2缺源正例 |
| --- | ---: | ---: | ---: |
| 任务完整且严格事实/引用通过 | 4/6 | 5/6 | 1/2 |
| 正例完整回答 | 2/4 | 4/4 | 1/2 |
| 必答点micro | 5/10 | 10/10 | 2/5 |
| 正例macro覆盖 | 50% | 100% | 50% |
| 反例正确拒答 | 2/2 | 1/2 | 未计划反例 |
| 程序completed/degraded/failed | 6/0/0 | 5/0/1 | 1/1/0 |
| 实际模型请求 | 23 | 39 | 14 |
| 输入/输出/总token | 38002/2865/40867 | 98175/5309/103484 | 31043/1832/32875 |
| 实际arXiv GET | 0 | 6 | 2 |

Agent-on净多完成1题（本样本+16.67个百分点），两个缺源正例均恢复，但新增一条无交付失败；多16模型请求/62617 token，token为关闭的2.532倍。Auto只测试预注册两正例，不能拿1/2与完整六题整体作收益比较。

n04-auto及n06-agent-on的主体含original/paper，正确书目标题没有这些修饰词而被词法校验误拒绝，均在搜索前失败。前者degraded、后者failed，计入分母。n04-agent-on首次复核错误登记了answer_quote里没有的引用，有限修订多2请求，最终答案文字未变；不是事实纠错收益。

全轮76次chat/POST、177226 token（输入167220/输出10006），全stop、模型HTTP失败/usage缺失/自动重试0；运行8GET均HTTP200，Gold预核验另2GET。没有模型judge或货币估价。顺序单次CPU预加载中位耗时Agent-off/on为27.029/36.462秒，非冷启动、并发或P95。四次实际PDF哈希均与冻结Gold一致，全部外部偏移/本地登记有效；数据和历史分数保持。

同助手出题/审阅、6题小样本，外部原文不在原索引，不能称为Recall@10提升或总体泛化证明。该轮生产代码冻结，旧失败未调提示重跑，当时P3稳定性未通过；后续书目修复见上，P4仍未开始。[完整报告](../evaluation/results/p3_validation_20261022/report.md)、[人工原文核对](../evaluation/results/p3_validation_20261022/manual_review.md)、[汇总JSON](../evaluation/results/p3_validation_20261022/summary.json)、[标题失败诊断](../evaluation/results/p3_validation_20261022/failure_diagnosis.json)。

## 此前P3.2工程接入与真实验证

新增19项main路径、原文身份、拒答、失败、预算和引用回归；全套291项通过、网络尝试0。显式开启arXiv时，独立网络决策最多3、公开工具最多2（搜索/读一篇），含原流程Agent/Auto模型上限为14/16；默认不增加arXiv请求，未开启仍11/13。

| 运行 | 实际行为与验收 | 模型请求 | 输入/输出/总token | arXiv GET |
| --- | --- | ---: | --- | ---: |
| 首次s01 | 本地Adam答案及第7页引用通过 | 5 | 8687 / 464 / 9151 | 0 |
| 首次s02 | 后续论文候选均拒绝；未完成预期联网回答 | 5 | 5841 / 396 / 6237 | 1 |
| s02第一次开发复验 | 自由检索式带入任务词，旧式ID校验失败 | 4 | 4513 / 322 / 4835 | 1 |
| s02最终开发复验 | 标题查询找到固定v2，第1页摘要5×及出处核验通过 | 8 | 23161 / 869 / 24030 | 2 |

实际合计22次chat/22 POST、44253 token（输入42202/输出2051），全部stop；HTTP模型失败/usage缺失/自动重试0，另有一次搜索结果解析校验失败。4次公开GET均HTTP200；首次自动审批拦截未启动进程/模型，随后用户明确批准这两题、公开片段、现有反代/上游及最多28模型请求后才执行。没有计算货币费用。

最终s02原文36页、134957字符，BM25预选120候选、BGE追加6段；合并17段/10687字符，11段本地全保留。实际耗时41.852秒为CPU资源预加载后的顺序单次，非P95。初次两题预期行为只有s01通过，后续仅是s02开发回归；不拼成当前版本2/2新题准确率，不重算旧检索分数。Auto真实联网、广泛缺源识别及独立补证收益未测。[报告](../evaluation/results/p3_integration_20261022/report.md)、[原文人工核对](../evaluation/results/p3_integration_20261022/manual_review.md)、[账本JSON](../evaluation/results/p3_integration_20261022/smoke_summary.json)。

## 此前反馈修复与P3.1

本轮11项反馈行为回归通过，262项全套通过；加入10项arXiv工具回归后最终272项通过、网络尝试0。旧h10四响应在新提示下离线注入，已支持需求不再被无关原文抹掉，循环推进到需要新反馈前暂停；不是精确同提示缓存、真实新模型或h10最终成功。新增LLM请求/token均0，不重算旧12/8题成绩。[修复报告](../evaluation/results/agent_feedback_fix_20261022/report.md)。

P3.1按用户选择先实现arXiv题录搜索和固定版本PDF读取，公开GET的尝试/成功、PDF页数/哈希单独记录，不混为LLM账单。实测最后2次GET均HTTP200：搜索3篇，读取Mamba v2的36页PDF、134957提取字符；此前权限/TLS失败4次客户端尝试另存。工具尚未接入Agent外部证据/回答链，没有联网答案质量成绩。[P3实测与失败](../evaluation/results/p3_arxiv_tools_20261022/report.md)。

## 此前Agent修复与RAG优先Auto开发回归

普通路径不再先做模型门控，直接用原RAG提示/原文生成及引用修复；通常完整请求从旧Auto4调用降到2，与固定RAG相同。明确证据缺口或引用失败才升级Agent，原草稿不进Agent事实输入；升级失败标degraded/CLI非零，不计完整通过。固定Agent上限仍11，Auto最坏上限13，普通路径成本与最坏预算分开。

251项离线测试通过。a03/a04最终Auto复用旧初检，各1次真实新生成、无Agent调用，必答2/2与3/3；固定Agent阶段一a04恢复3/3（7请求/2工具、仍过处理），a02恢复2/2（4请求、无原附加公式错误）。h10最新Auto触发升级并实际search一次，未补到RAG EM段落，反馈状态再次partial/空gap且修正额度已用，degraded，核心仍1/2；不包装成补证成功。

各阶段共32次新HTTP、98,399 token（输入89,087/输出9,312），全stop，HTTP失败/usage缺失/自动重试0；另精确复用已成功同提示probe1次，33条逻辑记录不重复计费。中间联合门控未采用，22次实际请求和相应失败全保留；RAG优先阶段与输入隔离阶段另10次HTTP。不是新留出，不混合各版本选出的成功题重算准确率。旧8题分数对应旧Auto。

[完整报告及阶段成本](../evaluation/results/agent_auto_improvement_20261022/report.md)、[选型区别](../evaluation/results/agent_auto_improvement_20261022/design.md)、[复算JSON](../evaluation/results/agent_auto_improvement_20261022/summary.json)。主要P1仍是反馈状态稳定性；没有新增P3。

## 此前第一版Auto的8题三路径对照

本轮先冻结3单篇/3跨篇/2不可答题及必答/补充，13处Gold核对PDF。共享一次真实初检，分别执行RAG、固定Agent和Auto，不传Gold或其他路径答案。CLI默认Auto、函数默认RAG；239项离线测试通过。

| 指标 | RAG | 固定Agent | Auto |
| --- | ---: | ---: | ---: |
| 必答完整且可交付，计划8题 | 8/8 | 7/8 | 6/8 |
| 严格事实/引用标准通过 | 8/8 | 6/8 | 6/8 |
| 可答6题核心覆盖micro | 15/15 | 12/15 | 10/15 |
| 可答6题核心覆盖macro | 100% | 83.33% | 66.67% |
| 正确拒答 | 2/2 | 2/2 | 2/2 |
| 路径归因请求 | 16 | 36 | 32 |
| 路径归因token | 23,780 | 75,091 | 62,276 |
| 路径中位耗时 | 28.317秒 | 36.851秒 | 35.535秒 |

Auto路由4direct/1agent/1stop/2failed；预先主标签一致5/8，含a08预先记录的合理搜索替代为6/8。Agent/Auto各实际search+read_neighbors两行动确认DPR费用/能耗不足，随后本地拒答；未出现可答题补查增益正例。2道Auto失败是排版连字符的逐字引文误阻塞、复杂并列主体规划拒绝；固定Agent也在后者失败。严格标准另扣固定Agent的附加公式说明，核心点不扣分；保守判断与引用冗余均公开。

实际68次chat/68 POST，149,573 token（输入140,036/输出9,537），全stop、HTTP失败/usage缺失/自动重试0；另有3次本地校验失败，计入分母。共享初检8请求/5,787 token实际仅一次：三路径归因和须减两份共享量。Auto较固定Agent少17.07%归因token，但较RAG多至2.619倍且交付更少，不能声称总体效率改善。共同交付6题的事后诊断子集，Agent/Auto为28/25请求、62,730/51,701 token，少17.58%；不替代计划8题结果。

共享初检Top-10：P=.1667、nP=1、Macro Recall=1、MAP=.7755、MRR=.8750，只统计6道有Gold题；实际生成上下文含原有身份锚点另计。CPU预加载顺序单次、非P95；同库、同助手出题/审阅、不是独立盲评，驱动共享初检也不等于三次独立CLI全程运行。**本轮实验已收尾，稳定性/质量收益未通过；P3未开始。** [完整报告](../evaluation/results/auto_closeout_20261022/report.md)、[逐题审阅](../evaluation/results/auto_closeout_20261022/manual_review.md)、[冻结标准](../evaluation/results/auto_closeout_20261022/review_protocol.md)、[汇总](../evaluation/results/auto_closeout_20261022/summary.json)、[设计与作用](../evaluation/results/auto_closeout_20261022/design.md)。

## 此前main入口集成验证

2026-10-22，main新增显式rag／agent选择；默认rag保留，Agent只初检一次再决策，不先生成RAG草稿。新增13项入口测试，全部230项离线测试通过、网络尝试0。两道已知题真实CLI共8次请求／8 HTTP POST，输入12689、输出942、共13631 token，无失败／usage缺失／自动重试；一题有出处回答、一题缺原论文停止，后者回答阶段0调用。

两题均0工具行动；工具执行、追加引用、资源复用另由真实入口离线测试覆盖。可答题实际使用英文，中文输出一致性有瑕疵并已留档。这是集成冒烟，不计算新的整体准确率或Agent收益。选择路径由调用者明确指定，尚无自动路由准确率；完整性优先级与新题必答／补充区分见[PROGRESS](../PROGRESS.md)。[接入报告](../evaluation/results/main_agent_integration_20261022/report.md)、[真实汇总](../evaluation/results/main_agent_integration_20261022/smoke_summary.json)、[原文核对](../evaluation/results/main_agent_integration_20261022/manual_review.md)。

## 规划修复后的三题开发回归

2026-10-22，b02/b03/b06均由规划失败恢复为交付答案，三个新规划一次通过，模型review_passed均3/3。按原冻结细粒度评分严格通过1/3、核心完整7/9：b03漏S最短边定义，b06漏通常省略LRN及配置例外；不能把模型pass替代人工评分。全部217项离线测试通过（新增15项），网络尝试0。

本轮仅重跑三题Agent，复用原初检，实际15次请求／39103 token（输入35697、输出3406），没有新初检调用；HTTP失败、缺失usage、自动重试0。这三题已用于诊断与提示修改，属于开发回归。未重跑其余9题、未拼接新12题分数、未证明新题泛化收益。旧实验与失败记录保留；[修复流程](../evaluation/results/agent_plan_fix_20261022/report.md)、[逐条审阅](../evaluation/results/agent_plan_fix_20261022/manual_review.md)、[汇总JSON](../evaluation/results/agent_plan_fix_20261022/summary.json)。

## 修复前P2.5成对结果

12道同语料新题，4单篇、6跨篇、2不可答；同八篇知识库、同API模型和参数，共享同一次真实固定RAG初检。比较的是在已有RAG检索结果上增加当前Agent层的整体效果。不是统一生产用户入口已经接好，也不能拆出工具、提示、复核各自的因果贡献。

| 指标 | 固定RAG | Agent | 解释 |
| --- | ---: | ---: | --- |
| 成功交付（含合理拒答） | 12/12 | 9/12 | 3题Agent规划校验失败，无交付答案 |
| 冻结严格标准通过 | 10/12，83.33% | 7/12，58.33% | 计划分母保留失败题 |
| 可答题严格通过 | 8/10 | 5/10 | 两道不可答题单列 |
| 可答核心覆盖macro | 94.17% | 64.17% | 每题等权，partial不计完整 |
| 可答核心覆盖micro | 25/27 | 16/27 | 冻结评分点累计 |
| 正确拒答 | 2/2 | 2/2 | 未猜缺失数值 |
| 路径归因模型请求 | 24 | 49 | 共享初检各分摊一次 |
| 路径归因token | 34,470 | 95,440 | Agent/RAG=2.769倍 |
| 路径中位耗时 | 33.546秒 | 41.180秒 | 共享CPU模型预加载、顺序单次，非P95 |

实际整轮为61次chat POST、121,397 token（输入112,607、输出8,790），全部stop，HTTP失败/自动重试0。共享初检12次/8,513 token实际只发生一次，因此24+49-12=61，34,470+95,440-8,513=121,397。未核验货币单价，不推算人民币费用。

主评分包含较细限定，不能泛称通用答案准确率。DPR表注/正文定义歧义以及b03、b09附加背景要求公开保留；事后仅放宽后两处为11/12与8/12，仍差3题。同助手出题、审阅，部分原子知识与旧题重合，样本小，非独立盲评或总体显著性证明。

该轮结论：**已有可复核量化结果，但修复前Agent未证明优于固定RAG。** 三种规划阻塞已修复并完成开发回归；修复版本的独立新题收益仍需另建留出检验。

## 检索指标的口径

本轮共享初检的10道可答题Top-10：Precision=.180000、整体nP=.818182、Macro Recall=.841667、MAP=.528280、MRR=.615238。不可答题无Gold，跳过检索评分。两条路径共用这组排名；不能把Agent后续增加上下文称为同预算Recall@10提升。

这些指标来自本轮题集，不能与旧42题或P1的12题分数直接相减作进步结论。Gold为非穷尽标注，替代原文也可能正确支持答案。整体nP与宏平均Recall分母/权重不同，保留原始Precision及全部指标。

## 最终交付应保留的量化内容

- **规模与版本**：实际论文、页数、分块、向量维度、知识库版本和文件哈希。
- **检索**：固定题集上的Precision、nP、Recall、MAP、MRR；不同K策略独立运行并说明预算。
- **回答**：核心点完整性、严格通过、引用支持、错误与拒答；计划分母和成功子集分开。
- **Agent执行**：工具选择、行动次数、停止原因、无进展/预算耗尽、规划和运行失败率。
- **成本与性能**：实际请求、输入/输出token、usage缺失、耗时；共享、冷启动、并发条件分清。
- **改进证据**：同题/同库/同模型对照，原始失败和修复后开发回归，再以新留出检验。只有实际通过后才写提升数字。

## 本轮原始证据

- [完整报告](../evaluation/results/agent_p25_20261021/report.md)、[逐条原文审阅](../evaluation/results/agent_p25_20261021/manual_review.md)。
- [冻结题集](../evaluation/results/agent_p25_20261021/questions_frozen.json)、[冻结评分](../evaluation/results/agent_p25_20261021/review_protocol.md)、[PDF引文核验](../evaluation/results/agent_p25_20261021/gold_verification_before_run.json)。
- [质量与成本JSON](../evaluation/results/agent_p25_20261021/summary.json)、[逐题指标](../evaluation/results/agent_p25_20261021/case_metrics.json)、[实际模型账本](../evaluation/results/agent_p25_20261021/actual_chat_calls.json)。
- [最终离线核验](../evaluation/results/agent_p25_20261021/verification.json)、[当前交接进度](../PROGRESS.md)。

阅读以上文件不产生请求。无需因更换对话、恢复额度或更换设备而重复运行已完成实验。
