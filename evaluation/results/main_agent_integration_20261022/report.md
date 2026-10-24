# main统一入口接入与选择机制

日期：2026-10-22，Asia/Shanghai。用户授权保存完整性优先级并接通main；保持普通函数、字典和列表，未提交/推送。

**新问题现在可通过main选择固定RAG或Agent，真实命令行的两种证据处理分支已跑通。** 默认RAG保留；没有自动路由器，也没有新增工具或更换模型。

## 修复/验收流程

1. 检查当前进度、main、Agent记录/原文身份接口；保存2773个现有文件的哈希和修改前源码。
2. 把用户确认的“必须修复／按任务补充／可以省略”写入PROGRESS，保留原冻结成绩，暂停围绕背景细节调试。
3. 先补main行为回归并观察旧版本11个入口测试报错，再做最小串接；随后补空问题、复核失败两项，共新增13项。全部230项离线测试通过，网络尝试0。
4. 冻结源码、两道已知问题、预算与验收条件，使用真实CLI参数、真实模型与本地Dense/BM25/RRF/BGE，不复用旧初检或旧模型响应。仅观察HTTP并断言请求前已有生产账本。
5. 逐条核对实际答案、引用和缺证据边界；保存成本与限制，更新交接。未重跑旧12题，不产生新整体准确率。

## workflow与Agent如何共存

main(mode="rag")：固定分解 → 检索/重排/规则补查 → RAG生成/引用检查。

main(mode="agent")：同一套分解与初检 → 需求规划/证据判断 → 按需搜索或读邻段并再判断 → 回答/停止 → 回答复核。

入口模式由用户/调用程序选择，不根据问题复杂度暗中切换。进入Agent后，同一API模型根据绑定需求、当前原文、论文目录与工具历史，返回answer/search/read_neighbors/stop；Python检查范围、参数、预算并执行。Agent的外框固定，框内的行动顺序按证据动态变化。并非每题都执行额外工具。

选择显式模式的依据：当前已有固定RAG基线与Agent开发结果，还没有“自动选择哪条路径更好”的独立验证；保持可解释、可比较、成本可控的入口，后续按需要再评估自动路由。

## 实现与预算

- main()保留原前四个参数，新增mode='rag'、output_dir=None。_run_pipeline保留原检索和RAG生成行为；五个原辅助函数AST不变。
- Agent模式在初检后直接调用既有run_diagnostics/run_answer，不先生成RAG答案。索引、Embedding、BM25、BGE对象直接复用，不重复加载搜索资源。
- query_decomposer仅增加可选call，默认保持原生成接口；Agent入口注入审计调用，分解提示与解析规则保留。
- 新初检只传原问题/原文/目录/版本白名单，不传旧答案、Gold、评分点或分解结果；原文由同库身份校验核对。
- 决策最多6请求、工具最多3行动、回答最多4请求保持；加上真实初检的1次分解，全程最多11次。为保证这个上限，Agent入口保持rewrite/HyDE关闭；原RAG可选增强保留。
- 每次请求前写账本；协议绑定问题、代码与公开API选项。已使用目录拒绝重跑；失败/截断/复核失败保留，不能自动改走RAG掩盖失败。
- 默认Agent使用all-papers-8-20261020，其他版本在调用前拒绝；默认RAG仍读取原激活指针。八篇模式不会改active_kb.json；比较两路时应显式指定同一八篇库。
- Agent返回的context/ledger/selected_ids对齐实际最终引用，initial_selected_ids保留初检排名；初检诊断不冒充Agent扩展后的固定Top-K指标。

## 真实命令行冒烟结果

| 已知题 | 结果 | 分解/决策/回答请求 | 工具行动 | token |
| --- | --- | ---: | ---: | ---: |
| Transformer优化器与常数 | review_passed，事实/引用核对通过 | 1 / 2 / 2 | 0 | 8,761 |
| 原Mistral 7B训练token/上下文 | model_stop，insufficient_evidence，未猜值 | 1 / 2 / 0 | 0 | 4,870 |

全轮8个实际模型请求、8个HTTP POST，输入12,689、输出942，合计13,631 token；全部stop，失败/缺失usage/自动重试0。两次CLI均退出0。总进程约78.185秒，包含两次独立加载与检索；不是延迟对照、并发或P95。

可答题实际用英文作答，未遵循生成提示的中文要求，记为展示一致性瑕疵，未针对冒烟题调提示。两题0工具行动：这次真实检查验证直接回答/停止分支，搜索执行和追加引用在新增离线main行为测试覆盖，历史工具实测仍单独保留。模型复核与人工核对均不等于独立盲评或新题泛化。

## 使用方式

Mac项目根目录，环境和本机代理按已有指南配置；受控线程环境沿用项目记录：

```bash
.venv/bin/python main.py
.venv/bin/python main.py --mode agent
.venv/bin/python main.py --mode agent --output-dir logs/my-agent-run "你的论文问题"
```

默认两条无问题参数的命令会交互读取问题。Agent自动记录到logs/agent_runs/下的新目录，显式output-dir需为空；完整日志含protocol、actual_chat_calls、retrieval、loop、answer与result。已有结果可直接阅读，勿为恢复上下文重跑模型。

```python
from main import main
result = main("你的论文问题", mode="agent")
# 同八篇库的固定RAG对照：
result = main("你的论文问题", kb_version="all-papers-8-20261020", mode="rag")
```

后续重点是按新优先级提前区分必答/补充，再做新留出质量与成本验证。自动路由、其他库的Agent工具支持、联网和UI均未包含在本次。

证据：[测试日志](all_tests.log)、[冻结协议](frozen_protocol.json)、[真实汇总](smoke_summary.json)、[原文核对](manual_review.md)、[HTTP记录](http_events.json)、[源码检查](source_checks.json)、[最终核验](verification.json)。
