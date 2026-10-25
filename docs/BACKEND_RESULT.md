# 后端返回结果与失败交付

2026-10-25。`main()`仍返回普通字典。RAG、Agent、Auto共用以下字段，Agent/Auto同时保存为运行目录的`result.json`；RAG直接返回，不新增审计目录。

| 字段 | 含义 |
| --- | --- |
| `query` / `mode` | 原问题和实际执行模式 |
| `status` | `completed`处理结束、`degraded`补查未完成但有有限交付、`failed`处理或回答校验失败 |
| `answer` | 非空的答案、缺口或失败说明；不会把被拒绝的草稿作为故障说明发布 |
| `answer_status` | 区分自动复核通过、证据不足、来源不可用、未作语义复核或校验失败，见下表 |
| `stop_reason` | 如`answer_ready`、`model_stop`、`external_rate_limited`、`external_timeout`、`processing_failed` |
| `ledger.citation_registry` | 当前交付对应的真实原文和出处；初检前失败时为空 |
| `selected_ids` | 当前所用片段ID；不能跨知识库版本混用 |
| `source_scope` / `retrieval_query` | 明确限定的论文文件名与用于检索的正文问题；一般问题的scope为空 |
| `actions` | 已尝试的本地或arXiv工具及状态；外部行动附请求诊断，不作为事实证据 |
| `api_summary` | 实际调用尝试、失败、已报告token合计与usage缺失调用；不根据缺失usage推算用量 |
| `network` | 未请求时`not_requested`；启用后的状态、GET工具次数、读论文数、失败阶段与诊断 |
| `error` / `run_dir` | 有错误时保留原因；Agent/Auto提供详细运行记录位置 |

`completed`只表示处理完成，包含有根据的证据不足答复，不能直接用作答案准确率。`degraded`和`failed`的CLI退出码均为1。模式、知识库版本、补查轮数和非空输出目录等入口校验错误仍抛出异常；运行时模型/工具故障返回明确的失败结果。

| `answer_status` | 解读 |
| --- | --- |
| `review_passed` | 通过当前自动复核，仍不是独立语义验收 |
| `insufficient_evidence` | 当前原文不足以回答，已说明需求缺口 |
| `source_unavailable` | 外部获取失败，原文尚未核实；不代表论文没有报告 |
| `not_reviewed` | RAG或Auto初检答复，只做引用结构检查 |
| `fallback_not_reviewed` | Agent本地失败后的新RAG后备答案，仅通过引用结构检查；原Agent错误仍保留 |
| `review_failed` / `citation_failed` | 回答复核或引用检查失败，仅交付说明 |
| `unavailable` | 处理失败，未得到可交付的事实性答案 |

429、超时和其他外部传输失败的处理顺序：

1. 保存失败工具与请求记录，区分搜索、PDF读取、来源校验和模型判断。校验错误不能归为临时网络故障。
2. Auto有引用结构合格的初检草稿时保留它，并附来源不可用说明；该草稿仍未通过Agent语义复核。
3. Agent或没有合格草稿的Auto使用本地已校验输入回答。全部missing时直接列出未核实需求，不再调用模型；有本地支持时仍走原有限生成/复核预算。
4. 获取失败时，回答输入中的missing/partial缺口改为中性的“尚未核实”，原判断保留在loop记录中，避免复制未经原文证明的“论文未报告”。
5. 顶层标为`degraded`和`source_unavailable`，失败工具保持`failed`。若本地回答也未通过复核，仍为`failed`。

HTTP诊断只保留必要的公开响应头、最多2048字节的错误正文、状态码和耗时；`Retry-After`支持秒数及HTTP日期，无有效值时记为null。不自动等待重试，不切换来源，不复用未经核验的缓存。需要再次尝试时由调用者另建运行目录，保留旧失败。

2026-10-25新增本地Agent回退：未开启联网、初检上下文/引用登记表有效且原11次总预算仍有余量时，Agent规划或复核失败可生成一次新的RAG后备答案，并在余量内最多修复一次引用。传输错误、截断或无余量时不触发。通过后返回`degraded`、`fallback_not_reviewed`、`stop_reason=agent_failed_rag_fallback`，保留原`error`和Agent记录；失败继续保留`failed`。这与Auto复用已生成的初检草稿不同，不保证语义正确，也不增加总请求上限。[实现与评测协议](../evaluation/results/qasper_improvement_20261025/protocol.md)

Python入口可传`main(query, sources=['paper.pdf'])`，文件名须在当前库中。未显式传入时只从完整题名、文件名或arXiv编号推断明确范围；不把短缩写当成硬约束。单一标准题头将论文身份与检索问题分离；多篇比较保留多个来源。FAISS/BM25先按范围筛选再截断，片段ID保持全库行号；Agent搜索/读邻段不能越出范围。

回答验收优先级：必须回答明确子问题，保留会改变结论的单位/条件，避免编造、主体串用和错引；定义、步骤和参数按任务需要补充；改写表达、组织方式和可选背景不作为失败理由。原文连续引文、版本/哈希、引用编号和调用预算仍按原规则检查。

10月23日首次可靠性修复覆盖默认关闭rewrite/HyDE的执行配置，未重跑完整历史评测；当时工程验证和成本见[修复报告](../evaluation/results/backend_reliability_20261023/report.md)。10月25日新增范围/回退的验证与新题配对口径见[新轮协议](../evaluation/results/qasper_improvement_20261025/protocol.md)。
