# 代码阅读说明与 Agent 当前边界

更新：2026-10-22（Asia/Shanghai，P2.5之后规划修复与开发回归）。此前注释整理覆盖46个Python文件；随后新增工具、执行反馈、循环及回答复核测试，均带中文说明。本轮另增规划回归测试文件；历史实验驱动和快照另行保留。

## 1. 当前做出了什么

当前已实现 **有预算工具循环及最终回答复核**；默认保留P2.1诊断模式，`--execute-once`为单步，`--max-actions 3`为循环；加`--finalize`后接回答，`--answer-from`可独立复用保存的证据。代码仍由普通函数、字典和列表组成。

它可以选择行动、执行工具、合并原文，再判断是否继续，并在回答阶段综合证据、逐项复核和有限修订。此前h10循环回归3次工具补到关键原文，复用了当轮精确提示的真实响应前缀。本轮P2.4以该证据新做4次生成/复核请求，最终通过已知题审阅；h11全缺失零调用拒答。生产入口仍从保存的检索记录启动；P2.5已用新题评测驱动接真实初检再调用原Agent，固定RAG／Agent严格通过10/12与7/12，当前Agent收益验收未通过。统一生产入口和更大范围泛化仍待实施。功能数量和是否使用`Agent`类都不是判断标准。

| 文件 | 已实现的职责 | 谁决定下一步 |
| --- | --- | --- |
| `main.py` | 分解、检索、融合、重排、规则化补查、生成和引用结构检查 | Python 预先安排步骤，部分开关/条件决定是否运行 |
| `src/evidence_gap.py` | 按来源覆盖和局部片段入选信号，实际补检索并重新选择证据 | 固定规则；不使用 LLM 判断具体事实是否已有支持 |
| `agent.py` | 抽取需求、检查原文，单步或有限循环执行本地工具 | LLM提出建议，本地校验/预算约束执行；有记录的章节规则可改选重复或重叠行动 |
| `src/agent_tools.py` | 搜索八篇库、读取同篇论文邻段，返回真实原文和轨迹 | 普通函数执行，由`agent.py`的执行入口分派 |
| `src/agent_answer.py` | 生成答案、逐项复核、最多修订一次；全缺失时直接说明缺口 | 模型判断内容，本地严格核对复核结构与逐字引文，预算约束执行 |

`agent.py`并非只做补查：它判断能否回答、应否停止及是否适合读邻段。默认模式保存建议，单步模式执行一次，循环模式最多执行三次；固定RAG的原有补查仍来自`main.py`调用的`evidence_gap.py`。

## P2.5 评测与规划修复

先读[冻结评分](../evaluation/results/agent_p25_20261021/review_protocol.md)，再读[评测驱动](../evaluation/results/agent_p25_20261021/run_comparison.py)：实际运行main，共用初检原文，调用原有run_diagnostics()/run_answer()；全局账本控制实际调用预算，旧答案/Gold不进入Agent。评测没有修改生产函数。

随后看[逐题原文审阅](../evaluation/results/agent_p25_20261021/manual_review.md)和[报告](../evaluation/results/agent_p25_20261021/report.md)：b02/b03/b06分别暴露回指、非逐字抽取、联合主体被规划校验拒绝。它们发生在工具执行之前。三种阻塞现已修复，三题开发回归交付3/3，冻结严格1/3；原失败记录和评分保持不动。另读[修复流程](../evaluation/results/agent_plan_fix_20261022/report.md)和[原文核对](../evaluation/results/agent_plan_fix_20261022/manual_review.md)，修复版新题收益仍待验证。成本、调用、耗时与评分解释见[项目量化入口](PROJECT_METRICS.md)。

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

P2.2当时全部142项测试通过；单步增加16项、循环再增加22项后为180项。P2.4当时新增22项，共202项离线测试通过；规划修复再增15项，当前217项全部通过、网络尝试0。此前原题场景保留改善任务段排名，防止区域重叠后读到RAG的EM原文；第三次行动来自本地元数据规则。P2.4最终答案使用[26]对应765、[2]对应1003；1003原文自身也点名PopQA与TriviaQA，1002则补充短问答任务语境。新题与同条件对照已在P2.5完成首轮，结果见下文。

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
- 当前注释版重新运行全部 **123 项 unittest，通过，无失败或跳过**。测试期间阻断 socket 连接；真实项目生成 API 调用为 0，没有新增测试或依赖。
- 历史实验驱动/源码快照、题集、PDF、索引、激活指针、旧日志和统计结果保留；未编辑虚拟环境和第三方代码。完整源码前后哈希与核对结果见 [verification.json](code_comments_20261020_verification.json)。

**源码哈希与历史续接：** 注释不改变执行语句，但会改变源码字节。`run_diagnostics()` 有意使用原文件哈希绑定实验协议，所以当前注释版不能直接向 P2.1 的旧输出目录续接。旧目录中“同源码续接新增调用 0”是当时的实测记录。查看历史结果无需运行；今后明确需要新实验时使用新目录并记录新的调用。旧源码快照和协议保持原样，不能为接受当前源码而修改历史哈希。

后续新增或修改代码继续适量补中文注释，优先解释用途、输入输出、关键取舍和约束；已有清楚的简单语句无需逐行翻译。
