# 代码阅读说明与 Agent 当前边界

更新：2026-10-24（Asia/Shanghai）。当前保存的回归为345项后端与27项网页通过；中文比较、回答语言及JSON代码块兼容已修复，网页支持独立配对版本和PDF入库。完整现状以[PROGRESS](../PROGRESS.md)为准，[分版本结果](PROJECT_METRICS.md)区分历史失败与当前开发回归。下文按阶段保留实现演进和旧运行证据，不把旧测试数量或当时限制当成今天的状态。

## 1. 当前做出了什么

当前已实现 **有预算工具循环及最终回答复核**；默认保留P2.1诊断模式，`--execute-once`为单步，`--max-actions 3`为循环；加`--finalize`后接回答，`--answer-from`可独立复用保存的证据。代码仍由普通函数、字典和列表组成。

它可以选择行动、执行工具、合并原文，再判断是否继续；Agent回答逐项复核并有限修订。main支持rag/agent/auto，CLI默认auto，函数默认rag。最终Auto先走原RAG生成/引用修复，只有明确缺口或引用失败才进入Agent，普通路径没有额外门控API。反馈修复前251测试；a03/a04Auto开发回归直答、部分Agent阻塞改善，h10升级仍degraded；历史8题8/7/6及P2.5的10/12与7/12保持原版本边界。功能数量和是否使用`Agent`类不构成采用理由。

| 文件 | 已实现的职责 | 谁决定下一步 |
| --- | --- | --- |
| `main.py` | CLI默认RAG优先Auto，函数默认RAG；三模式共用初检 | Auto先检查原RAG回答的明确缺口/引用状态，再按需升级；Agent内部模型选行动 |
| `src/evidence_gap.py` | 按来源覆盖和局部片段入选信号，实际补检索并重新选择证据 | 固定规则；不使用 LLM 判断具体事实是否已有支持 |
| `agent.py` | 抽取需求、检查原文，单步或有限循环执行本地工具 | LLM提出建议，本地校验/预算约束执行；有记录的章节规则可改选重复或重叠行动 |
| `src/agent_tools.py` | 搜索所选配对库（默认八篇）、读取同篇论文邻段，返回真实原文和轨迹 | 普通函数执行，由`agent.py`的执行入口分派 |
| `src/agent_answer.py` | 生成答案、逐项复核、最多修订一次；全缺失时直接说明缺口 | 模型判断内容，本地严格核对复核结构与逐字引文，预算约束执行 |
| `src/arxiv_tools.py` | arXiv题录搜索、固定版本PDF读取与原文保存 | 普通函数执行有预算GET，题录不作为回答证据 |
| `src/arxiv_evidence.py` | 本地缺源后路由/选论文、原文选段登记、复用检查与回答复核 | LLM仅在三个决策点提建议，Python核对来源、原文和预算 |
| `src/answer_language.py` / `src/model_json.py` | 程序固定提示的中英选择、回答语言规则；只剥整段JSON代码块 | 普通函数；不替代各处字段校验 |
| `webui/server.py` / `webui/library.py` | 网页worker、公开字段/配置接口；上传、独立库指针和配对版本发布 | 本机服务调度，问答仍调用main |

`agent.py`并非只做补查：它判断能否回答、应否停止及是否适合读邻段。默认模式保存建议，单步模式执行一次，循环模式最多执行三次；固定RAG的原有补查仍来自`main.py`调用的`evidence_gap.py`。

## main新问题入口怎么读

1. `main()`函数默认rag、CLI默认auto。原Agent分解/决策/回答上限1/6/4=11；Auto另加probe2，最坏13。显式`allow_network=True`另加最多3次network决策，分别为14/16。全程预写账本，不重置循环预算。
2. `_run_pipeline()`共用原分解、混合检索、重排和规则补查。固定Agent不先生成RAG草稿；Auto的草稿在`_answer_with_agent()`内生成，原检索与五个辅助函数保持。
3. `_answer_with_agent()`的Auto分支先调用原build_prompt/repair_citations_once，记录probe.json；无缺口则direct，Agent调用0。有明确缺口/引用失败则先写routing.json，再运行既有独立规划/判断和工具循环，最后原回答复核；草稿不进入Agent白名单。
4. 循环失败时仅引用结构合格的初稿可标degraded保留；失败记录不抹掉，CLI非零。没有有效初稿则failed。原route_only暂停能力作为既有函数接口保留，最终Auto不依赖它；未采用的combined gate已删除。
5. `cli()`支持三模式、版本、空审计目录及可选问题。Auto/Agent默认八篇，也可显式选合法配对库，不切指针；网页提交时固定自己的版本。日志在logs/auto_runs或agent_runs，原目录不重跑。
6. `--allow-network`将本地正常`model_stop`接到`run_arxiv_followup()`，不改原本地动作协议。证据已齐、明确主论文已在库或未开启时不做arXiv GET；最终答案仍复用原复核。独立`agent.py`诊断入口不会因此自动联网。
7. 外部传输失败保持network.failed及工具轨迹，`_answer_with_agent()`交付有限本地结果并标degraded/source_unavailable。全部missing时零回答调用；部分支持仍复用`run_answer()`，其`source_unavailable=True`将回答输入的未完成缺口改为尚未核实，原loop判断保留。来源/版本/引文校验错误不走临时网络降级。
8. `_record_call()`共用调用审计，`_finish_result()`补齐三模式的状态、答案/说明、证据、行动、停止原因和成本。运行时异常返回failed，CLI非零；评测采集必须保留该失败。RAG生成失败仍保留初检原文。[返回约定](BACKEND_RESULT.md)

最终Auto没有额外复杂度分类器，用RAG回答明确缺口及引用信号触发；不承认的隐性遗漏可能不升级。普通完整请求通常与RAG一样2调用；复杂题需额外草稿，未开启arXiv时最坏预算13。此前251测试、32新HTTP开发回归与各失败详见[改进报告](../evaluation/results/agent_auto_improvement_20261022/report.md)和[区别/选型](../evaluation/results/agent_auto_improvement_20261022/design.md)。旧68请求/8题及两题CLI冒烟分别见旧报告，不能归给当前策略。

新增绑定与输入隔离重点读`scoped_prefix()`、`isolate_need()`、`has_source_quote()`及`src.agent_answer.answer_input()`：原审计question_quote保存在文件里，模型的检查/生成/复核需求仅id/subject/need，减少混合原句诱发范围串用。字母间连字符后的排版空白仅影响原文引文匹配，不修改原文或需求摘录。

## P2.5 评测与规划修复

先读[冻结评分](../evaluation/results/agent_p25_20261021/review_protocol.md)，再读[评测驱动](../evaluation/results/agent_p25_20261021/run_comparison.py)：实际运行main，共用初检原文，调用原有run_diagnostics()/run_answer()；全局账本控制实际调用预算，旧答案/Gold不进入Agent。评测没有修改生产函数。

随后看[逐题原文审阅](../evaluation/results/agent_p25_20261021/manual_review.md)和[报告](../evaluation/results/agent_p25_20261021/report.md)：b02/b03/b06曾暴露回指、非逐字抽取、联合主体问题。三种已知阻塞修复后，三题开发回归交付3/3、冻结严格1/3；旧记录保持。新8题又暴露更复杂主体句式和PDF排版匹配问题，不宣称绑定已覆盖所有自然语言。另读[旧修复](../evaluation/results/agent_plan_fix_20261022/report.md)、[Auto新题审阅](../evaluation/results/auto_closeout_20261022/manual_review.md)与[项目量化入口](PROJECT_METRICS.md)。

反馈状态的新入口是`feedback_scope()`：未完成项始终复查；已支持项遇到同源新段或明确主体时再复查，否则保留原已校验状态。`assess_evidence()`只应用复查ID的更新，合并后仍校验全部需求，循环/单步保存反馈范围。被复查项的非法状态仍失败，不把partial自动改supported。[修复报告](../evaluation/results/agent_feedback_fix_20261022/report.md)。

P3.1先读`src/arxiv_tools.py`的`search_arxiv()`与`read_arxiv_paper()`：题录定位与固定版本原文分开，复用原PDF解析器；独立证据ID、原文/页码/网址/哈希与请求记录都保留。[工具设计/边界](../evaluation/results/p3_arxiv_tools_20261022/design.md)。

P3.2再读`src/arxiv_evidence.py`：`run_arxiv_followup()`最多做路由、选论文、重查证据三次决策；`validate_download()`核对版本、文件哈希并重解析实际PDF；`select_passages()`从连续原文窗口预选120段、用已有BGE取最多6段。新段保留`origin=arxiv`、独立`evidence_id`、版本、页码、网址、PDF哈希与字符偏移，仅为兼容现有校验分配临时整数ID，不写入本地索引。合并后复用`assess_evidence()`和`answer_with_review()`，外部来源链接由实际被引用的登记表生成。[接入流程、首次搜索不足与验证](../evaluation/results/p3_integration_20261022/report.md)。

## P3新题验收暴露的名称边界

此前六题主对照Agent-off/on为4/6、5/6，Auto次级1/2，该轮生产代码全程冻结。两条失败集中在`src/arxiv_evidence.py`的外部标题核对：规划主体可以合法含original/paper，旧核对却将整个短语当成书目名称，正确标题因此被拒绝。[逐题验收](../evaluation/results/p3_validation_20261022/report.md)、[原始诊断](../evaluation/results/p3_validation_20261022/failure_diagnosis.json)。

书目修复轮只改该文件：`paper_subject()`仅移除边缘的the/original和末尾paper，提取书目查找名；`run_arxiv_followup()`在模型提出标题、实际选择的题录标题两处使用查找名，同时保留原完整名称的匹配。原subject/need仍完整传给选论文、查证据和回答，`agent.names_subject()`全局规则没有修改；名称内部词、连字符和版本数字保留，空名称或错论文仍拒绝。`subject_identity`记录完整主体及查找名，便于追查。

该修复轮新增7项行为回归，原代码先复现6个失败子场景，修复后定向26项、全套298项离线通过。受控main测试替换模型/HTTP/CPU资源，PDF解析、来源/引文校验仍执行；原两组FlashAttention主体/标题也单独离线核对。该轮模型请求和公网GET均0。[修复报告与开发回归含义](../evaluation/results/p3_subject_fix_20261022/report.md)。

随后上一轮真实复验保持当时生产代码不变：n04/Auto主体original FlashAttention paper提取为flashattention并发起搜索，n06/Agent本次主体直接为FlashAttention；两条搜索均HTTP429，分别降级和失败。问题发生于`arxiv_tools.fetch_bytes()`，未到达PDF、外部原文核验或Agent最终回答复核；当前没有等待/缓存恢复路径，已有失败不重试策略保留。9模型POST/12278 token、2公网GET，旧成绩不改；本轮未重复整套离线测试。[本次真实输出与瑕疵](../evaluation/results/p3_closeout_20261023/report.md)。

## 2. 怎样阅读 agent.py

建议先看 `run_diagnostics()`，再按调用关系追到以下函数：

1. **`load_replay_cases()`：准备输入。** 从已成功的 P1 记录读取原题、检索原文和同版本论文目录，核对 manifest、文件哈希及 chunk 身份。旧答案、Gold、旧分解和评审标准不进入传给模型的白名单数据。
2. **`plan_requirements()`：第一次模型调用。** 模型只看问题，返回主体和原题片段；`bind_requirements()`绑定原片段，明确的单主体回指扩展到先行词；`isolate_need()`仅投影紧邻的联合主体，原始question_quote保留，need只含本主体及原谓语条件；`validate_plan()`重新计算并校验，不能自由改写need。
3. **`assess_evidence()`：第二次模型调用。** 模型看到绑定需求、预计算查询、原文和目录，要求每项独立判断 supported/partial/missing/conflicting，并提出一个 `next_action`。
4. **`validate_assessment()`：本地约束。** 检查字段、需求归属、chunk ID、原句存在性、状态与行动参数。词法与原句检查仍不是完整语义正确性的证明。
5. **`execute_action()`：分派一次工具。** 已通过校验的search调用搜索函数；read_neighbors读取已给出的中心段附近；answer/stop返回未执行状态，不生成答案。
6. **`merge_evidence()`：准备反馈原文。** 核对知识库版本、manifest及各段原文；保留旧证据顺序、追加新段，按版本/ID去重。只将原文字段传给模型，分数和工具轨迹留在日志。超出32段或24000字符则报错，不截断正文。
7. **`action_signature()`：识别重复。** 只比较type/query/source/chunk_id，理由文字改变不代表新行动。
8. **`neighbor_ids()`及`neighbor_fallback()`：识别重叠区域。** 只看来源、位置和章节元数据，计算前后各两段的范围。当原建议重复或与已读区域重叠超过一半，尝试同篇、与原题公共任务至少重合两个词的未读章节区域。同分按文档先后试读，没有候选则不改选，仍受重复/新增证据/预算规则约束；未知章节跳过。选择来源记录在action_overrides与step.action_origin，不伪装成模型建议。
9. **`shared_question_context()`：保留公共场景。** 只取原题For/In/Under/On开头、逗号前且不含任一方法名的前缀，补入工具的实际查询；不添加答案术语。effective_query和模型query分别保存。
10. **`run_diagnostics()`中的while循环：控制执行。** 终止判断→重复/区域检查→动作/API预算→执行并落盘→合并原文→无新片段停止→反馈模型。规划校验修正与checked_assessment/revise_assessment的状态修正或行动改选共用最多一次额度；规划修正仅max-actions启用，所有完整但无效输出均保留，修正后仍严格校验。

默认模式接受一至三题，单步接受一至两题，循环只接受一题；整批最多六次API请求。工具和网络失败不自动重试；已完成同输入调用与工具结果可精确续接。循环的max-actions最多3，邻段窗口2，证据仍最多32段/24000字符。

主要输出文件：

| 文件 | 用途 |
| --- | --- |
| `protocol.json` | 冻结源码、输入、公开模型选项及预算 |
| `inputs.json` | 保存实际白名单输入 |
| `actual_chat_calls.json` | 每次请求、原始响应、usage、耗时与失败状态 |
| `h01.json` 等逐题文件 | 单步execution；循环steps/action_overrides/final_assessment/halt_reason；原文及判断均保留 |
| `summary.json` | 本批次完成情况、调用总量及行动建议汇总 |

`next_action.type=answer`本身只表示可以进入回答；显式`--finalize`才接回答阶段。循环可继续执行search/read_neighbors，单步模式保持只执行一次。[P2.3轨迹](../evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json)与[报告](../evaluation/results/agent_loop_20261020/report.md)可直接阅读；此前单步失败和P2.1记录原样保留。

P2.2当时全部142项测试通过；单步增加16项、循环再增加22项后为180项。P2.4当时新增22项，共202项离线测试通过；规划修复当时再增15项为217项；main接入当时增13项为230项；第一版Auto再增9项为239；此前更新Auto并增范围/输入隔离检查时251项通过；此前反馈/P3.1工具之后272项通过；P3.2新增19项后291项通过；书目修复轮新增7项后298项通过、网络尝试0。此前原题场景保留改善任务段排名，防止区域重叠后读到RAG的EM原文；第三次行动来自本地元数据规则。P2.4最终答案使用[26]对应765、[2]对应1003；1003原文自身也点名PopQA与TriviaQA，1002则补充短问答任务语境。新题与同条件对照已在P2.5完成首轮，结果见下文。

### P2.4 怎么读

先看`agent.py`中的`load_answer_case()`和`run_answer()`，再看`src/agent_answer.py`：

1. **`load_answer_case()`准备可信输入。** 读已完成记录及相邻的inputs/protocol，核对上游输入哈希、问题、版本、知识库文件和原文身份，复用原有需求/状态校验。只取问题、绑定需求、最后状态、原文和停止原因，重新按保留顺序分配引用号，不传Gold或旧答案。
2. **`answer_with_review()`控制回答。** 全部missing时本地列缺口，零请求；否则生成初稿，再复核。两次复核之间最多修订一次，不重新检索、不扩充预算。
3. **`answer_prompt()`约束写作。** 只凭原文，按各主体原有范围回答；partial说明已知与缺口，missing不猜值，conflicting不任意选边。比较结论来自分别成立的事实，不要求论文中存在跨篇比较句。
4. **`review_prompt()`和`validate_review()`共同检查。** 模型查覆盖、主体、数值、条件、引用、无额外断言和缺口；程序查每项是否恰好出现一次、布尔值是否合法、answer_quote是否真在草稿里、支持引文是否真在对应[n]原文里。模型自称全部pass不能跳过这些检查。
5. **`run_answer()`负责审计。** 回答阶段独立最多4请求；每次请求前落盘，已完成同输入响应可复用，失败和中断中的请求不自动重试。`--finalize`把决策/回答日志分别写到loop/answer，总上限6+4=10。

`review_passed`只表示通过这套自动检查；`semantic_correctness`仍标记待人工核对。两次都失败时`review_failed`，`answer.md`只输出未通过说明，被拒草稿留在JSON。网络失败/截断直接失败并保留原始响应与usage，不能伪装成证据不足。当前[报告](../evaluation/results/agent_answer_20261021/report.md)、[逐条原文核对](../evaluation/results/agent_answer_20261021/manual_review.md)及[答案](../evaluation/results/agent_answer_20261021/network_followup/h10/answer.md)可直接查看，无需重复付费运行。

阅读`src/agent_tools.py`中的`read_neighbors()`时，可以沿四步看：

1. 校验`chunk_id`在当前库内、`source`等于中心片段的精确来源、`window`为0～2的整数。
2. 从`chunks`中筛出同篇论文，保留入库顺序，再找到中心位置。不能简单对全库ID加减，否则可能读到其他论文。
3. 用列表切片取前后各`window`段，并保留中心段；默认最多3段，最大5段，首尾自动截断。
4. 复制原始字段，加版本和`offset`返回。`offset=0`是中心段，负数为前文、正数为后文；`trace`记录ID、字符数与耗时，不进行模型调用。

它解决的是“检索命中一段，但定义、条件或判据在附近”的问题。真实人工样例用此前搜索已命中的763号片段，显式`window=2`读出761～765；765中有Exact Match（EM）的评价说明。这个已知开发样例证明原文可按顺序展开，不代表Agent自主选择了片段或h10回答已验收。ID只在同一知识库版本内有效，应复用产生搜索命中的那份资源；邻段依据已存分块顺序，无法补回解析或分块时遗漏的内容。

## 3. 其余代码的阅读顺序

| 顺序 | 文件 | 阅读重点 |
| --- | --- | --- |
| 1 | [main.py](../main.py) | 一次问答的完整固定流程；候选 120、最终 10 与 RRF_K=60 的区别 |
| 2 | [src/retriever.py](../src/retriever.py)、[src/bm25_retriever.py](../src/bm25_retriever.py)、[src/hybrid_retriever.py](../src/hybrid_retriever.py) | 向量/关键词检索和按名次融合 |
| 3 | [src/reranker.py](../src/reranker.py)、[src/evidence_gap.py](../src/evidence_gap.py) | 全局/局部排名、预算内选证据、规则补查与停止 |
| 4 | [src/grounded_evidence.py](../src/grounded_evidence.py)、[src/numeric_evidence.py](../src/numeric_evidence.py) | 原文账本、有限数值解析、主体线索和未知项 |
| 5 | [src/api_llm.py](../src/api_llm.py)、[src/citation_validation.py](../src/citation_validation.py) | API 完成状态、调用边界、引用结构检查及有限修复 |
| 6 | [agent.py](../agent.py) | 独立的需求与证据决策原型，与固定 RAG 对照 |
| 7 | [build_semantic_index.py](../build_semantic_index.py)、[src/pdf_loader.py](../src/pdf_loader.py)、[src/chunking_semantic.py](../src/chunking_semantic.py)、[src/knowledge_base.py](../src/knowledge_base.py) | 从 PDF 到配对版本；建库与激活分开 |
| 8 | [evaluation/run_evaluation.py](../evaluation/run_evaluation.py)、[evaluation/run_answer_evaluation.py](../evaluation/run_answer_evaluation.py)、[evaluation/metrics.py](../evaluation/metrics.py) | 检索指标与真实回答采集的区别、缓存和 API 成本边界 |

根目录辅助脚本、其余 `src/` 模块、全部六个评估脚本和十四个测试文件也已补上用途或边界注释。测试通过替身验证的行为与真实模型语义表现要分别理解。

## 4. 此前注释整理的修改与验证记录

- 46 个当前 Python 文件新增 180 行中文注释及 46 行分隔空行；执行语句、字符串字面量、函数签名、已有注释和文档字符串均保留。
- 修改前保存源码副本，逐文件比较忽略位置信息的 AST 与去除注释/空白 NL 的代码词元，并进行纯编译检查；没有执行建库或付费评测入口。
- 当时注释版重新运行全部 **123 项 unittest，通过，无失败或跳过**。测试期间阻断 socket 连接；真实项目生成 API 调用为 0，没有新增测试或依赖。这是10月20日的注释整理记录，当前总数见本页开头。
- 历史实验驱动/源码快照、题集、PDF、索引、激活指针、旧日志和统计结果保留；未编辑虚拟环境和第三方代码。完整源码前后哈希与核对结果见 [verification.json](code_comments_20261020_verification.json)。

**源码哈希与历史续接：** 注释不改变执行语句，但会改变源码字节。`run_diagnostics()` 有意使用原文件哈希绑定实验协议，所以当前注释版不能直接向 P2.1 的旧输出目录续接。旧目录中“同源码续接新增调用 0”是当时的实测记录。查看历史结果无需运行；今后明确需要新实验时使用新目录并记录新的调用。旧源码快照和协议保持原样，不能为接受当前源码而修改历史哈希。

后续新增或修改代码继续适量补中文注释，优先解释用途、输入输出、关键取舍和约束；已有清楚的简单语句无需逐行翻译。
