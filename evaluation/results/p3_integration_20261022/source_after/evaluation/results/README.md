# 实验结果索引

这些目录保存各轮输入、源码基线、真实请求、证据、答案、失败及离线复算；目录保持原位，避免破坏报告链接、脚本和文件哈希。最新状态见[PROGRESS](../../PROGRESS.md)，分母与成本口径见[PROJECT_METRICS](../../docs/PROJECT_METRICS.md)。

## 当前交接优先阅读

| 目录 | 内容与结论边界 |
| --- | --- |
| [p3_integration_20261022](p3_integration_20261022/report.md) | P3.2显式开启的联网闭环、291项离线回归与两题工程验证；保留首次搜索不足和开发复验，不作独立泛化分数 |
| [agent_feedback_fix_20261022](agent_feedback_fix_20261022/report.md) | 反馈状态保留/相关新反证复查，11项新增回归；旧响应注入不作真实模型验收 |
| [p3_arxiv_tools_20261022](p3_arxiv_tools_20261022/report.md) | P3.1独立arXiv只读工具、离线边界及真实GET；该轮未接自动联网与外部引用 |
| [agent_auto_improvement_20261022](agent_auto_improvement_20261022/report.md) | 最新RAG优先Auto和已知题开发回归；h10仍降级，无总体收益结论 |
| [auto_closeout_20261022](auto_closeout_20261022/report.md) | 第一版Auto的冻结8题三路径对照，不能归给最新版策略 |
| [main_agent_integration_20261022](main_agent_integration_20261022/report.md) | main资源复用、预算和两题真实CLI冒烟 |
| [agent_plan_fix_20261022](agent_plan_fix_20261022/report.md) | 回指、摘录、联合主体修复及三道已知题回归 |
| [agent_p25_20261021](agent_p25_20261021/report.md) | 首轮冻结12题RAG/Agent对照，保留规划失败与较差结果 |

## 本地Agent各步

| 目录 | 用途 |
| --- | --- |
| [agent_answer_20261021](agent_answer_20261021/report.md) | P2.4回答/复核；已知h10/h11验收与首次失败 |
| [agent_loop_20261020](agent_loop_20261020/report.md) | P2.3预算循环、章节改选和已知h10开发轨迹 |
| [agent_feedback_20261020](agent_feedback_20261020/report.md) | 单次工具执行与反馈，保留校验失败 |
| [agent_local_search_20261020](agent_local_search_20261020/report.md) | 本地搜索工具单独验收 |
| [agent_neighbors_20261020](agent_neighbors_20261020/report.md) | 同篇邻段读取工具单独验收 |
| [agent_p21_closeout_20261020](agent_p21_closeout_20261020/report.md) | P2.1三题完整规划/检查，小规模收尾 |
| [agent_scope_fix_20261020](agent_scope_fix_20261020/report.md) | 需求范围与主体条件隔离修正 |
| [agent_step1_20261020](agent_step1_20261020/report.md) | 首轮需求与证据诊断，语义缺陷保留 |

## 固定RAG、语料与检索

| 目录 | 用途 |
| --- | --- |
| [holdout_v1_20261020](holdout_v1_20261020/report.md) | P1固定RAG的12题留出基线，部分题随后转开发集 |
| [quick_closeout_20261020](quick_closeout_20261020/report.md) | 五题真实主流程和失败边界 |
| [normalized_precision_20261020](normalized_precision_20261020/report.md) | 从保存结果补充nP与复算，未改善原排名 |
| [evidence_retention_20261020](../../docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md) | 锚点/局部证据保留、候选60/120、独立Top-10/20对照 |
| [all_papers_20261020](../../docs/ALL_PAPERS_EVALUATION_2026-10-20.md) | 八篇库、查询增强与两轮补查历史对照 |
| [completion_rounds_20261019](../../docs/COMPLETION_ROUNDS_2026-10-19.md) | 0/1/3轮补查，保留局部退步 |
| [evidence_gap_20261019](../../docs/EVIDENCE_COMPLETION_2026-10-19.md) | 单轮规则补查原型 |
| [independent_validation_20261019](../../docs/INDEPENDENT_VALIDATION_2026-10-19.md) | 十二道英文新题与模型知识对照 |
| [retrieval_optimization_20261019](../../docs/RETRIEVAL_OPTIMIZATION_2026-10-19.md) | 开发集检索与证据选择优化 |
| [retrieval_metrics_20261019](../../docs/RETRIEVAL_EVALUATION_2026-10-19.md) | 初始检索量化 |
| [decomposition_fix_20261019](../../docs/DECOMPOSITION_EVALUATION_2026-10-19.md) | 分解修复与主流程证据对齐 |
| [arxiv_pilot_20261019](../../docs/ARXIV_PILOT_2026-10-19.md) | 五篇固定版本论文下载、解析、检索与回答 |
| [kb_versions_20261019](kb_versions_20261019/verification.json) | 知识库成对版本、切换与回退验证 |
| [mac_20261019](../../docs/MAC_AUDIT_2026-10-19.md) | Mac迁移、CPU模型与真实API抽测 |
| [reliability_20261019](reliability_20261019/verification.json) | API未完成输出、BM25边界及失败留档回归 |
| [rewrite_hyde_20261018](../../docs/REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md) | 查询增强与本地Qwen历史对照 |
| [deepseek_v41](../../docs/DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md) | 早期六题真实回答、固定证据与提示调试 |

`source_before/`、`source_snapshot/`、`baseline/`、`final/`等名称是各轮内部定义；有些final后仍有后续修复，最新生产版本应核对当前PROGRESS和该轮报告。旧JSON/Markdown中的得分、调用和失败保持原样，不通过目录名推断“通过验收”。

恢复上下文先读保存记录。不同版本、不同题集和共享初检不能混合计分或重复计费；新实验使用新目录。空stdout、首次失败和未采用试验仍有审计用途，不按文件为空或运行失败删除。
