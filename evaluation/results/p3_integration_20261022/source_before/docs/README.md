# 项目文档导航

当前状态只以[PROGRESS](../PROGRESS.md)为准；[项目全流程](PROJECT_WORKFLOW.md)与桌面总览描述预期路线。日期报告记录各轮当时的实现、失败和结论，不能将其中“尚未接main／未实现Auto”等句子当作今天的状态。

## 继续开发或运行

| 需要了解什么 | 入口 |
| --- | --- |
| 当前已完成、限制和下一步 | [PROGRESS](../PROGRESS.md) |
| 三模式启动、默认值、知识库选择 | [README](../README.md) |
| 功能分工与代码阅读顺序 | [代码阅读说明](CODE_READING_GUIDE.md) |
| Agent工具、保存记录诊断、单步/循环/回答 | [Agent操作](AGENT_REPLAY_GUIDE.md) |
| 各阶段预期工作 | [全流程路线](PROJECT_WORKFLOW.md) |
| 指标分母、质量与成本 | [项目量化入口](PROJECT_METRICS.md) |
| 索引构建、切换和回退 | [知识库版本](KNOWLEDGE_BASE_VERSIONS.md) |
| API与开发环境 | [PyCharm设置](PYCHARM_API_GUIDE.md)、[Mac接续](MAC_HANDOFF.md) |

## 当前重点证据

| 工作 | 报告 |
| --- | --- |
| 最新反馈状态修复、旧h10离线回放与边界 | [修复报告](../evaluation/results/agent_feedback_fix_20261022/report.md) |
| P3.1 arXiv搜索/固定版本原文读取，尚未自动联网 | [设计](../evaluation/results/p3_arxiv_tools_20261022/design.md)、[实测与失败](../evaluation/results/p3_arxiv_tools_20261022/report.md) |
| 最新RAG优先Auto、已知题改善和h10降级 | [设计](../evaluation/results/agent_auto_improvement_20261022/design.md)、[实测与失败](../evaluation/results/agent_auto_improvement_20261022/report.md) |
| 第一版Auto的8题三路径对照，旧版本分数 | [报告](../evaluation/results/auto_closeout_20261022/report.md)、[人工原文核对](../evaluation/results/auto_closeout_20261022/manual_review.md) |
| main接入与两题真实CLI验证 | [接入报告](../evaluation/results/main_agent_integration_20261022/report.md) |
| P2.5首轮12题RAG/Agent对照，修复前分数 | [报告](../evaluation/results/agent_p25_20261021/report.md)、[冻结评分](../evaluation/results/agent_p25_20261021/review_protocol.md) |
| 三类规划问题修复、旧失败题开发回归 | [修复报告](../evaluation/results/agent_plan_fix_20261022/report.md) |
| 本次进度核对与文件清理 | [清理记录](CLEANUP_LOG_2026-10-22.md) |

## 历史实验与接续依据

实验原始目录保持原位，题集、Gold、源码快照、原始请求、失败和成本记录均从[实验目录索引](../evaluation/results/README.md)进入。以下文档按工作归类，不改原实验版本与分数。

| 工作 | 文档 |
| --- | --- |
| Mac迁移与环境核对 | [2026-10-19审计](MAC_AUDIT_2026-10-19.md) |
| 五篇论文先导与选择理由 | [先导实验](ARXIV_PILOT_2026-10-19.md)、[论文选择](ARXIV_PILOT_SELECTION_2026-10-19.md) |
| 分解、检索与英文新题 | [分解修复](DECOMPOSITION_EVALUATION_2026-10-19.md)、[检索量化](RETRIEVAL_EVALUATION_2026-10-19.md)、[检索优化](RETRIEVAL_OPTIMIZATION_2026-10-19.md)、[新题验证](INDEPENDENT_VALIDATION_2026-10-19.md) |
| 补查轮数、八篇库、证据保留与预算 | [单轮补查](EVIDENCE_COMPLETION_2026-10-19.md)、[轮数对照](COMPLETION_ROUNDS_2026-10-19.md)、[八篇评估](ALL_PAPERS_EVALUATION_2026-10-20.md)、[保留与预算](EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md) |
| 归一化Precision | [指标说明](NORMALIZED_PRECISION_2026-10-20.md) |
| P1回答基线与早期收尾 | [12题留出](RAG_HOLDOUT_V1_2026-10-20.md)、[五题收尾](RAG_QUICK_CLOSEOUT_2026-10-20.md) |
| P2.1演进与小样本验收 | [首轮](AGENT_STEP1_2026-10-20.md)、[范围修正](AGENT_SCOPE_FIX_2026-10-20.md)、[三题收尾](AGENT_P21_CLOSEOUT_2026-10-20.md) |
| 早期模型、提示和保持风格清理 | [DeepSeek调试](DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md)、[rewrite/HyDE与本地模型](REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md)、[10月18日清理](CLEANUP_LOG_2026-10-18.md) |
| 全部历史进度、旧清单与恢复 | [完整进度正文](history/PROGRESS_THROUGH_2026-10-22.md)、[历史归档](history/README.md)、[早期实验概览](experiments.md) |

`chat_history/`保留10月19～20日已导出的对话及工具记录；最新10月21～22日上下文还需结合各轮报告和当前PROGRESS，不把旧导出当作完整最新对话。
