# P2.1 收尾：最新版三题完整链路验收

日期：2026-10-20（Asia/Shanghai）。**P2.1 已完成本次约定的小规模验收；P2.2 未开始，留待用户先询问概念和工具范围。**

本轮不修改生产代码，使用当前 `agent.py` 完整新跑 h01／h10／h11 的“需求规划 → 绑定原题 → 证据检查 → 行动建议”。程序完成 3/3，人工语义核对 3/3。实际 6 次 API、9,907 token、全部 stop，零自动重试、零工具执行。

## 1. 做了什么

1. 核对当前代码与上一轮通过 123 项测试的交付源码完全一致，保存源码和 2,147 项旧项目文件 hash。
2. 从 P1 记录读取三题全部实际原文，核对八篇配对库、manifest、chunk／向量文件 hash、ID、来源、页码和正文一致性。没有重跑检索，也没有把旧答案或 Gold 传给模型。
3. 在首次请求前冻结代码、输入、公开 API 参数、人工验收要求及 **6 次硬上限**。
4. 三题各新调用一次抽取式规划、一次证据检查；不复用前轮规划、检查或答案。
5. 核对范围、支持状态和建议参数，校验四处原文引用；完成目录再次进入新增调用为 0。

## 2. 三题验收结果

| 题目 | 新规划与检查结果 | 建议 | 人工核对 |
| --- | --- | --- | --- |
| h01 标签平滑 | 两项需求均 supported；69 支持 0.1，70 支持困惑度变差、accuracy／BLEU 改善 | answer | 通过；需要的数值和方向均有原文，未把编号合法当作事实支持 |
| h10 RAG／Self-RAG 判据 | RAG missing、evidence=[]；Self-RAG supported，引用 1003／1002 | search r1 | 通过；PopQA／TriviaQA 仍属于 Self-RAG，训练损失不算评测判据支持，另一项缺失不降低 Self-RAG 状态 |
| h11 Mamba 规格 | 训练数据规模与隐藏维度合并为一项，missing；完整八篇目录没有 Mamba 论文 | stop | 通过；不借其他论文参数，不捏造数值 |

h10 的真实搜索建议：

```text
RAG: how does the correctness criterion reported by RAG differ | how does the correctness criterion reported by RAG differ
```

没有 PopQA／TriviaQA 或猜测答案；source=null 为现协议允许的全库查询建议，尚未执行。

原始 JSON 的 `semantic_correctness=requires_manual_review` 是程序固定标记，保留不改；本轮 3/3 人工结论另存于 [manual_review.md](manual_review.md)／[manual_review.json](manual_review.json)，不是直接读取模型自评。

## 3. 调用和时间

| 项目 | 本次实测 |
| --- | ---: |
| 新规划／新检查 | 3／3 |
| 实际 chat／HTTP POST | 6／6 |
| 输入／输出／总 token | 8,886／1,021／9,907 |
| finish_reason | 6 次均 stop |
| API 失败／自动重试 | 0／0 |
| 三题程序耗时合计 | 14.336 秒 |
| API 请求计时合计 | 14.313 秒 |
| 工具执行／新检索／最终答案生成 | 0／0／0 |
| 完成后续接新增调用 | 0 |

这是复用已保存原文的诊断耗时，不是完整 RAG 延迟、并发或 P95。沿用现有私有 API 配置；未导出凭证，也不根据未核实的单价推测费用。与前轮 7 次修正调用分别记账。

## 4. 验证与保留边界

- 6 次调用的编号、阶段、提示 hash、usage 与独立 HTTP 审计一致；冻结时间早于第一请求。
- 抽取模型真实返回 id／subject／question_quote，程序绑定 need；检查模型只看到绑定需求、查询、原文与目录，未输入旧答案／Gold／人工标准。
- 四处引用与配对 chunks 的来源、页码、原句一致；本轮未重新解析 PDF。
- 当前源码与上一轮 123 项测试对应版本一致；**本轮未重复运行该测试集**，不能把历史测试说成本轮新测试。
- 发布前 2,147 项旧文件 hash 均一致；只更新进度／README／桌面总览并新增本轮日志，不修改 main、agent、测试、知识库、激活指针或旧实验。
- h01 第二项主体原文为 “the paper”，本题回指唯一论文且原文支持明确；保留该非规范名称。h10 source=null 和重复查询片段也保留。这些不影响本次需求／证据判断验收，但不能据此宣称后续来源路由已验证。
- 三题为已知开发／回归题，3/3 不代表独立泛化准确率；尚无自动补查、工具循环或新最终答案收益。

## 5. 阶段结论与下一步

**P2.1 收尾完成。** 新规划到检查的完整三题已实际运行，满足本轮约定的收尾条件，不再把这三题完整回归列作待办。

**P2.2 保持未开始。** 用户将先询问“本地工具接入是什么、要接入哪些工具”；下一次先讲解目的、范围、输入输出和验收，再按用户后续要求实施。本轮不接入或执行任何工具。

## 6. 审阅入口

- [冻结协议](protocol_before_run.json)、[实际运行协议](run/protocol.json)、[白名单输入](run/inputs.json)。
- [h01 完整结果](run/h01.json)、[h10 完整结果](run/h10.json)、[h11 完整结果](run/h11.json)。
- [实际调用](run/actual_chat_calls.json)、[独立 HTTP 审计](actual_http_calls.json)、[汇总](run/summary.json)。
- [人工核对](manual_review.md)、[引用核验](verified_quotes.json)、[离线核验](verification.json)、[发布核对](delivery_verification.json)。
- [本轮驱动](run_closeout.py)、[离线审计脚本](verify_closeout.py)；`source_snapshot/` 是运行时源码。
- [前轮修正及失败记录](../agent_scope_fix_20261020/report.md)、[最新进度](../../../PROGRESS.md)。
