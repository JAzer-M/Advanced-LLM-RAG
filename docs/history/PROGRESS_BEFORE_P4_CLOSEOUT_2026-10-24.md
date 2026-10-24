# Advanced-LLM-RAG 当前进度与交接

**中文比较需求绑定修复（2026-10-24）：** 已知问题“VGG和RAG的区别是什么？”此前被绑定成“vgg的区别是什么?”、“rag的区别是什么?”，导致 Agent 只讲 VGG 内部配置和 RAG/DPR 的差异。用原抽取复现后确认：`agent.isolate_need()` 的中文比较规则支持“有什么区别”，漏了后置“是什么”；只修改两处匹配，使其沿用逐方描述、保留原比较引文与明确方面的路径。新增3项回归，原失败测试先红后绿，40项定向、345项后端及27项网页测试通过。网页首轮两项因沙箱禁止临时本机端口报错，放开本机端口后通过，原失败输出保留。当前9篇库/cn:glm-5.3 真实 main Agent 一题 completed/review_passed，102.13秒、9请求、34320 token（输入29853/输出4467）、1次读邻段、arXiv/自动重试0；一次复核引用登记错误触发既有有限修订，初稿和失败复核保留。最终直接比较 VGG 的视觉分类/卷积网络与 RAG 的文本检索增强生成，核心事实已对照引用原文。此为已知题开发回归；初检片段与旧运行不同，不据此宣称独立准确率或提速收益，不改旧成绩。[修复、验证与边界](evaluation/results/chinese_comparison_20261024/report.md) · [真实结果](evaluation/results/chinese_comparison_20261024/live_summary.json)

**回答语言与模型 JSON 兼容（2026-10-24）：** 用户换用 cn:glm-5.3 后，中文 VGG/RAG 比较题在 Auto 升级 Agent 时失败：glm 把评估结果包在 ```json 代码块里，原解析器只认纯 JSON，两次格式错误用完唯一修复额度，退回初稿（degraded）。新增 `src/model_json.py`，7 个解析模型 JSON 的位置只剥掉整段回复外的一层代码块，其余校验不变。同时按用户要求让回答语言跟随提问语言（明确指定时按指定）：新增 `src/answer_language.py`；RAG/Agent 回答提示词、Agent 缺口说明、程序插入的固定文字（补查未完成、arXiv 失败说明、证据不足清单、来源）均按语言输出；Auto 缺口判断补充英文“direct comparison”等措辞，避免英文概览题被误升级。新增 11 项测试；15 项原测试用英文提问却断言中文固定文字，已改为对应英文措辞。全套 342 项与 webui 27 项离线通过。真实验证（cn:glm-5.3，网页，开启联网）：英文 Auto 直答 37.1 秒/2 请求/4151 token、英文回答；中文 Auto 直答 37.1 秒/2 请求/3550 token；中文 Agent completed/review_passed，133.8 秒/7 请求/31338 token，评估步骤的代码块回复被正常解析、未用修复额度。两题都不需要 arXiv（论文均在本地库）。遗留：中文“A和B的区别”被拆成“A的区别是什么”“B的区别是什么”，Agent 回答偏题（讲 VGG 各配置差异、RAG 与 DPR 差异），需另行修复需求拆分。以后新评测的回答语言跟随问题，不与旧“英文问中文答”成绩直接比较。

**前端重设计（2026-10-24，待用户验收）：** 按用户确认的设计稿重写 `webui/` 的 index.html、style.css、app.js：暖白/朱橙主题；结果页只保留问题、回答、原文三部分，状态只在异常时出现；点编号同时标出回答中的句子和原文；Enter 发送并处理输入法选词；联网开关改名“联网搜索”（仍只查 arXiv）；模型设置自动填好当前模型、可用已保存密钥获取列表；中英文界面切换。后端、检索参数、提示词、server.py 和测试未改，未重跑 331 项测试。用模拟服务（真实运行记录）做了浏览器检查，Mac 上用真实网页库和模型网关检查了回放、引用联动和模型列表（21 个），未发起真实问答。删除 `ui_prototype/` 的页面文件和 start.command，保留被复用的 app.py。改动前完整状态已提交到分支 `paperlens-frontend-redesign`（提交 00d7f6e）。

**联网UI追加验收（2026-10-23）：** 用户要求开启arXiv跑一次。新版页面Agent成功搜索并读取Mamba `2312.00752v2`，两次GET均HTTP200；completed/review_passed，48.89秒、8模型请求、24836 token。第1页摘要5×及第15页补充均经原文核对，未入库、未自动重试。连同本轮首条本地RAG验收，助手共10请求/27890 token。一次成功不代表外部来源长期稳定，不改旧成绩。[完整日志](docs/WEBUI_REBUILD_2026-10-23.md) · [联网汇总](docs/maintenance/webui_20261023/network_smoke_summary.json)。

**最新前端交付（2026-10-23，待用户验收）：** 按用户要求在 `webui/` 从空白重做PaperLens，独立端口8849，旧版8848保留。暖白/墨绿/朱橙的研究台，支持三模式提问、引用原文、论文搜索、运行记录和同页签刷新恢复。9项适配层离线检查通过；新页面真实RAG一条16.28秒/2请求/3054 token，刷新仍接续原任务，无arXiv、无自动重试。原核心/测试/旧UI共61份文件哈希不变；未重跑331项整套测试。此次没有修改后端答案质量策略。[启动](webui/start.command) · [完整开发日志与边界](docs/WEBUI_REBUILD_2026-10-23.md)。

更新：2026-10-23（Asia/Shanghai，Auto比较题/性能/网页恢复）。工作区：`/Users/j/Desktop/Advanced-LLM-RAG`；已有大量未提交成果。本轮针对用户实际VGG/RAG比较题修复意图与过度升级，最终实测30.98秒/2模型请求/4037 token，原101.85秒/8请求/28092 token。331项离线通过；五轮真实开发合计21请求/54187 token，失败和中间结果保留，没有提交或推送。

**结论：主要比较与速度已改善，本地网页已恢复。** 用双方摘要支持独立事实比较，简单英语概览避免重复规则补查；显式强制补查、其他题型与原预算保留。最终核心原文核对通过，附带联合微调句的引用覆盖仍不全，不冒充全文严格语义通过。Mac可双击桌面的「PaperLens 启动.command」（即[webui/start.command](webui/start.command)），保持终端打开后访问[研究台](http://127.0.0.1:8849)；旧版8848页面已于2026-10-24删除。这是本题开发验证，非新独立成绩。[修复及全部成本](evaluation/results/auto_comparison_20261023/report.md) · [人工核对与残留](evaluation/results/auto_comparison_20261023/manual_review.json)。

本页负责当前状态、约束与下一步；多轮原始交接转入[完整历史](docs/history/PROGRESS_THROUGH_2026-10-22.md)，包括全部失败、调用量、实验口径和复现命令。各实验原始文件及路径保留，[实验索引](evaluation/results/README.md)可逐轮查阅。桌面《RAG项目全流程与进度总览.md》与 [PROJECT_WORKFLOW](docs/PROJECT_WORKFLOW.md)内容一致，二者只描述预期路线，不表示实际完成。

## 1. 阶段状态

| 阶段 | 已完成 | 仍未完成或边界 |
| --- | --- | --- |
| 基础 RAG 与检索改进 | PDF、分块、混合检索、重排、问题分解、证据保留、规则补查、引用检查 | 解析/分块不保证无损，引用结构通过不等于语义正确 |
| P0 论文与知识库 | 三篇、五篇、八篇配对版本及校验、切换、回退 | 通用去重和完整增量导入生命周期延期 |
| P1 评测基线 | 检索指标、小规模12题固定 RAG 回答/拒答/成本记录 | 同助手出题审阅，非第三方盲评或大规模泛化 |
| P2.1～P2.4 | 需求绑定、证据判断、搜索/邻段、预算循环、生成与有限复核 | 早期h10/h11属于已知开发验收，不能覆盖最新版失败 |
| main 接入 | `rag`、`agent`、`auto` 共用初检与资源，保留各模式记录 | 函数默认rag；CLI默认auto；历史“尚未接main”已过时 |
| P2.5 对照与收尾 | 首轮12题 RAG/Agent、第一版Auto的8题三路径对照及原文审阅 | 旧12/8题成绩保持版本边界；最新P3六题Agent对照与两题Auto次级验收另列，非总体收益证明 |
| 最新 Agent/Auto 改进 | RAG优先Auto、反馈状态修复、书目修复及本轮故障交付；共331项离线回归通过 | 旧h10真实失败保留；隐性漏答和总体收益未证明 |
| P3 / P4 | P3.1/P3.2及故障交付已完成；P4本地网页原型已启动，真实RAG提问通过 | 单用户原型，未正式发布/持久会话；arXiv仍默认关闭、外部可用性未恢复 |

## 2. 当前三条执行路径

- **固定 RAG**：分解 → Dense/BM25 → RRF → 全局BGE/子题局部证据 → 按来源信号最多两轮补查 → 生成 → 引用检查/必要时一次修复。常规完整问题通常为分解、回答两次调用。
- **固定 Agent**：共用一次初检后，独立规划需求、逐项检查，模型选择搜索/读取邻段/回答/停止，Python校验并执行；回答阶段逐项复核、必要时修订一次。
- **Auto**：先用固定RAG相同提示和证据生成/修复引用；出现明确缺口、无法回答或比较、引用失败才升级原Agent；简单英语概览中，已有引文事实后的未要求性能/直接实验比较说明不触发升级。普通路径没有额外门控调用。Agent事实输入只含问题、绑定需求、原文与论文目录，RAG草稿不作为事实证据。

`main(..., mode='rag')`保持Python原默认；命令行默认`--mode auto`。RAG未指定版本时读三篇激活指针；Auto/Agent仅支持八篇，不切换指针。同库比较必须让RAG显式使用八篇。运行命令见 [README](README.md)，保存记录模式见 [Agent 操作](docs/AGENT_REPLAY_GUIDE.md)。

**预算与失败：** 未启用arXiv时，固定Agent最多1次分解+6次决策+4次回答=11请求；Auto另保留最多2次前置草稿/引用修复，最坏13请求。显式`--allow-network`另加最多3次联网决策，上限分别14/16；公网工具另限一次搜索/一次固定PDF读取，不重置本地预算。工具最多3行动，证据最多32段/24000字符；规划、状态修正或重复行动改选共用一次额度，不能因升级重置。回答最多初稿/复核/修订/再复核4次。全部missing时回答阶段本地说明缺口、0请求。网络/截断失败不自动重试，`finish_reason='length'`不能算完整输出。

Auto的规划/循环/回答复核失败时，仅原草稿引用结构合格才允许`degraded`保留，CLI非零；loop失败、草稿与原因均留档，不能计作完整成功或保证草稿事实正确。隐性漏答可能没有升级信号。新输出目录须为空，旧运行受输入/源码哈希约束，不强行覆盖或续写。

外部搜索/PDF读取遇429、超时等传输失败时，Auto可保留合格初稿，Agent或没有合格初稿的Auto仍使用已校验的本地输入回答；全缺失直接列出未核实需求，部分支持仍走原生成/复核预算。获取失败不等于论文未报告，missing/partial的回答输入缺口改为中性说明，原判断留在loop。HTTP记录状态、必要响应头、有限错误正文、Retry-After和耗时；本轮选择停止，不自动重试或引入缓存。来源/原文校验错误仍保持失败，不能冒充临时网络问题。

三模式返回`status/answer/answer_status/stop_reason/ledger/selected_ids/actions/api_summary/network`；运行时故障返回可展示结果，参数/配置等请求前错误仍抛出。`completed`不是准确率标签；`source_unavailable`不算完整事实答复。评测采集已适配，避免将返回的failed/degraded重标为完成。[字段与处理顺序](docs/BACKEND_RESULT.md)

## 3. 已有质量与成本证据

**最新用户问题修复（2026-10-23）：** VGG/RAG比较由内部版本/无直接比较拒答，恢复为任务与机制的直接比较。原运行101.85秒/8模型请求/28092 token；最终30.98秒/2请求/4037 token、Auto直答、无arXiv、无自动重试。主要原文核对通过；联合微调句应补[7]、当前仅[19]，保留该瑕疵，不宣称全文引用覆盖全通过。新增17项后全套331项离线通过、网络尝试0。五轮真实开发共21请求/54187 token，包含拒答/降级、62秒中间版本及49秒仍过度升级，均保留。缓存单项测量65.028→50.712秒且原10个ID保持；最终概览路径追加双方摘要，默认规则补查0次。显式强制与具体方面问题仍走原补查，候选120/Top-10及上限不变。详情见[本轮报告](evaluation/results/auto_comparison_20261023/report.md)。

**最新P4本地网页试验（2026-10-23）：** 新增`ui_prototype/`，原生HTML/CSS/JS加Python标准库WSGI，无新增依赖或生产后端改动。固定用八篇1397段知识库，RAG显式指定该版本，不切换激活指针。启动与回放均不调用模型，点击实时运行才复用现有main，保留模型/联网预算；新运行写入`logs/ui_prototype/`。

三个真实历史案例的本地回答、联网成功、来源不可用展示均可加载；浏览器检查了案例切换、引用定位/展开、运行过程、窄窗口知识库入口和等待状态。真实只跑一条已知VGG开发问题，RAG、本地模式：2模型请求，输入2733/输出72/总2805 token、约15.3秒，失败/usage缺失/本地重试0、arXiv GET0；回答步长与padding均1像素，与VGG第2页引用原文一致。RAG仅作引用结构检查，不冒充Agent复核或独立新题成绩。原生产/测试源码哈希保持，没有重复314项整套测试。[UI报告](evaluation/results/ui_prototype_20261023/report.md) · [真实运行与人工核对](evaluation/results/ui_prototype_20261023/smoke_summary.json)

**最新后端稳定性修复（2026-10-23）：** 先保存4154份现有文件哈希及源码/测试基线，核对上一段对话全部11个用户回合与当前代码。初始13项新增故障回归复现交付/字段/诊断问题；随后补测“不应复制未报告断言”、RAG故障保留原文及采集器保留失败，共新增16项。最终314项离线通过，失败/错误/跳过/网络尝试0；常规RAG和Auto直答仍各2模型调用，预算、真实原文和来源校验保留。

真实只跑一次n06/Agent，源码/问题/公开API选项及14模型请求/2GET上限先冻结。实际4模型POST、4915 token（输入4566/输出349），均stop、模型失败及usage缺失0；1次arXiv搜索在约30.735秒后超时，未返回HTTP状态或Retry-After，未读PDF，不重试。初检上下文和片段ID与此前n06逐字节一致，10段本地原文保留；无回答阶段模型请求。最终degraded/source_unavailable/external_timeout，明确暂时无法核实，不能据此断言论文未报告。故障交付通过，原事实问题仍未核实，不重算旧分数。[报告](evaluation/results/backend_reliability_20261023/report.md) · [离线测试](evaluation/results/backend_reliability_20261023/offline_test_summary.json) · [真实运行](evaluation/results/backend_reliability_20261023/live/summary.json) · [人工核对](evaluation/results/backend_reliability_20261023/manual_review.json)

**此前P3两条真实开发回归与收尾报告（2026-10-23）：** 问题、源码、API公开选项及30模型请求/4GET上限先冻结，实际main独立运行n04/Auto-on与n06/Agent-on；只复用真实CPU资源，不共享模型响应，不传Gold/旧答案。两条均通过标题核对，但arXiv搜索返回429，分别degraded/failed，完整任务0/2。本次n04主体original FlashAttention paper实际验证了修饰词分离；n06主体FlashAttention不含修饰词，不能当成精确重现旧词组。两组初检上下文均与旧对应路径逐字节一致，本地原文保持；没有读到PDF或执行外部检查/最终回答复核，相关核验为不适用。

本轮实际9模型POST、12278 token（输入11422/输出856），全部stop，模型HTTP失败/调用失败/usage缺失0；另2搜索GET均429，PDF/Gold GET/自动重试0。n04保留安全但未回答三个必答点的初检缺口；n06没有最终拒答。429具体来源原因未确认，未重试刷成功。报告区分已有真实成功、当前实测失败、离线修复、未验证及设计边界，旧成绩不改；生产/测试不变，本轮未重复298项整套测试。[功能与瑕疵](evaluation/results/p3_closeout_20261023/report.md) · [人工核对](evaluation/results/p3_closeout_20261023/manual_review.md) · [成本与结果](evaluation/results/p3_closeout_20261023/summary.json) · [文件核验](evaluation/results/p3_closeout_20261023/verification.json)

**此前P3书目修复（2026-10-22～23）：** 旧n04-auto和n06-agent-on给出的完整FlashAttention标题正确，失败发生在GET之前；根因是将original/paper来源修饰词纳入论文名称。先写7项行为回归，在原代码上复现6个失败子场景；再只在`src/arxiv_evidence.py`增加`paper_subject()`，用于模型提出标题和实际返回标题的两处核对。保留原subject/need和全局主体匹配，连字符/版本数字不删，空名称仍拒绝。

该轮定向26项及全套298项离线通过、网络尝试0；Agent/Auto实际main测试使用受控模型/HTTP/CPU资源，PDF解析、来源核对和回答复核走真实代码。原两组subject/title离线均通过，错论文及FlashAttention-2仍拒绝；不等于原两题真实模型全流程已成功。该修复轮新增模型请求/token/公网GET均为0。已暴露并参与修复的旧题称为开发回归，用于查修复和防复发，不能变成新的独立准确率。知识库、配置及旧实验文件按基线哈希核对，原4/6、5/6、1/2不改。[修复与验证](evaluation/results/p3_subject_fix_20261022/report.md) · [全套测试](evaluation/results/p3_subject_fix_20261022/offline_test_summary.json) · [文件核验](evaluation/results/p3_subject_fix_20261022/verification.json)

**此前P3六题对照（2026-10-22）：** 先冻结2本地可答/2缺原论文正例/2原论文未报告精确数值反例及评分，六题各跑真实main Agent关闭/开启arXiv；n03/n04另预注册Auto开启，共14路径。只复用CPU资源，各路径真实分解/生成；Gold不传给模型、参考PDF不加入知识库。六题初检上下文在两组Agent中逐字节一致，后续行动有模型差异。该轮生产代码全程冻结，失败没有调提示重跑。

Agent-off/on任务完整且严格事实/引用通过4/6、5/6；正例完整2/4→4/4，必答点5/10→10/10，反例正确拒答2/2→1/2。RoFormer位置编码和FlashAttention IO机制均有实际原文/页码支持；但n06-agent-on主体original FlashAttention paper、n04-auto主体original FlashAttention，正确标题不含修饰词而被词法匹配拒绝。前者failed无答案，后者degraded保留初检缺口，均计分母；不是HTTP故障。Auto次级1/2，不与六题总体比较。

主对照23→39模型请求、40867→103484 token（2.532倍、多62617）；Auto另14请求/32875 token。实际合计76次chat/POST、177226 token（输入167220/输出10006），全stop，模型HTTP失败/usage缺失/自动重试0；8次运行arXiv GET均HTTP200，Gold预核验另2次。n04-agent-on首次review引用登记不合格，有限修订/再复核多2调用，最终答案文字未变。不是事实纠错收益。顺序预加载CPU耗时非并发/P95，不估算金额。[完整报告](evaluation/results/p3_validation_20261022/report.md) · [逐题原文审阅](evaluation/results/p3_validation_20261022/manual_review.md) · [汇总](evaluation/results/p3_validation_20261022/summary.json) · [失败诊断](evaluation/results/p3_validation_20261022/failure_diagnosis.json)

**此前P3.2工程验收（2026-10-22）：** main新增默认关闭的`allow_network`/`--allow-network`，独立`src/arxiv_evidence.py`在本地正常缺源停止后最多定位/读一篇arXiv原论文。搜索题录不进事实白名单；固定版本、PDF哈希及重解析原文通过校验后，BGE选最多6段追加，保留本地证据、页码、独立ID和连续原文位置，再复用原逐项检查与有限回答复核。无新依赖，agent.py/原检索/原回答/工具代码保持；新增19项入口、失败和预算测试，共291项离线通过、网络尝试0。

真实工程验证首次两题：s01回答Adam并核对第7页、无arXiv；s02只返回后续论文，安全拒答，预期联网回答未通过。第一次同题开发复验仍因自由检索式带入abstract且返回不支持的旧式ID而失败；最终收紧为“模型给完整书目标题、Python构造标题查询”后，s02完整定位Mamba `2312.00752v2`、读取36页、引用第1页摘要回答5×吞吐量，并复核第2/15页补充。最终上下文11段本地+6段外部、10687字符，本地原文全保留；没有自动入库。

初次10请求+失败开发4+最终开发8=**22次模型POST、44253 token（输入42202/输出2051）**，全stop，HTTP模型失败/usage缺失/自动重试0；另4次arXiv GET均HTTP200，其中一次后续解析校验失败。首次自动审批在请求前拦截，明确告知目的地/数据/费用并获用户授权后才运行，拦截本身0调用；总模型请求低于批准28上限。最终s02单次41.852秒、8请求/24030 token，CPU预加载顺序单次，非P95；不推算货币费用。两题及开发复验属于当时工程验收，不是独立泛化成绩；该轮尚未测Auto真实联网和新题总体收益，后续六题结果见上。[完整流程与失败](evaluation/results/p3_integration_20261022/report.md) · [原文审阅](evaluation/results/p3_integration_20261022/manual_review.md) · [合并账本](evaluation/results/p3_integration_20261022/smoke_summary.json)

**此前反馈修复（2026-10-22）：** 工具反馈始终复查未完成需求；已supported项只有遇到同源新段或明确提及其主体的原文才重新检查。其余保留上一份已校验状态和引文，额外返回的未授权状态更新不应用；合并后仍执行原完整状态/主体/引文/行动校验。相关新反证可重新打开，非法partial不自动改supported；单步/循环/改选沿用同一次修正额度。只改agent.py两处原函数、新增feedback_scope，main/检索/回答代码不改。

新增11项反馈行为回归，全套先262项通过；P3.1另加10项后最终272项通过、网络尝试0。完整旧h10响应前缀在新提示下离线注入后不再因r2空gap重复失败，实际读取一次本地邻段；在需要未记录的新模型反馈前停止，不能当作完整h10通过或精确同提示缓存。本轮模型请求/token均0，旧成绩不重算。[修复流程](evaluation/results/agent_feedback_fix_20261022/report.md)、[回放边界](evaluation/results/agent_feedback_fix_20261022/saved_prefix_summary.json)。

**P3.1起步：** 用户明确选择arXiv。搜索只用于定位带版本论文，读取固定版本PDF并保留来源/页码/章节/原文、获取记录及哈希，外部evidence_id与本地chunk_id分开；不自动入库、生成答案或联网调用Agent。实现、实测与失败见[P3.1报告](evaluation/results/p3_arxiv_tools_20261022/report.md)和[设计/输入输出](evaluation/results/p3_arxiv_tools_20261022/design.md)。首次沙箱和随后CA失败均独立保留；补充根证书后真实搜索HTTP200返回3篇，读取搜索中找到的Mamba固定v2，PDF36页/1168615字节、提取134957字符；跨三批6次客户端GET尝试、2次HTTP200，模型请求0。工具可用不等于回答收益通过。

| 冻结对照 | 固定 RAG | Agent | 第一版 Auto | 证据 |
| --- | --- | --- | --- | --- |
| P2.5 首轮12题严格通过 | 10/12 | 7/12 | 当时未加入 | [报告](evaluation/results/agent_p25_20261021/report.md) |
| 同12题可答核心macro | 94.17% | 64.17% | — | [原文审阅](evaluation/results/agent_p25_20261021/manual_review.md) |
| 同12题归因token | 34470 | 95440 | — | [复算](evaluation/results/agent_p25_20261021/summary.json) |
| 第一版Auto的8题严格事实/引用通过 | 8/8 | 6/8 | 6/8 | [报告](evaluation/results/auto_closeout_20261022/report.md) |
| 同8题必答完整且可交付 | 8/8 | 7/8 | 6/8 | [原文审阅](evaluation/results/auto_closeout_20261022/manual_review.md) |
| 同8题归因token | 23780 | 75091 | 62276 | [复算](evaluation/results/auto_closeout_20261022/summary.json) |

两批不可答题各路径均正确拒答2/2。12题Agent有3题规划失败，8题Agent/Auto也有校验失败；分母包括无交付题。8题的6道可答题初检Gold均齐，未验证可答题的补证增益。两批均同库、同模型、共享真实初检；归因token不可直接相加当实际账单。12题实际61请求/121397 token，8题实际68请求/149573 token。严格评分中背景定义与引用要求的差异及敏感性见原报告，不回改历史主成绩。

**此前RAG优先Auto开发回归（反馈修复前），不能拼接成新准确率：** a03/a04的最终Auto复用已保存真实初检，各1次新生成恢复直答；固定Agent的a04恢复交付但仍过处理，a02回归不再附加原错误公式解释。h10触发升级且真实search一次，未取到所需RAG判据段落；已支持的Self-RAG需求反复被标partial却不给gap，唯一修正用完后`degraded`，核心仍1/2，未通过。

该轮跨版本开发累计32次新HTTP、98399 token（输入89087/输出9312），全部stop、HTTP失败/usage缺失/自动重试0；另精确复用1次已成功的同提示probe，33条逻辑调用不双计账单。联合门控试验未采用，阶段源码与全部失败保留。最新输入隔离版本真实走到反馈阶段，未进入最终生成/复核，后两者最新真实验证不能冒称完成。[改进流程与失败](evaluation/results/agent_auto_improvement_20261022/report.md) · [设计与采用理由](evaluation/results/agent_auto_improvement_20261022/design.md) · [分阶段汇总](evaluation/results/agent_auto_improvement_20261022/summary.json)

**选型：** 固定RAG继续作为质量和成本基线；Auto作为按需升级入口；固定Agent只在需要多步补证据的任务上考虑。普通路径调用从旧Auto通常4次降到2次是路径改进，尚无当前全题集token降幅或总体质量收益证明。

## 4. 优先级与下一步

完整性以用户所问和避免误解所必需的条件为准，保留用户已确认的三层标准：

1. **必须修复**：漏明确子问题、改变结论的单位/条件/范围缺失、跨论文或数据集混淆、编造事实/引错引用、正常问题无交付。
2. **按任务补充**：复现实验需要的定义/步骤/参数，做决策需要的限制条件。
3. **可以省略**：不影响当前任务的背景、例外和延伸。b03的S定义、b06的VGG背景不继续专门调试，原冻结严格1/3、核心7/9保留。

原反馈状态P1的已知机制已修复：保留无关已完成项，同源/明确主体新证据触发复查，真实冲突可以重新打开。相关性规则保守，无法保证识别所有隐含跨来源反证，也不自动修正初始语义误判；最终版本独立新题质量仍未验收。旧h10不继续付费调试，旧32/68/61次请求无需重跑。

P4本地网页已恢复访问，启动文件已补齐。下一步优先处理剩余附带训练句的引用覆盖，并观察其他实际问题；不为背景满分重跑旧评测。约31秒仍有CPU初检耗时，常驻模型/并发/正式会话保存尚未实施。此次是定向后端修复，不是独立质量总分，外部来源不稳定边界保持。

完整性仍按上述三层标准，不为背景细节满分调试；不根据新运行回改旧冻结成绩。

## 5. 配置、知识库与关键约束

| 项目 | 当前值 |
| --- | --- |
| Embedding / reranker | MiniLM `paraphrase-multilingual-MiniLM-L12-v2`，384维 / `BAAI/bge-reranker-base`，CPU |
| 候选 / RRF / 最终证据 | 每路120、RRF候选120、秩平滑常数60；最终10，子题局部3 |
| 规则补查 / 增强 | main按来源覆盖信号最多2轮，候选深度120/240；rewrite/HyDE关闭 |
| 评估入口 | 候选默认120；补查需显式启用，CLI轮数默认1；不同K独立选证据与补查 |
| 生成API | 配置模型`cn:deepseek-v4.1-flash`；历史响应标识`deepseek-v4.1-flash`；标识不独立证明上游权重 |
| 生成选项 | `thinking.type=disabled`、`temperature=0`、`max_tokens=4096`；本轮n06开发回归4请求/4915 token；离线314项0模型请求 |

| 知识库版本 | 分块数 / 维度 | 使用状态 |
| --- | --- | --- |
| `legacy-3papers-20261019` | 378 / 384 | 原三篇逐字节配对快照 |
| `semantic-mac-20261019` | 378 / 384 | **激活指针**；RAG省略版本时使用 |
| `arxiv-pilot-5-20261019` | 1019 / 384 | RAG/DPR/ColBERT/Self-RAG/CRAG，独立先导库 |
| `all-papers-8-20261020` | 1397 / 384 | 三篇/五篇已验证向量精确合并，Auto/Agent使用 |

原三篇为Transformer、DCNN/AlexNet、VGG，不含ResNet；五篇版本分别为RAG v4、DPR v3、ColBERT v2、Self-RAG v1、CRAG v3。各版`faiss.index`、`chunks.json`、`manifest.json`成套保留，位置ID不能跨版本混用。默认PDF构建只遍历本层，不能假定会递归导入全部八篇。[版本操作](docs/KNOWLEDGE_BASE_VERSIONS.md)

- 普通函数、字典、列表与原文件结构优先；重要Python代码补目的/输入输出/预算的中文注释，不新增无必要框架或CLI。
- MacBook Air/PyCharm为主开发环境，本次确认项目Python 3.11.9；具体芯片/内存不推测。Windows RTX 5060 Laptop/约8GB显存是历史用户记录，本次未实测Windows。
- 本项目不做Fine-tuning/LoRA/QLoRA；本地Embedding/BGE与API生成不要求新增GPU。两台电脑的虚拟环境、模型缓存、本机代理和未提交资料不会自动同步。
- 私有API配置、凭证、原始论文、成对索引、Gold、实验/失败和用户未提交工作保留；Git只同步已提交并推送的内容。
- FAISS为归一化`IndexFlatIP`，非HNSW；Chunk保留来源/页码/标题/章节，但标题未作为Embedding正文；Semantic参数500字符/percentile10不保证无损。
- 固定原问题增强前RRF锚点，保护初次局部Top-3；每个K独立补查，不能拿Top-20前缀冒充Top-10。BM25没有有效英文/数字词项时返回空。
- 引用编号结构、词法主体绑定、原文连续引文和模型review_passed均不等于独立语义验收；仍需核对重要断言与原文。

## 6. 检索基线与验证口径

42道历史Gold可答题，候选120、最多两轮、rewrite/HyDE关闭：

| 预算 | Precision | 整体nP | 宏Recall | MAP | MRR | 全Gold入选 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-10 | .1310 | .6790 | .7679 | .4837 | .5708 | 28/42 |
| Top-20 | .0714 | .7407 | .8115 | .4857 | .5727 | 30/42 |

Top-20 Recall增加4.37个百分点，未达当时预定5点门槛，默认10。逐题nP=`H/min(K,G)`，整体=`sum(H)/sum(min(K,G))`，不能平均逐题值；本集81条Gold均G≤K，整体nP等于micro recall，原Recall是macro。Gold非穷尽，不代表其他段落无用；检索覆盖、回答质量和成本分开报告。[量化入口](docs/PROJECT_METRICS.md) · [nP口径](docs/NORMALIZED_PRECISION_2026-10-20.md)

此前书目修复轮全套298项通过；本轮新增16项故障回归后全套314项通过，失败/错误/跳过/网络尝试0，[测试记录](evaluation/results/backend_reliability_20261023/offline_test_summary.json)。模型/HTTP/CPU资源使用替身，真实解析与引用/来源校验保留；常规RAG和Auto直答仍为2调用。随后单条真实n06消耗4模型请求/4915 token、1搜索GET，搜索超时但有明确交付，没有自动重试。此前0/2、4/6、5/6、1/2不重算，本轮未重建索引或重跑大规模旧评测。原历史退出139根因仍未定位；本轮测试及真实进程均正常结束。

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m unittest discover -s tests -v
```

## 7. 文件导航与本次整理

[运行与模式](README.md) · [文档分类](docs/README.md) · [代码阅读](docs/CODE_READING_GUIDE.md) · [Agent工具/回放](docs/AGENT_REPLAY_GUIDE.md) · [实验目录](evaluation/results/README.md) · [完整历史交接](docs/history/PROGRESS_THROUGH_2026-10-22.md)

清理前README/PROGRESS/忽略规则/历史索引逐字节保存在[备份](docs/history/20261022_before_cleanup.zip)。实验路径与得分保持，当前说明从多轮历史中独立整理；删除范围仅可再生成的Python缓存和macOS元数据。[完整清理范围与验收](docs/CLEANUP_LOG_2026-10-22.md)

### 2026-10-23 桌面启动与 WebUI 访问修复

新增桌面「PaperLens 启动.command」，双击自动启动并打开默认浏览器。修复空闲连接阻塞单线程WSGI的问题；并发任务创建加锁，保持单任务。Finder启动→Safari首页“本地已连接”实测通过，11项检查通过。本轮无模型调用。详情见 `docs/WEBUI_REBUILD_2026-10-23.md` 追加日志。

### 2026-10-24 阅读布局与模型列表配置

按截图建议完成阅读优先布局；模型设置增加“获取模型→下拉选择→保存”。19项检查通过，浏览器模拟列表选择通过；当前真实网关7863未启动，实际列表读取失败，未发起真实生成或改动配置。未做入库或公网部署。详见 [交接日志](docs/WEBUI_MODEL_SETTINGS_2026-10-24.md)。

### 2026-10-24 网页PDF入库完成

“论文库→选择PDF→添加并入库”已接通后台解析/向量化/新版本发布。三种网页问答模式固定使用同一网页库版本；原实验默认及激活指针保留。真实Mamba上传后9篇1767段；关闭arXiv的真实RAG问答成功（13.62s、2请求、2965 token），引用本地第1页。102项检查通过。后端改动、失败修复和GitHub交付边界见 [入库交接](docs/WEBUI_PDF_IMPORT_2026-10-24.md)。arXiv链接导入尚未实现。
