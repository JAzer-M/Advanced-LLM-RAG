# Advanced-LLM-RAG 项目进度与新对话交接

更新：2026-10-22（Asia/Shanghai，Auto实现与8题三路径对照收尾；稳定性/质量收益验收未通过）。当前工作区：`/Users/j/Desktop/Advanced-LLM-RAG`；Git 基点 `c2cd612`，有大量已保留的未提交 / 未跟踪工作，尚未提交或推送本轮改动。

## 1. 新对话先看这里

**最新交付（2026-10-22，Auto与一次对照后收尾）：** 用户要求实现Auto、说明设计及每项接入的作用，再做一次对照并收尾。当前CLI默认`auto`；Python函数默认`rag`保留旧接口。Auto共同初检后复用需求规划/证据判断：全supported直答，有可补缺口则同状态进入工具循环，无法建立事实则停止。`routing.json`在工具/生成之前落盘；首次工具前暂停后同协议续接，精确复用原计划与判断，原6决策/4回答/3行动/一次校验修正预算不重置。direct复用原RAG提示和一次引用修复，省去答案复核；不是零成本分类器。新增9项行为回归，全部239项离线测试通过。见[设计及功能作用](evaluation/results/auto_closeout_20261022/design.md)。

**本轮冻结对照：** 8道同库新题（3单篇/3跨篇/2不可答），先冻结必答/补充与13处PDF Gold；共享一次真实初检，比较RAG/固定Agent/Auto，无评分信息或旧答案泄露，不在见结果后改题/调参。必答完整且可交付为8/8、7/8、6/8；严格事实/引用标准为8/8、6/8、6/8，固定Agent另有a02附加公式解释支撑不足，核心点仍给满。可答核心micro为15/15、12/15、10/15；正确拒答均2/2。Auto实际4direct/1agent/1stop/2failed；主路由标签一致5/8，含预先记录的a08合理补查替代为6/8。Agent/Auto的a08均真实search+read_neighbors两行动后停止，回答阶段0请求；没有可答题补查增益正例。详见[本轮报告](evaluation/results/auto_closeout_20261022/report.md)、[原文审阅](evaluation/results/auto_closeout_20261022/manual_review.md)、[复算JSON](evaluation/results/auto_closeout_20261022/summary.json)。

**本轮成本与验收结论：** 实际68次chat/68 HTTP POST，输入140036、输出9537、合计149573 token，全部stop，HTTP失败/usage缺失/自动重试0。另有3次本地运行校验失败（Agent1、Auto2），保留计划分母。共享初检8请求/5787 token；路径归因RAG16请求/23780 token、Agent36/75091、Auto32/62276；归因合计需减2份共享初检。Auto较固定Agent少17.07% token，但仍为RAG的2.619倍且多一题无交付，不能宣称总体效率改善。全8题路径中位耗时28.317/36.851/35.535秒，预加载CPU顺序单次、非P95。6道可答题初检Gold Recall=1，额外补查收益空间有限。**按用户范围，本轮功能实现和对照已收尾；稳定性与质量收益未通过，不自动推进P3，不重跑本批调到满分。** P1待办为排版连字符引文误阻塞、复杂并列主体绑定、附加事实/引用精度，见第2节。旧知识库、默认激活指针、旧结果与失败均保留；未提交/推送。

**此前交付（2026-10-22，优先级保留与main接通）：** 用户确认完整性修复按“必须修复／按任务补充／可以省略”区分，详细规则已写入本文第2节，暂停为b03/b06背景细节调试；保留历史冻结分数，未来新题先区分必答与补充。`main(..., mode='rag')`默认保持固定RAG；`mode='agent'`共用一次新分解／初检后直接接原Agent循环和回答复核，不先生成RAG草稿。当时入口模式由用户／程序明确选择，本轮Auto已在其上接通。

**实现与验证：** 保持原main前四个参数；新增mode和output_dir，命令行支持`--mode agent`。复用初检已加载的索引、Embedding、BM25与BGE；Agent及工具算法／提示未改，query_decomposer仅增可选审计call。Agent最多1分解+6决策+4回答=11请求，最多3工具行动，状态／规划／行动修正共用原一次额度；逐次预写账本，非空输出目录拒绝重跑，失败不改走RAG。默认RAG仍读原激活指针；Agent明确使用八篇库，不切换指针。新增13项入口行为测试，全部230项离线测试通过、网络尝试0；五个原main辅助函数AST保持。

**本轮真实命令行冒烟：** 两道已知题分别走新分解／新检索／原Agent：Transformer优化器题5请求、8761 token，引用[7]→chunk66原文核对通过；Mistral 7B原论文缺失题3请求、4870 token，model_stop且回答阶段0请求，未猜值。实际共8请求／8 HTTP POST，输入12689、输出942、合计13631 token，全stop，HTTP失败／usage缺失／自动重试0。两题均0工具行动；工具执行／资源复用／追加引用已由真实main离线测试覆盖，不冒称本轮真实工具执行。可答题实际输出英文，未遵循中文提示，保留为展示一致性瑕疵，不为冒烟题改提示。这是入口集成验证，不是新留出或整体质量提升证明；旧实验和知识库全部保留，未提交／推送。见[接入流程与使用](evaluation/results/main_agent_integration_20261022/report.md)、[原文核对](evaluation/results/main_agent_integration_20261022/manual_review.md)、[真实汇总](evaluation/results/main_agent_integration_20261022/smoke_summary.json)、[核验](evaluation/results/main_agent_integration_20261022/verification.json)。

**此前交付（2026-10-22，规划可用性修复）：** 用户授权修复P2.5暴露的回指、非逐字摘录及联合主体规划问题，并要求说明流程。先保存2695个现有文件的哈希和源码基线，原始响应稳定复现3/3失败；补行为回归并看红灯后，修改`agent.py`的绑定、投影、规划提示和循环内一次校验修正；`src/agent_answer.py`明确使用操作需求need确定范围。保留连续原题引文、主体／数据集隔离、分别条件拒绝与原调用预算；未改main、工具／检索算法或知识库。新增15项测试，全部217项离线测试通过、网络尝试0。原12题规划响应离线回放11/12接受，只有b03的非逐字引文仍被正确拒绝。

**本次真实开发回归与剩余边界：** 仅对b02/b03/b06复用原初检做三次新Agent运行，三个规划均一次通过，均完成回答并review_passed，工具行动0。实际15次chat POST、全部stop，输入35697／输出3406／合计39103 token，HTTP失败／usage缺失／自动重试0；首次沙箱socket预检在chat前失败，放行后按冻结方案执行，失败记录保留。本轮b02用一次既有状态修正、一次回答修订；没有真实触发plan_repair，该分支由实际循环入口的离线回归覆盖。按原冻结评分仅1/3严格通过、核心7/9：b03未说明S最短边定义，b06未明确VGG通常省略LRN及配置例外；模型pass不替代这些人工完整性评分。三题已是开发集，不给出新12题分数或泛化收益；旧P2.5结果及失败全部保留。详细[修复流程与结果](evaluation/results/agent_plan_fix_20261022/report.md)、[逐条原文核对](evaluation/results/agent_plan_fix_20261022/manual_review.md)、[汇总](evaluation/results/agent_plan_fix_20261022/summary.json)、[核验](evaluation/results/agent_plan_fix_20261022/verification.json)。生产统一main入口与新留出仍未实施，未提交／推送。

**此前交付（P2.5首轮成对量化，2026-10-21采集／10月22日离线收尾）：** 用户要求先进行P2.5，并希望最终项目有可复核量化数据。本轮在首次模型调用前冻结12道新题（4单篇／6跨篇／2不可答）、27个可答核心点和21处PDF Gold引文；同八篇库、同模型与公开参数，真实固定RAG初检只执行一次，比较原main回答与现有Agent决策／回答层。**实验完成，当前Agent未通过质量收益验收：严格通过固定RAG 10/12（83.33%）、Agent 7/12（58.33%）；可答核心覆盖macro 94.17%／64.17%，正确拒答均2/2。** Agent有3题在规划校验阶段失败（it回指、非逐字片段、联合主体），未交付答案；不能只看成功输出子集。

**本轮成本与范围：** 实际61次chat POST，全部stop，输入112607／输出8790／合计121397 token，HTTP失败与自动重试均0。另一次沙箱socket预检失败发生在chat前，模型请求0；放行后执行同一冻结方案。共享初检12次／8513 token实际只发生一次；路径归因RAG 24次／34470 token，Agent 49次／95440 token（2.769倍），相加须减共享部分。路径中位耗时33.546秒／41.180秒，CPU模型初载另列；非冷启动／并发／P95。Agent共2个工具行动均在b12，最后合理拒答，回答阶段0调用；本批没有可答题通过工具新增证据提高严格通过。共用初检P@10=.1800、nP@10=.8182、Macro Recall=.8417、MAP=.5283、MRR=.6152；不同题集旧分数不作提升对照。

**评分与接续边界：** 同语料新问题，部分知识点与旧题重合，同助手出题／审阅，非第三方盲评。b07的源文表注与正文对指标分母措辞有歧义；b03的S含义、b09的段级beam属于较细冻结要求。主评分完整保留；事后只放宽后两处背景要求为RAG 11/12、Agent 8/12，仍差3题。生产Python、提示、工具、知识库／默认指针和旧实验均未改。10月22日续接只做离线复算、资产核验和交接，无新模型请求。完整[报告](evaluation/results/agent_p25_20261021/report.md)、[逐条原文审阅](evaluation/results/agent_p25_20261021/manual_review.md)、[汇总JSON](evaluation/results/agent_p25_20261021/summary.json)、[冻结评分](evaluation/results/agent_p25_20261021/review_protocol.md)及[项目量化入口](docs/PROJECT_METRICS.md)已保存。下一步先修正规划的自然语言可用性，再统一main入口并另建留出；本次失败题后续仅作开发回归。尚未实施生产修复，未提交／推送。

以上历史P2.5与以下P2.4及更早段落为各轮当时记录；实时状态以顶部Auto收尾记录为准。

**此前交付（2026-10-21，P2.4最终回答与有限复核）：** 用户明确授权先完成P2.4、沿用先说明/最小实现/测试/实测/原文核对/文档交接流程。新增`src/agent_answer.py`：原文生成初稿、逐需求与七维复核、必要时修订一次并再复核；全missing本地列缺口、0请求，partial保留已知与缺口，conflicting不擅自选边。`agent.py`新增`load_answer_case()`和`run_answer()`，重新核对保存输入、同版本原文与状态，回答阶段独立最多4请求；`--answer-from`只续接已有证据，`--max-actions 3 --finalize`串联循环/回答（分别输出loop/answer，总预算6+4=10）。原21个非入口函数AST保持，main.py与工具/检索/旧校验函数原样保留。新增22项测试，全部202项离线测试通过、无网络尝试。

**本轮实测边界：** h10复用此前26段/10198字符证据，回答阶段4次全新模型请求，最终`review_passed`；首次复核将不连续草稿文字用省略号拼成引文，被本地校验拒绝（还提出草稿未引的[16]，原始响应完整保留），一次修订后复核通过。答案为RAG报告EM、Self-RAG按生成内容包含金标准答案判定，分别引用[26]→765、[2]→1003；代码代理逐条原文核对通过，非独立人员盲评。h11缺失Mamba原文，0请求返回`insufficient_evidence`。首次受沙箱限制的连接失败保留在run/h10；明确网络沙箱放行后在新目录network_followup/h10完成，未重写失败日志。本轮客户端尝试5次=本地连接失败1+实际模型请求4；4个真实响应全部stop，报告输入21523、输出1254、合计22777 token；本地失败无usage，不假定上游扣费。无自动重试、没有重跑P2.3。全部失败、初稿、修订稿、复核和出处见[报告](evaluation/results/agent_answer_20261021/report.md)、[原文核对](evaluation/results/agent_answer_20261021/manual_review.md)、[最终答案](evaluation/results/agent_answer_20261021/network_followup/h10/answer.md)、[调用汇总](evaluation/results/agent_answer_20261021/api_usage_summary.json)。该P2.4轮次仍从保存的P1检索输入启动；当时统一main与P2.5尚未实施。P2.5最新结果见本文顶部。

**此前交付（2026-10-20，P2.3有预算循环及已知题优化）：** 用户明确授权加入循环并继续优化。`agent.py --max-actions 3`每题最多3行动/6模型请求/1次状态修正或行动改选，证据仍32段/24000字符；重复、无新证据、预算及answer/stop均有停止条件，前后各读两段。保留原题不含方法名的公共场景；重复或读取区域重叠超过一半时，可按同篇/任务章节元数据改选未读区域，明确记录action_origin和action_overrides；没有硬编码答案或评测ID。新增22项回归，全部180项离线测试通过。已知h10最终轨迹为search→read783→本地规则将重叠的read782改为read763，新增9/4/3段，最终26段/10198字符，读到765的Exact Match原文。一次模型修正后状态合法，最终两项supported、原文/语义核对2/2，停在answer_ready。**这是结合本轮真实响应精确前缀复用的开发回归，不是全部重新调用的盲测；第三步由本地规则选择，最终答案生成及新题泛化仍未验收。** 不同优化阶段累计实际chat9次、全部stop、报告43705 token；成功轨迹6个模型回合27315 token（含5个已发生响应复用），缓存未重复计新请求。全部失败及不采用的查询对照保留，见[循环报告](evaluation/results/agent_loop_20261020/report.md)、[最终轨迹](evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json)、[语义核对](evaluation/results/agent_loop_20261020/manual_review.json)、[调用汇总](evaluation/results/agent_loop_20261020/api_usage_summary.json)。

**此前单次交付（2026-10-20）：** 用户授权先接执行和反馈，再讨论循环。`agent.py`新增`execute_action()`、`merge_evidence()`及`--execute-once`；默认诊断保留，单步最多执行一个工具再检查一次。新增16项测试，当时全部158项通过。真实h10初次新判断跨需求转移PopQA/TriviaQA，被拒绝；回放P2.1已验收行动后search新增10段，反馈先遇HTTP503与断连，用户恢复服务后正常返回但partial/空gap矛盾仍被拒绝。当时尚未实施循环或接受反馈。该轮5次API尝试、3次返回报告8330 token、2次失败无usage，完整[旧报告](evaluation/results/agent_feedback_20261020/report.md)、[原反馈](evaluation/results/agent_feedback_20261020/feedback_raw_model_output.json)及[校验记录](evaluation/results/agent_feedback_20261020/proxy_restarted_result.json)保持原样。

**此前第二步（2026-10-20，P2.2）：** 用户明确授权实现读取邻段。在`src/agent_tools.py`新增`read_neighbors(chunk_id, resources, source, window=1)`：校验当前库ID与精确来源，先限定论文，再按入库顺序读取中心段及前后各一段；window可设0～2，最多5段，首尾截断。保留原文/页码/ID/版本，加offset和读取轨迹。只用已加载的chunks及knowledge_base，不加载模型、不检索或生成答案。新增10项测试，当时全部142项离线测试通过。一次人工已知开发样例使用此前搜索命中的763、显式window=2，得到761～765，共1643字符；原文身份一致，模型/搜索/生成API/网络请求均0。**当时工具尚未连接到Agent执行与反馈，未做h10回答或完整Agent验收。** 当时`agent.py`与`main.py`未改，记录见[报告](evaluation/results/agent_neighbors_20261020/report.md)与[原文结果](evaluation/results/agent_neighbors_20261020/neighbor_result.json)。

**此前第一步（2026-10-20）：** 用户授权先做本地搜索工具。新增`src/agent_tools.py`，显式加载八篇实验库，复用Dense/BM25/RRF/BGE，支持精确论文来源过滤（先过滤再截断）、候选120/返回最多10条，保留原chunk ID、版本、页码与正文。新增9项测试，当时全部132项离线测试通过。另实际执行一次人工指定RAG论文来源的搜索，返回10条、原文身份核对通过；查询沿用P2.1保存的h10绑定文本，生成API/网络请求均0。**该记录不是Agent执行行动或h10回答验收**；当时`agent.py`与`main.py`未修改，邻段工具及工具反馈循环尚未实现。完整[验收报告](evaluation/results/agent_local_search_20261020/report.md)和[结果](evaluation/results/agent_local_search_20261020/search_result.json)保留。

用户要求桌面总览只写预期全流程与小步骤。66行纯路线图及项目内副本本轮保留；旧923行稿在历史目录。当前状态由本文维护，后续先阅读本轮循环代码和开发回归结果；最终生成及新题验证按后续指示推进。

**此前注释补充记录（2026-10-20，在本次搜索工具之前）：** 用户要求解释 Agent 当前形态，并为重要 Python 源码补中文注释。当时覆盖46个Python文件（含14个测试文件）；`agent.py`准确称为“Agent决策原型”，只提出行动建议。新增[代码阅读说明](docs/CODE_READING_GUIDE.md)，当时未实施P2.2。所有执行语句与字符串保留，AST/代码词元/编译检查通过，注释版123项离线测试重新通过，真实项目生成API调用0。注释改变源码文件哈希，旧P2.1目录的同源码续接结论属于历史实测；当前源码不得直接续接旧目录，历史快照/协议/结果保持原样。

P2.1收尾历史记录（发生在本轮注释补充之前）：用户决定**先将P2.1收尾；P2.2留待先询问“本地工具接入是什么、有哪些工具”。** 当时用最新版完整新跑h01/h10/h11的抽取式规划与证据检查，程序3/3、人工语义3/3：h01→answer，h10→RAG missing / Self-RAG supported及绑定search，h11→missing/stop。实际6次新API、9,907 token，均stop、零重试、零工具执行。**P2.1正式完成本次小规模验收；P2.2未开始。** 当时生产代码未改，与前轮123项测试版本一致；该次收尾没有重复运行测试集。

上一轮已完成原四项指标保留、整体归一化 Precision（nP@K）增补和离线报表。现有决定继续生效：按需最多补查两次、候选 120、默认 Top-10，Top-20 保留为显式对照。

**已完成**原查询锚点和补查局部证据保留修复；当前 main 为候选 120、最终 Top-10、按需最多两轮补查。Top-20 已独立量化并保留结果，尚未设为默认。重写与 HyDE 关闭。四项指标全部计算；该离线预算对照新增 API 调用为 0。此前五题快速验收新增6次真实API；此前P1的12题留出另新增24次，34,556 token，全为stop。

先读[本轮P2.1收尾完整日志](evaluation/results/agent_p21_closeout_20261020/report.md)及[人工核对](evaluation/results/agent_p21_closeout_20261020/manual_review.md)。本轮6次是3次新规划+3次新检查，没有复用旧模型输出；完成目录续接新增调用0。此前[范围/状态修正](evaluation/results/agent_scope_fix_20261020/report.md)的7次调用和失败原文完整保留，分轮记账。桌面总览已同步。

先读本文、[原P2第一步](docs/AGENT_STEP1_2026-10-20.md)、[本轮 P1 留出日志](docs/RAG_HOLDOUT_V1_2026-10-20.md)、[快速收尾与基线报告](docs/RAG_QUICK_CLOSEOUT_2026-10-20.md)、[归一化指标与本次进度核对](docs/NORMALIZED_PRECISION_2026-10-20.md)和 [修复 / 预算报告](docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md)，需要旧结论的原话再查 [完整可见对话](docs/chat_history/RAG_2026-10-19_20_完整对话.md)。归档对话仍是上一轮快照，不包含此后的 Precision 讨论；不要重跑整套付费查询或重建索引来“恢复上下文”。

## 2. 用户约束与设备事实

### 回答完整性与修复优先级（2026-10-22，用户确认保留）

完整性以用户明确问题及避免误解所必需的条件为准。优先保证有限成本内稳定交付、重要结论有原文支持、证据不足明确说明；不为已知题背景细节追求满分。

1. **必须修复**：漏掉明确子问题；缺失会改变结论的单位、范围或适用条件；跨论文／数据集混淆；编造事实或引错引用；正常问题无法交付。
2. **按任务补充**：用户要复现实验时所需的定义、参数和步骤，用户要做决策时所需的限制条件。是否必答由任务目的决定。
3. **可以省略**：不影响当前问题理解的背景、例外和延伸信息，不因这些缺失自动判定回答不合格。

b03已回答采样／裁剪／初始化；S的最短边定义对复现有价值。b06已回答LRN收益及内存／时间成本；通常省略LRN属于本题额外架构背景。暂不继续针对这两处调试，进入main接入。原冻结严格1/3、核心7/9完整保留，不能直接当作产品可用性结论。后续新题在运行前区分必答要点与补充信息；不根据结果回改历史主成绩，比较时同时报告事实／引用、核心覆盖、拒答、失败和成本。

**Auto对照后的P1待办（本轮未继续修）：**

- a03 Auto把PDF原文`Arc- Challenge`中的断行空格规范化为`Arc-Challenge`，两次逐字引文检查失败而无交付。需区分可核验的PDF排版规范化与真正改写/非连续拼接，不直接放开证据检查。
- a04的`For A ... and for B ..., ... in each`超过当前紧邻主体投影范围，Agent/Auto均规划失败。需支持原句跨度与各自条件的可靠绑定，避免跨主体/任务混淆。
- a02固定Agent额外公式解释支撑不足，a05有冗余引用。必答点都已回答；问题是已经写出的附加事实/引用应准确，不能以“背景可省略”为由忽略错误。

这些是可用性/正确性问题，与已延期的b03/b06背景遗漏不同。8道新题今后若用于修复即转开发集，原本轮成绩保持；新比较另建独立题集。当前先完成本轮收尾，不自动扩大到P3。

- 默认中文说明；问题题集使用英文。先说明目的、结果和验证边界。讲解 / 下一步讨论不等于实施授权；明确委托执行时在授权范围内完成。
- 保持普通函数、字典、列表及原文件结构；最小改动，不为技术名词增加框架。插件是协作辅助，不是项目运行依赖。
- 后续新增或修改Python代码适量补中文注释，优先说明用途、输入输出、关键取舍和约束，避免只留下大段英文提示而没有流程说明。
- 桌面总览和`docs/PROJECT_WORKFLOW.md`只保留预期流程与小步骤；当前状态、下一步、历史实验与验收证据写入PROGRESS及各轮报告。
- 本机全局规范位于 `~/.codex/AGENTS.md`，本轮实际收到并遵循；无需重复改插件缓存。Matt Pocock / 鼠鼠实习工具按需要使用，不自动同步到 Windows 或普通 ChatGPT。此前已用Karpathy与Matt调试技能；本轮代码实现沿用Karpathy精准改动，没有新增子代理。
- 核心目标是可解释、可复现、有量化证据的科研论文 RAG / Agent 项目，面向大模型应用、RAG、Agent 开发实习，尚未绑定具体 JD。
- **本项目不做 Fine-tuning、LoRA、QLoRA**；不混入独立的 PyTorch Transformer 架构项目。
- MacBook Air + PyCharm 是主开发设备；本机项目 `.venv` Python **3.11.9** 本轮已核对。现有记录没有确认具体芯片和内存，不推断为 M3 或 16GB。
- Windows：用户历史设备 RTX 5060 Laptop GPU、约 8GB 显存，PyCharm、Python 3.11.9。历史本地 Qwen3.5-2B / CUDA 运行记录不冒充本轮 Mac 或 Windows 新实测。
- 当前生成走 API，Embedding / BGE 在 Mac CPU 离线运行；主线不要求额外 NVIDIA GPU。两台电脑不共享进程、虚拟环境、模型缓存或本机代理，`127.0.0.1` 指运行程序所在电脑。
- Git 只同步已提交且推送的内容。当前新增论文、版本、模型缓存、配置与未提交资料不能假定已同步到 GitHub / Windows；本轮没有提交 / 推送授权或操作。
- 保留原有工作、配对索引、题集与实验结果；凭证只保存在本地私有配置 / 环境变量，不进入日志。

## 3. 当前配置、知识库与真实运行范围

| 项目 | 当前值 / 验证边界 |
| --- | --- |
| Embedding | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，CPU、384 维 |
| Reranker | `BAAI/bge-reranker-base`，本机缓存，CPU 离线实测 |
| 每路 Dense / BM25 与 RRF 候选 | `RETRIEVAL_TOP_K=120`、`RRF_TOP_K=120` |
| RRF 秩平滑常数 | `RRF_K=60`，不是候选数 |
| 最终证据 | `RERANK_TOP_K=10`；Top-20 已独立对照 |
| 来源定向补查 | `USE_EVIDENCE_COMPLETION=True`，`main(..., completion_rounds=2)`；按信号触发并可提前停止 |
| 补查候选深度 | 第 1 / 2 轮为 120 / 240，先限定论文再截断；不是固定执行两次 |
| rewrite / HyDE | `USE_MULTI_QUERY=False`、`USE_HYDE=False` |
| 默认知识库 | `semantic-mac-20261019` 三篇库；八篇需显式指定 |
| evaluation | 候选默认120；历史预算对照用Top-10/20，本轮留出直接从main的Top-10计分；CLI补查轮数默认仍为1 |
| 当前真实生成 | 历史P2.5的12题/修复3题/main冒烟2题保留；本轮Auto新8题三路径对照68请求完成，质量收益未通过，非第三方盲测 |


API 私有配置已填写，当前请求路由 `cn:deepseek-v4.1-flash`；此前实际响应报告 `deepseek-v4.1-flash`，标识不能独立证明上游权重。设置为 `thinking.type=disabled`、`temperature=0`、`max_tokens=4096`。此前五题抽测实际完成 6 次 chat 调用、全部 stop，失败 / 自动重试 / 引用修复均为 0；代理报告 11,665 token。当前连通和小样本回答已实际运行，不代表完整语义验收或服务级性能通过。此前离线指标对照仍为零 API 调用。

本轮P1另执行12次新分解+12次新回答，共24个chat POST，全部stop，失败/重试/引用修复为0；代理报告输入32,080、输出2,476、合计34,556 token。受控线程共享CPU模型整轮611.583秒，非冷启动/并发/P95。冻结模型选项与旧配置相同，见[调用与成本](evaluation/results/holdout_v1_20261020/api_usage_summary.json)。

### 知识库版本

| 版本 | 语料 / 数量 | 状态 |
| --- | --- | --- |
| `legacy-3papers-20261019` | 原 Transformer / DCNN / VGG，378 条 | 不重编码的旧配对快照 |
| `semantic-mac-20261019` | 同三篇，378 条、384 维 | **当前激活指针**，Mac 重建对照通过 |
| `arxiv-pilot-5-20261019` | RAG / DPR / ColBERT / Self-RAG / CRAG，88 页、1,019 条 | 独立五篇实验库 |
| `all-papers-8-20261020` | `data` 全部八篇，120 页、1,397 条 | 精确合并三篇 / 五篇的已验证分块及向量，仅重映射位置 ID |

五篇固定版本为 RAG v4 `2005.11401v4`、DPR v3 `2004.04906v3`、ColBERT v2 `2004.12832v2`、Self-RAG v1 `2310.11511v1`、CRAG v3 `2401.15884v3`。原三篇是 Transformer 11 页、DCNN / AlexNet 7 页、VGG 14 页，不含 ResNet。

`data/processed/active_kb.json` 仍选择三篇库。使用八篇库时显式传 `kb_version="all-papers-8-20261020"`；本轮未擅自切换指针。每版 `faiss.index`、`chunks.json`、`manifest.json` 必须成对；位置 ID 不跨库通用，Gold 以 source/page/quote 映射，合并 ID 映射另存。操作见 [版本指南](docs/KNOWLEDGE_BASE_VERSIONS.md)。

### Mac 受控线程

批量线程退出 139 的根因仍未定位；本轮稳定运行继续采用：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python evaluation/results/evidence_retention_20261020/run_comparison.py
```

驱动在首次模型加载前设置 `torch.set_num_threads(1)` 和 `torch.set_num_interop_threads(1)`。上述完整实验已有结果时直接读取，**无需再次执行**。新 Python 进程中的真实 main 问答仍会调用 API。

## 4. 当前流程与已完成的实现

离线：PDF 解析 → Semantic 分块 → MiniLM 归一化向量 → FAISS 配对版本。构建入口 `build_semantic_index.py --version 新版本名` 不覆盖旧版；整体构建，尚无完整增量导入生命周期。默认 `data/raw` 加载只遍历本层 PDF，五篇另在子目录；八篇版本是既有配对资产的精确合并，不能假定默认构建入口会递归重建全部八篇。

在线：API 分解判断（2～4 个有效去重子题）→ 原问题 Dense / BM25 → 保存增强前 RRF 首条锚点 → 可选 rewrite / HyDE 候选融合 → 子题各路检索并合并去重 → 原问题全局 BGE + 子题局部 Top-3 → 预算内选证据 → 按来源覆盖信号最多补查两轮 → 原文 / 标题 / 规则账本 → API 回答 → 引用结构检查、必要时一次修复。

- **锚点固定**：增强前原问题的 RRF 首条不因 rewrite / HyDE 融合而改变。不开增强时该修复不改变原锚点。
- **局部证据保留**：只把初次已入选且属于子题局部 Top-3 的片段记为 `retained_local_ids`；补查后与锚点一起保护，并复用 `select_evidence` 选择原子题和定向补查候选。去掉另一套“先给全局前五”的规则。
- **K 独立**：原 evaluation 每个最终 K 分别选证据、判断覆盖、运行补查，保存 `evidence_completion_by_k`；不能把 20 条前缀当 10 条结果。
- 补查只对能识别两个以上论文来源且有覆盖信号的题触发；单篇题或无信号时跳过。每轮最多四个来源任务，第二轮增加同一批任务的候选深度；没有动态 LLM 语义缺口判定。
- main统一入口已接通：默认mode=rag保留固定流程；mode=agent在共用初检后接`agent.py`原循环/回答，分解1+决策6+回答4上限11。两条路径由调用者选，Agent内部按证据动态选择工具。`agent.py`原诊断／单步／循环／--finalize／--answer-from入口保留。联网、自动路由、LangGraph、UI及修复版独立泛化尚未实施。
- 两个工具及检索算法本轮保持原样。`execute_action()`可补原题公共场景并分别记录模型query/实际effective_query；`merge_evidence()`仍严格核对并保留原文。`neighbor_fallback()`只在重复/重叠时依据已有片段章节、来源和位置改选，未知章节跳过，不按答案词或固定ID定位。所有原校验保留，状态修正由新的模型响应完成。

### 不能丢失的数据 / 算法事实

- Chunk 字段：`chunk_id/text/source/page/title/section`。Embedding 和 BM25 主要索引正文；保留 title 不等于 title 进入向量，BGE / 生成上下文使用标题元数据。
- 构建 Semantic 实参 `max_chunk_size=500` 字符、`percentile=10`；单个超长句不硬切，但短句 / 短片段过滤和跨页断句意味着不保证无损。双栏文件显式指定，尚无通用版式保证。
- FAISS 是归一化向量的 `IndexFlatIP` 精确内积检索，不是 HNSW。论文中提到 HNSW 不等于项目使用 HNSW。
- `RRF_K=60` 是秩平滑常数，与每路候选 120、`RRF_TOP_K=120` 和最终 K 不同。
- 引用检查仅验证编号结构；元数据、来源覆盖、局部 Top-3 和保护规则都不是语义正确的证明。
- API 只接受非空正文且 `finish_reason=stop`，截断 / 其他结束状态显式失败并留档；不隐式回退本地 Qwen，也没有隐藏重试。
- BM25 空有效词项返回空，过滤零分，避免无效 RRF 贡献；纯中文仍可走 Dense，英文 / 数字分词不代表中文 BM25 已完善。

## 5. 当前检索指标与归一化结果

此前保存的八篇库42道英文可答题，候选120、关闭 rewrite / HyDE、按需最多补查两轮：

| 最终预算 | Precision | nP（整体） | Recall（宏平均） | MAP | MRR | 全部 Gold 入选 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-10 | 0.1310 | 0.6790 | 0.7679 | 0.4837 | 0.5708 | 28/42 |
| Top-20 | 0.0714 | 0.7407 | 0.8115 | 0.4857 | 0.5727 | 30/42 |

新字段 `normalized_precision`：逐题为 `H/min(K,G)`，汇总为 `sum(H)/sum(min(K,G))`，汇总不能直接平均逐题归一化分数。H 是前 K 条中去重后的 Gold 命中数，G 为该题去重后的 Gold 数；无 Gold 题跳过，无可计分题时返回 None。原四项字段和计算口径保留。

42 题 Gold 数按题相加为 81，所有 G≤8；原平均 P@10 / P@20 的理论上限为 .192857 / .096429。实际合计命中 55 / 60，因此整体 nP 为 55/81=.679012、60/81=.740741，在本题集等于 Micro Recall。原 Recall 是逐题平均的 Macro Recall；逐题归一化再平均在本题集会得到原 Recall，不能混作整体 nP。若以后某题 G>K，nP 分母按 K 截断，与普通 Recall 不再相同。

新列只重新表达预算内指定 Gold 的完成程度，不代表检索改善、全部上下文的有用比例或回答正确率。完整各方法、旧 / 新题与单篇 / 跨篇结果见 [补充报表](evaluation/results/normalized_precision_20261020/report.md)及同目录 JSON；历史原始结果未覆盖。

Precision 分母随 K 变化，Top-20 下降需要结合 Recall、MAP、MRR 和完整覆盖判断；不是只选 Recall 最大的一组。Gold 为非穷尽原文标注，不等于所有其他段落无用。上下文字符长度只是成本代理，不是实际 token 账单或服务 P95。

Top-20 的 Recall 增加 **4.37 个百分点**、完整 Gold 由 28/42 增至 30/42，MAP / MRR 略增；完整上下文字符比值中位数为 **1.92**。本轮开始前设定 Recall 至少增加 5 个百分点才把默认提高为 20，因此保持 10。此门槛是本轮的工程预算选择，不是通用统计结论；偏重召回时可显式使用 20。候选 120 按用户决定保留，但修复后候选 60 的 Top-10 Recall 同为 .7679、MAP / MRR 更高，不能说候选越大越好。

### 本轮新增12题留出结果（不与旧42题作提升对照）

前10道可答题Gold按题累计25条，命中18条；整体nP@10=.7200，P=.1800，宏Recall=.7900，MAP=.5337，MRR=.7833，全部Gold入选6/10。单篇nP=.8750 / 宏Recall=.8750，跨篇nP=.6471 / 宏Recall=.7333。h11/h12无Gold，跳过检索计分。

严格完整核心点19/27，逐题覆盖宏平均70.0%；partial/missing/wrong不计完整覆盖。可答题严格通过4/10（单篇2/4、跨篇2/6），两题拒答内容2/2正确，但h12附带真实VGG数值未引用，含引用要求的总体严格通过5/12。41个已表达重要断言可由原文/语料边界核验支持；引用结构12/12不等于内容完整或引用语义全部通过。

h02粒度Gold1279初始漏召；h08/09部分Gold在候选却未入最终预算；h10分解把PopQA错套到RAG，Gold765补查后在候选却未留下，未完成指标比较。h04/05证据已齐但省略细节；h07/08有多余保留措辞。均不修复、不调参。细项与严格计分理由见[本轮报告](evaluation/results/holdout_v1_20261020/report.md)。同语料由本助手出题/审阅，不是独立第三方盲评；后续若据此优化则改称开发集并另建留出。

### P2第一步首轮记录：已实现，当时语义验收2/3

独立agent.py只做需求与证据诊断；规划模型只收问题，检查模型收生成的需求、P1原始片段和完整八篇目录，旧答案/Gold/评审标准不输入。三题原文12/10/10段，按配对版本/hash/ID/source/page/text核对，不重新检索或生成最终回答。

h01三项需求均supported，建议answer；h11三项missing，Mamba来源缺失，建议stop；h10识别RAG判据缺口及Self-RAG包含式判据，但r3将PopQA扩展到RAG，查询延续错误，且训练损失被过宽算作判据partial支持。结构和原句校验虽3/3，人工语义只2/3；未执行错误查询。原12题后续作诊断/回归，本轮三题已明确用于开发，最终独立验收另冻新题。

实际6次API（3规划+3检查），输入7850、输出1934、总9784 token，全部stop，失败/本地自动重试0。三题程序耗时合计16.983秒，没有实际检索和最终生成，不能与P1完整main耗时比较。完成目录再次进入新增调用0。[完整日志](evaluation/results/agent_step1_20261020/report.md)、[人工核对](evaluation/results/agent_step1_20261020/manual_review.md)。

### P2.1 范围/状态修正（前轮记录）

操作need由原题片段生成，不接受模型自由转述；单主体回指可在唯一先行词下扩展，多主体/不明时拒绝。检查器只见绑定需求、预计算查询、原文和完整目录；原完整比较题不再作为事实检查输入。supported_part须说明真实支持部分；跨项缺口/条件被拦，显式比较允许提另一方法但不转移数据集。搜索一次只指向一个未满足需求并复制绑定文本。

本轮最终123项测试通过，禁止网络。总计7次API、输入11663/输出1841/总13504 token、均stop；初始5次与第6次失败留档，第7次状态正确但被过严比较校验误拦，最后仅改本地校验并精确同提示回放通过，新增调用0。h10定向状态为missing/supported；source=null建议尚未执行。h01仅本地回指绑定回归，h11为本轮首轮真实stop及最终校验回放；新版抽取式规划的完整三题未新跑，不声称完整Agent或检索/回答分数提升。详见[完整报告](evaluation/results/agent_scope_fix_20261020/report.md)、[123项测试](evaluation/results/agent_scope_fix_20261020/tests_final.log)、[精确回放](evaluation/results/agent_scope_fix_20261020/accepted_h10_replay.json)。

### P2.1 三题完整链路收尾（最新，已完成）

新版真实规划到检查已完整跑完h01/h10/h11，程序3/3、人工语义3/3。h01数值与指标方向支持明确；h10不转移PopQA/TriviaQA且训练损失不算判据支持；h11缺Mamba原文合理stop。实际6次API、输入8886/输出1021/总9907 token，全部stop；代码未改、未复用旧规划或检查，未执行工具。四处原句及来源/页码校验通过，完成目录续接新增0次。

h01的“the paper”回指、h10的source=null和重复查询片段作为非阻塞瑕疵保留，不声称来源路由或检索已验收。123项测试是此前通过且源码一致的记录，本轮未重跑。P2.1小规模收尾完成；完整Agent/独立泛化仍未验收，P2.2未开始，下一次先按用户提问讲解工具范围。详见[收尾报告](evaluation/results/agent_p21_closeout_20261020/report.md)。

## 6. 验证记录与仍未验收的内容

- P2首轮全部99项unittest通过（原79+新增20），测试禁止网络；覆盖虚构引文、错误ID、越界动作、预算、失败保存和中断续接。1,986项旧输入运行前后hash一致，main/索引/激活指针/旧题和结果保留。6次真实调用独立审计，10处引文存在性通过但h10语义未通过。发布仅更新旧README/PROGRESS，并新增代码/测试/日志。

- 本轮P1：12/12真实main成功，24个实际chat POST逐次审计与逐题记录相互一致；25条Gold及2条边界引文先核对PDF再冻结，冻结时间早于首个chat；1,277项旧输入运行前后哈希相同。直接从本次selected_ids用独立公式复算10题×5项检索指标；来源/页码/全文与chunk匹配。新增准备/驱动/离线审阅脚本通过语法检查；生产代码未改，79项测试为历史记录，本轮未重跑。发布仅更新已有README/PROGRESS并新增题集和日志。

- 此前五题快速收尾：q2 / p3 核心完整；n07 部分回答；a12 分别事实正确但过度拒绝比较；n11 正确拒绝编造 P95 延迟。五题真实 main 检索 / 重排与最终回答均执行，四题分解复用已有真实 API 缓存，n11 分解实时生成。引用结构 5/5，四道可答题的入选 ID 与现有最终离线结果全部一致。生产代码和数据未改，79 项测试是上一轮通过的记录，本次未重复运行。
- 该五题收尾新增 API 6 次、报告 11,665 token；49 项源码 / 资产输入哈希在运行前后保持一致。源码快照、答案、原文、调用审计和两项跨篇瑕疵均保存于 `evaluation/results/quick_closeout_20261020/`；这次收尾按用户决定完成，不把语义瑕疵隐藏为全部通过。

- 此前归一化补充：全部 **79 项 unittest** 通过（原 68 项及新增 11 项）；新增检查覆盖整体 / 逐题聚合差异、G>K、无 Gold、重复 ID、CLI JSON 输出、报表拒绝覆盖和旧指标一致性。测试禁止网络连接，无模型生成或 API 调用。
- 只读取保存的四组选择 / 候选对照，复核 **3,696 条逐题记录和 880 条分组汇总**；补充 nP 列，原 Precision / Recall / MAP / MRR、Gold 与入选 ID 均保留。当前配置、四版知识库配对文件哈希、激活指针及九项迁移清单另行核对；结果见新目录的 `verification.json` / `progress_audit.json`。

- 上一轮锚点 / 保留修复：先在旧代码上建立四个失败回归测试，再修复；当时全部 **68 项 unittest** 通过，红灯 / 绿灯原始输出保留。
- 原 `run_evaluation` CLI 完成 42 题 × 修复前后 × 候选 60/120 × 独立 K=10/20；所有方法保存 Precision、Recall、AP/RR，汇总 MAP/MRR。4 道无 Gold 题跳过，未伪造为 0 分。
- 独立脚本重新由原文映射 Gold，并复算 **3,844 组方法/K/题记录的四项指标**（主对照 3,696 组，加增强和三篇入口检查）；分组均值也一致。
- `main.main` 真实检索 / 重排 / 上下文回放 **8 次**，p1 含 rewrite + HyDE 的两种 K，选中 ID 均与 evaluation 对齐；最终回答显式替身，不能称为真实回答成功。
- 当前仍激活的三篇库，通过五道题、候选 120、两种 K、最多两轮的实际 evaluation CLI；原三篇/五篇/八篇资产哈希及 9 项迁移清单一致。
- 原 60 / Top-10 共有方法逐题复现上一轮；全部被标记的局部证据在补查各轮保留，API 调用计数为 **0**，凭证未进入导出产物。
- 主对照耗时约 **20.6 分钟**，共享重排缓存，不能作为单请求延迟或服务基准。

- 新预算下Top-10已有此前五题抽测及本轮12题留出真实记录，但 Top-20 生成、独立盲测、并发 P95 与大规模语义效果仍未验证。此前八次 main 回答保留为旧参数历史；本次 n07 仍部分回答，a12 已取到两篇关键原文但末段拒绝比较，不沿用旧“DPR 原文未选中”的解释。
- 原数据、题目、Gold、旧结果、配对索引及私有配置保留；日志脱敏。默认库指针仍三篇，完整八篇需显式指定。
- 来源别名仍不能把 Transformer 简称映射到 `Attention is all you need.pdf`（a09/a15），本轮未改题 / 改标注解决它。
- 复用的 p4 旧分解因五个子题被拒绝，沿用原状态，没有再花 API 重生成。n08 原题条件归属有歧义，保留原题与 Gold。
- 保护可能保留不正确的局部候选；候选 120 会改变首次局部排序。修复不承诺所有 Gold 进入 Top-K，也不代表语义充分。

## 7. 历史实验索引与结论

| 工作 | 可信结论 / 边界 | 报告 |
| --- | --- | --- |
| 保持风格清理 / 早期 API 调试 | 保持普通函数结构；六题与固定证据调试，仍有绝对化措辞问题 | [清理](docs/CLEANUP_LOG_2026-10-18.md)、[DeepSeek 调试](docs/DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md) |
| rewrite / HyDE 与本地 Qwen 对照 | 三篇库三题四条件；增强输出来自 API，本地 Qwen 仅回放最终提示；不是本地生成的增强实验 | [三篇模型 / 增强对照](docs/REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md) |
| Mac 迁移 / 版本配对 | 离线检索、BGE CPU、三题真实 API；版本切换 / 回退已实测 | [Mac 审计](docs/MAC_AUDIT_2026-10-19.md)、[版本指南](docs/KNOWLEDGE_BASE_VERSIONS.md) |
| 五篇下载 / 先导 | 固定版本、幂等下载 / 失败重跑；不等于通用导入阶段完成 | [先导](docs/ARXIV_PILOT_2026-10-19.md)、[选题](docs/ARXIV_PILOT_SELECTION_2026-10-19.md) |
| 分解 / 证据选择修复 | 2～4 子题、局部 Top-3、标题、拒答修正；部分措辞精度仍有限 | [修复与 evaluation](docs/DECOMPOSITION_EVALUATION_2026-10-19.md) |
| 英文六题 / Top-K | 开发六题指定 Gold 全覆盖，排序仍靠后；不能宣称泛化满分 | [原量化](docs/RETRIEVAL_EVALUATION_2026-10-19.md)、[英文优化](docs/RETRIEVAL_OPTIMIZATION_2026-10-19.md) |
| 新十二题 / 模型知识对照 | 十道计分题 Recall .4833，跨篇 .2222；oracle 原文不是实际检索成功，两个排序候选未采用 | [独立新题与有限优化](docs/INDEPENDENT_VALIDATION_2026-10-19.md) |
| 一轮 / 三轮补查 | 有局部收益与旧题退步；三轮未超一轮，轮数与候选深度一起变 | [一轮](docs/EVIDENCE_COMPLETION_2026-10-19.md)、[三轮](docs/COMPLETION_ROUNDS_2026-10-19.md) |
| 全部八篇与增强 / 两轮 | 42 题：原 .7361/.4899，全部增强 + 两轮 .7242/.4797；8 次真实问答未补足两题 | [八篇完整评估](docs/ALL_PAPERS_EVALUATION_2026-10-20.md) |
| 本轮锚点 / 保留 / 预算 | 用户接受两轮，候选 120，独立比较 10 / 20，四项指标及交接完整留档 | [最新修复与预算](docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md) |
| 整体归一化 Precision 与进度核对 | 当前 Top-10 / 20 nP 为 .6790 / .7407；原四项及检索结果保留，79 项测试通过 | [归一化补充](docs/NORMALIZED_PRECISION_2026-10-20.md) |
| P2第一步需求/证据诊断 | 程序3/3、人工语义2/3；99测试；6次API、9784 token；h10范围错误保留 | [P2第一步](docs/AGENT_STEP1_2026-10-20.md) |
| P2.1范围/状态修正 | 123测试；7次API、13504 token；h10定向同提示回放通过，当时新规划完整链待验收 | [修正日志](docs/AGENT_SCOPE_FIX_2026-10-20.md) |
| P2.1完整链路收尾 | 3次新规划+3次新检查；人工3/3；6次API、9907 token；阶段完成，P2.2未开始 | [收尾日志](docs/AGENT_P21_CLOSEOUT_2026-10-20.md) |
| P1新12题留出基线 | P=.18、nP=.72、宏R=.79；严格完整核心点macro70%，可答严格4/10，拒答内容2/2 | [本轮留出](docs/RAG_HOLDOUT_V1_2026-10-20.md) |
| 五题快速收尾与本地冻结 | 真实 chat 6 次；单篇两题核心完整、跨篇瑕疵保留、不可答题合理拒答 | [快速收尾](docs/RAG_QUICK_CLOSEOUT_2026-10-20.md) |

历史“默认关闭”结论保留在对应报告中；当前用户选择与实际开关以本文件第 1～3 节为准，不把旧报告重写成新结论。

## 8. 新对话的下一步

本轮Auto实现、8题三路径对照及交接已收尾；功能范围完成，稳定性/质量收益未通过。当前CLI默认auto，Python函数默认rag。恢复上下文直接读Auto报告/summary与失败轨迹，不重跑68次付费调用；历史P2.5、规划修复和main冒烟分轮保留。下一轮若继续，先处理第2节P1阻塞，再评估P3；本轮没有P3实现。桌面总览保持纯路线图，P0通用增量导入增强继续延期。

1. **P0基础导入：完成**。新增五篇已下载、校验、建独立库并合并；原三篇与版本回退保留。通用身份去重/完整增量生命周期等增强延期，不是本轮待做步骤。
2. **P1小规模留出基线：完成**。本轮新12题、PDF Gold/评分冻结、真实main、检索指标与语义/拒答/成本审阅完成；质量瑕疵留档。不是第三方盲评或大规模泛化验证。其中h01/h10/h11现已用于P2开发诊断；后续用已知题优化时按开发/回归集处理，最终验收另建新留出。
3. **P2.1：完成约定小规模验收**。当时完整运行h01/h10/h11规划与检查，程序/人工均3/3；6次新API、9907 token。诊断模式仍只保存建议；旧快照与失败原样保留。
4. **P2.2：搜索与邻段工具完成独立验收**。当时9项搜索测试及10项邻段测试，全部142项离线测试通过；真实工具原文身份检查通过，生成API0。手动工具样例和h10答题验收分开理解。
5. **P2.3：有预算循环及已知h10回归完成**。新增22项回归、全部180项通过。已知案例最终3行动、6逻辑模型回合，修正1次，原文支持两项需求并answer_ready。区域兜底为本地规则、真实响应前缀精确复用和新最终反馈均在日志中区分；开发阶段累计9次真实chat/43705 token。后续可检查更多题及边界，再按用户指示进入P2.4最终生成/复核；P2.5同条件对照与新留出尚未实施，不把本例推广为总体收益。
6. **P2.4：实现及约定小规模验收完成**。新增回答模块、入口串接与22项测试，全部202项通过。h10续接旧证据、4次新生成/复核22777 token后通过，首次复核非法引文与单次修订均保留；h11全缺失0请求拒答。回答阶段最多4请求；失败草稿不直接交付，不自动重试网络失败。模型复核不是正确性保证，验收为代码代理原文审阅，不是独立盲评。
7. **P2.5首轮实验：完成；质量收益验收未通过**。12道新题同条件共用真实初检，RAG／Agent严格通过10／7题，可答核心覆盖macro94.17%／64.17%，正确拒答均2/2；实际61请求／121397 token。3题Agent规划失败全部计入分母；冻结评分及敏感性分析保留。本轮未修改生产算法，不根据本批结果调参。
8. **规划修复及三题开发回归：完成**。回指／联合主体按保守规则绑定，伪造连续引文仍拒绝，max-actions内规划可占用原来的一次校验修正额度。全部217测试通过；本轮15新请求／39103 token，三题交付3/3、冻结严格1/3，剩余细节遗漏如实保留。随后main真实问题入口已接通，保留固定RAG路径；后续另建新留出，不得把本三题调试后结果拼成新12题分数。原P2.5驱动与本次生产入口接入分轮记账。
9. **main接入：完成**。当时显式rag/agent，230项离线测试通过，两题真实CLI合计8请求/13631 token。此历史冒烟没有自动路由，不重写成Auto验证。
10. **Auto实现与本次对照：收尾完成，稳定性/收益未通过。** 239项测试；新8题三路径必答交付8/7/6，68实际请求/149573 token。4直答/1补查/1停止/2失败；保留复杂语句绑定和排版误阻塞P1，当前不再针对这批题调参。入口设计和失败均可复核，不能声称Agent/Auto比RAG更准。
11. **P3/P4：后续按需，当前未开始。** 先解决正常问题交付与事实/引用问题，再决定联网证据、必要编排与演示UI；不为工具数量扩展项目。

有 arXiv、小批量免费接口的历史调研，但不把旧报告中的价格 / 限速当成永久当前事实；选服务前重新核对。当前主线无需先采购 GPU 或引入微调。

## 9. 文件与复现入口

- [Auto设计及每项作用](evaluation/results/auto_closeout_20261022/design.md)、[收尾报告](evaluation/results/auto_closeout_20261022/report.md)、[冻结题及必答/补充](evaluation/results/auto_closeout_20261022/questions_frozen.json)、[逐题审阅](evaluation/results/auto_closeout_20261022/manual_review.md)、[量化JSON](evaluation/results/auto_closeout_20261022/summary.json)、[68次实际调用](evaluation/results/auto_closeout_20261022/actual_chat_calls.json)、[239项测试](evaluation/results/auto_closeout_20261022/tests_final.log)。已完成，不为恢复上下文重跑API；可执行同目录summarize.py离线复算。
- [main接入与选择机制](evaluation/results/main_agent_integration_20261022/report.md)、[230项测试](evaluation/results/main_agent_integration_20261022/all_tests.log)、[实际命令行结果](evaluation/results/main_agent_integration_20261022/smoke_summary.json)、[原文核对](evaluation/results/main_agent_integration_20261022/manual_review.md)、[最终核验](evaluation/results/main_agent_integration_20261022/verification.json)。从新问题运行`.venv/bin/python main.py --mode agent`，默认logs/agent_runs/留档；查看结果不产生模型请求。
- [规划修复流程与三题回归](evaluation/results/agent_plan_fix_20261022/report.md)、[原文审阅](evaluation/results/agent_plan_fix_20261022/manual_review.md)、[15次真实调用](evaluation/results/agent_plan_fix_20261022/actual_chat_calls.json)、[217项测试](evaluation/results/agent_plan_fix_20261022/all_tests_final.log)、[最终核验](evaluation/results/agent_plan_fix_20261022/verification.json)。本轮是生产规划修复与开发回归，不是原P2.5实验重跑或新留出。
- [P2.5成对量化报告](evaluation/results/agent_p25_20261021/report.md)、[冻结题集](evaluation/results/agent_p25_20261021/questions_frozen.json)、[逐条原文审阅](evaluation/results/agent_p25_20261021/manual_review.md)、[成本与质量JSON](evaluation/results/agent_p25_20261021/summary.json)、[最终核验](evaluation/results/agent_p25_20261021/verification.json)、[项目量化入口](docs/PROJECT_METRICS.md)。61次实际调用已完成；额度恢复后只读记录，无需再次调用API。
- [P2.4回答与复核报告](evaluation/results/agent_answer_20261021/report.md)、[最终答案](evaluation/results/agent_answer_20261021/network_followup/h10/answer.md)、[逐条原文核对](evaluation/results/agent_answer_20261021/manual_review.md)、[202项测试](evaluation/results/agent_answer_20261021/tests.json)、[调用汇总](evaluation/results/agent_answer_20261021/api_usage_summary.json)、[保护与源码检查](evaluation/results/agent_answer_20261021/verification.json)。新增实现为`src/agent_answer.py`，阅读顺序见`docs/CODE_READING_GUIDE.md`的P2.4段落。首轮连接失败和成功网络续接分目录保留，勿覆写旧协议或为恢复上下文重复请求。
- [P2.3循环与优化报告](evaluation/results/agent_loop_20261020/report.md)、[最终完整轨迹](evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json)、[语义与原句核对](evaluation/results/agent_loop_20261020/manual_review.json)、[180项测试](evaluation/results/agent_loop_20261020/tests.json)、[9次真实调用汇总](evaluation/results/agent_loop_20261020/api_usage_summary.json)、[资产与源码核对](evaluation/results/agent_loop_20261020/verification.json)。首轮重复行动、改选后状态错误、公共场景对照及区域修复全保留；不要为恢复上下文重跑付费步骤。
- [P2.3单次执行与反馈报告](evaluation/results/agent_feedback_20261020/report.md)、[模型反馈原文](evaluation/results/agent_feedback_20261020/feedback_raw_model_output.json)、[最新校验结果](evaluation/results/agent_feedback_20261020/proxy_restarted_result.json)、[158项测试](evaluation/results/agent_feedback_20261020/tests.json)、[调用汇总](evaluation/results/agent_feedback_20261020/api_usage_summary.json)、[资产保护核对](evaluation/results/agent_feedback_20261020/verification.json)。该目录同时保留初次跨需求失败、HTTP503、断连和人工续接记录，不重跑恢复上下文。
- [P2.2第二步邻段读取验收](evaluation/results/agent_neighbors_20261020/report.md)、[真实返回原文](evaluation/results/agent_neighbors_20261020/neighbor_result.json)、[读取与调用统计](evaluation/results/agent_neighbors_20261020/smoke_summary.json)、[142项测试](evaluation/results/agent_neighbors_20261020/tests.json)、[资产保护核对](evaluation/results/agent_neighbors_20261020/verification.json)。
- [P2.2第一步本地搜索验收](evaluation/results/agent_local_search_20261020/report.md)、[真实返回原文](evaluation/results/agent_local_search_20261020/search_result.json)、[本次调用及耗时](evaluation/results/agent_local_search_20261020/smoke_summary.json)、[132项测试](evaluation/results/agent_local_search_20261020/tests.json)、[资产保护核对](evaluation/results/agent_local_search_20261020/verification.json)。
- [预期全流程路线图](docs/PROJECT_WORKFLOW.md)、[桌面旧总览备份](docs/history/DESKTOP_WORKFLOW_BEFORE_SIMPLIFY_2026-10-20.md)；路线图不承载实时进度。
- [本轮P2.1收尾完整MD](evaluation/results/agent_p21_closeout_20261020/report.md)、[人工核对](evaluation/results/agent_p21_closeout_20261020/manual_review.md)、[6次真实调用](evaluation/results/agent_p21_closeout_20261020/run/actual_chat_calls.json)、[验证](evaluation/results/agent_p21_closeout_20261020/verification.json)。
- [前轮范围/状态修正完整MD](evaluation/results/agent_scope_fix_20261020/report.md)、[人工核对](evaluation/results/agent_scope_fix_20261020/manual_review.md)、[123测试](evaluation/results/agent_scope_fix_20261020/tests_final.log)、[离线核验](evaluation/results/agent_scope_fix_20261020/verification.json)。
- [原P2第一步完整MD日志](evaluation/results/agent_step1_20261020/report.md)、[逐题人工核对](evaluation/results/agent_step1_20261020/manual_review.md)、[新入口](agent.py)、[99项测试日志](evaluation/results/agent_step1_20261020/full_tests.log)、[调用汇总](evaluation/results/agent_step1_20261020/run/summary.json)。同目录run/含三题完整JSON、输入、协议和调用；不重复付费调用恢复上下文。

- [本轮P1留出Markdown日志](evaluation/results/holdout_v1_20261020/report.md)、[逐题人工审阅](evaluation/results/holdout_v1_20261020/manual_review.md)、[正式新题/Gold](evaluation/holdout_v1_questions_en.json)、[冻结评分规则](evaluation/holdout_v1_review_protocol.md)、[运行后核对](evaluation/results/holdout_v1_20261020/verification_after_run.json)、[真实调用汇总](evaluation/results/holdout_v1_20261020/run_summary.json)。原始答案、提示、分解、排序追踪、调用与源码快照都在同目录，无需再次调用API恢复上下文。

- [本次五题快速收尾](evaluation/results/quick_closeout_20261020/report.md)、[人工语义核对](evaluation/results/quick_closeout_20261020/manual_review.json)、[运行 / 资产核对](evaluation/results/quick_closeout_20261020/verification.json)、[真实调用汇总](evaluation/results/quick_closeout_20261020/run_summary.json)。同目录 `source_snapshot/` 为验收时本地源码快照，未提交或推送；完整会话归档仍是此前快照。

- [归一化补充报表](evaluation/results/normalized_precision_20261020/report.md)、[完整新增指标 JSON](evaluation/results/normalized_precision_20261020/report.json)、[独立复核](evaluation/results/normalized_precision_20261020/verification.json)、[当前配置与资产核对](evaluation/results/normalized_precision_20261020/progress_audit.json)。
- [最新原始结果目录](evaluation/results/evidence_retention_20261020/comparison.json)、[独立复核](evaluation/results/evidence_retention_20261020/verification.json)、[预算采用依据](evaluation/results/evidence_retention_20261020/adoption.json)。
- [本次可见对话](docs/chat_history/RAG_2026-10-19_20_完整对话.md)、[工具记录压缩包](docs/chat_history/RAG_2026-10-19_20_tools.jsonl.gz)、[导出清单](docs/chat_history/RAG_2026-10-19_20_export_manifest.json)。
- [重写前完整 PROGRESS](docs/history/PROGRESS_BEFORE_RETENTION_2026-10-20.md) 保留原长期路线和全部阶段记录；[旧实验归档说明](docs/history/README.md)。
- `main.py` 问答；`build_semantic_index.py` 离线构建；`src/knowledge_base.py` 成对版本；`src/evidence_gap.py` 有界补查；`evaluation/run_evaluation.py` 原四项检索指标及整体 nP；`evaluation/summarize_normalized_precision.py` 只读取已有日志生成补充报表；`evaluation/run_answer_evaluation.py` 回答与引用检查。

仅重建归一化补充报表，不加载模型或调用 API（须使用新输出目录）：

```bash
python -m evaluation.summarize_normalized_precision \
  --output-dir evaluation/results/new_normalized_precision
```

直接运行 evaluation 默认会生成辅助查询；离线复评必须提供 `--auxiliary-cache`。`--no-auxiliary` 也可避免 API，但会禁用分解 / 改写，不能冒充同分解对照。

如确需重跑量化，以下使用已有辅助查询、不会新调用 API，但会消耗本机 CPU；请使用新的结果目录：

```bash
python -m evaluation.run_evaluation \
  --questions evaluation/all_papers_questions_en.json \
  --kb-version all-papers-8-20261020 \
  --candidate-k 120 --top-k 10 20 \
  --complete-evidence --completion-rounds 2 \
  --auxiliary-cache evaluation/results/all_papers_20261020/auxiliary.json \
  --output-dir evaluation/results/new_retention_replay
```

Mac 仍应使用前述受控线程环境 / Python 设置。已有完整结果无需重复计算；源码变更后再运行 `python -m unittest discover -s tests -v` 做相应回归。
