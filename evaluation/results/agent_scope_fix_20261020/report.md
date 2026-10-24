# P2.1：需求范围与证据状态修正日志

日期：2026-10-20（Asia/Shanghai）。承接用户“接下来先修正”的授权；只修 P2 第一步，不接自动工具循环。

**本轮已落地范围与状态约束，h10 的定向证据复核通过：RAG 判据 missing、Self-RAG 判据 supported；搜索文本不再把 PopQA／TriviaQA 转给 RAG，训练损失不再计为判据的部分支持。** 最终 123 项离线测试通过，原 99 项加新 24 项。

本次累计 7 次真实 chat、13,504 token，全部 stop；自动重试、工具执行、新检索、最终答案生成均为 0。原定总量 6 次，因第 6 次仍暴露问题，在继续前明确说明仅追加 1 次、调整总上限为 7 次；不是静默重试或遗漏失败账单。

**验收边界：**最后一次是 h10 的单次新证据检查，规划锚点复用本轮先前真实响应；不是新版抽取式规划接口的三题全新端到端通过。最后一次原始程序记录因局部校验过严被标 failed；修正比较例外后，最终代码对完全相同提示和保存的真实响应离线回放通过。原 failed 记录未覆盖，也没有第 8 次调用。

## 1. 为什么不能只再加一句“保留范围”

旧规划器自由生成中文 need；即使 question_quote 来自原题，need 仍可能把 Self-RAG 的条件复制给 RAG。检查器又能把名字出现、原句存在、scope_check.valid=true 当作通过，搜索查询还可继续自由改写。

实测首轮加提示和字段校验仍不够：

- h01 的第二项用“the paper”回指唯一论文，新校验过严，错误地拒绝了可还原的范围引文。
- h10 的自由 need 仍把 PopQA／TriviaQA 加给 RAG；随后把 Self-RAG 判据标 partial，理由却是另一项 RAG 缺证据。
- 一个布尔 scope_check 不能代替关系绑定检查。模型仍可能自称通过。

因此本次把操作需求改为原题片段，并隔离逐项证据检查，同时在本地拒绝跨需求的条件或缺口。

## 2. 实际改了什么

仅修改生产入口 [agent.py](../../../agent.py)；现有 main、检索、索引、题集和生成主线未改。沿用普通函数、字典、列表，无新依赖。 本次修的是独立 Agent 需求／证据判断；P1 中固定 main 的旧分解范围漂移仍作为历史缺陷保留，不能说原固定 RAG 的 h10 最终答案已修好。

| 改动 | 实际行为 |
| --- | --- |
| 抽取式需求 | 规划模型只返回 id／subject／question_quote；程序将原题片段作为 need，不使用自由转述来驱动判断或查询。 |
| 主体边界 | RAG 不再仅匹配 Self-RAG 的后缀；范围引文应包含自己的主体，不混入另一已声明主体。 |
| 有限回指处理 | 同一唯一主体、片段含“the paper／the authors／该论文／该文”、且前方只有一个可定位先行词时，扩展连续引文；多主体或不明确时拒绝。不是通用指代消解。 |
| 逐项输入隔离 | 原题供规划和本地绑定使用；事实检查模型收到绑定需求、预计算查询、原文、完整目录，不再收到完整比较题供其重新解释。 |
| 明确支持部分 | supported／partial 必须说明 supported_part；missing／conflicting 不得假称某部分已建立。相关背景不是部分支持。 |
| 跨需求缺口拦截 | 对支持内容／gap 做保守名称检查，拒绝借用另一项的主体或条件；显式比较可以提到另一方法，但不因此获得另一方法的数据集条件。 |
| 绑定搜索文本 | search 一次只指向一个未满足需求，query 必须精确复制该需求预计算的字符串；不得追加数据集或猜测答案。 |
| 引文来源 | 原句存在性仍校验；若响应额外给 source，则验证其与真实 chunk 匹配，不能忽略错误来源。 |
| 失败与预算 | 原有断点、源码／输入／公开选项绑定和不自动重试继续保留；不让校验失败进入工具执行。 |

scope_check 仍是模型的一项自查输出，并非语义证明。本地词法检查也不能证明所有自然语言关系正确，复杂关系仍需人工核验和后续新题测试。

## 3. 三个真实调用阶段，全部保留

| 阶段 | 新 chat | 输入／输出／总 token | 实际结果 |
| --- | ---: | --- | --- |
| 首轮三题 | 5 | 6,188／1,057／7,245 | h01 规划因回指被拒；h10 输出有范围／状态错误；h11 正确 stop。 |
| 绑定片段后复核 h10 | 1 | 2,756／372／3,128 | 查询范围已受约束，但 RAG gap 仍借用数据集，Self-RAG partial 借用另一项缺口；人工不通过。 |
| 隔离需求后复核 h10 | 1 | 2,719／412／3,131 | RAG missing、Self-RAG supported、query 不带错误条件；原局部 guard 误拦比较缺口，随后仅修改校验并离线同输入回放。 |
| 合计 | **7** | **11,663／1,841／13,504** | API 均 stop；不把程序／语义失败混成 API 服务失败。 |

实际请求在 API 入口和 HTTP 请求入口分别审计，两者提示哈希、计数和 usage 一致。每次提示修改后的定向复核都有独立冻结协议；它们是人工诊断修订，不是隐藏自动重试。

首次受控诊断的单批上限仍为 6；本轮累计是三个协议下的 5＋1＋1。没有运行整套 RAG 或重付旧 12 题的费用。没有可靠单价，不根据代理 credit 字段推测人民币／美元金额。

## 4. 最后一次 h10 到底验证了什么

原问题：

> For short-answer open-domain QA, how does the correctness criterion reported by RAG differ from the criterion used by Self-RAG for PopQA and TriviaQA?

操作需求来自先前真实规划响应的三个白名单字段，丢弃自由中文转述，程序生成：

| ID | 主体 | 绑定片段／need | 最终状态 |
| --- | --- | --- | --- |
| r1 | RAG | how does the correctness criterion reported by RAG differ | missing；evidence=[] |
| r2 | Self-RAG | from the criterion used by Self-RAG for PopQA and TriviaQA | supported；chunk 1003／1002 |

RAG 的训练负对数似然、TriviaQA 训练过滤没有被计入正确性判据支持。Self-RAG 的包含式判据和任务归属由原文支持，没有再因为 RAG 缺证据被降为 partial。

绑定查询：

```text
RAG: how does the correctness criterion reported by RAG differ | how does the correctness criterion reported by RAG differ
```

建议是 search、requirement_ids=[r1]。query 不含 PopQA／TriviaQA，不添加 exact match 等答案猜测。source=null 是当前协议允许的全库查询建议，尚未执行；不能说已经定向检索到 RAG 原文，更不能说补到了缺失判据。查询重复片段属于当前兼容格式，后续工具接入时可单独简化。

最后返回的 r1 gap 提到与 Self-RAG 的比较。由于 r1 原题片段含 differ，允许说明比较仍不能完成是合理的；但仍不允许把另一个方法的数据集变成 r1 的条件。本轮增加正反回归区分这两者，避免为接受一个样例而撤掉范围保护。

两处支持引文均核对 source／page／chunk／原句：[引文核验](verified_quotes.json)。缺失的 RAG 判据没有用 Gold 或模型常识补入。

## 5. h01／h11 回归的边界

- **h01：**使用本轮真实规划响应中的片段，验证唯一论文先行词的扩展和原题归属。没有对最终修订后的整条链新生成 h01 证据检查；不宣称它本轮最终端到端通过。
- **h11：**首轮实际产生 missing／missing 和正确 stop；目标 Mamba 论文不在八篇目录。最终校验器对保存的判断回放通过；这也不是新版规划接口的新整轮运行。
- **h10：**最后一份实际 API 响应，加最终校验器的精确提示回放及人工核对，验证此次两个具体问题已修正。

三题都是开发／回归案例，不是新留出集。新抽取式规划 JSON 协议的真实模型输出尚未完整验收，不能将本轮写成“最终三题语义 3/3”或完整 Agent 收益。

## 6. 本地测试、精确回放与资产保护

1. 旧代码上三项范围／查询回归实际失败，见[红灯日志](scope_red.log)。
2. 最终 **123 项 unittest 通过**，其中原 99 项和新增 24 项；禁止网络连接，见[最终测试](tests_final.log)、[计数与源码 hash](tests_final.json)。覆盖名称边界、范围引文、抽取绑定、回指歧义、跨项缺口、合法比较、不得转移数据集、绑定查询、引用来源、失败留档和预算。
3. 逐项隔离后，原三个模拟案例的事实输入若完全相同可合法复用响应；预算测试改为各有不同原文的案例，继续验证真实不同输入的 6 次上限。中间测试失败原文保留，不修改生产缓存逻辑来迎合测试。
4. 最后一次模型提示与最终代码重新渲染提示逐字相同；仅修正过严的局部比较校验。保存响应离线回放通过，新增 API 为 0；前一份确实错误的 h10 响应仍被拒绝，见[离线审计脚本](verify_scope_fix.py)、[接受的回放](accepted_h10_replay.json)、[核验结果](verification.json)。
5. 最后调用后源码的变化仅在校验逻辑；调用时源码与最终交付源码分别保留，不冒充最终源码在第 7 次调用前就已冻结。
6. 发布前 2,075 项原项目文件哈希均未变；发布允许更新 agent.py、原 Agent 测试、README／PROGRESS，新增测试／日志。main、全部旧题／Gold、旧实验、配对知识库和默认三篇激活指针保留；发布后核对另存 delivery_verification.json。
7. 私有配置和凭证正文不进入快照／报告；真实运行只读取现有本地配置，没有请求新 Key，没有提交或推送。

## 7. 如何继续

**两个具体问题的代码修正和 h10 定向复核已交付；新版规划到证据检查的完整三题真实回归尚未补。** 下一小步先用另行冻结的小预算验证新抽取式规划协议和 h01／h10／h11 全链路，再接 search／read_neighbors 的真正执行。不要把旧完整目录拿到新源码下强行续接；源码 hash 改变会明确拒绝。

之后才进入“执行建议工具 → 合并实际原文 → 再检查 → 有预算地回答／停止”。本轮没有新 Precision／nP／Recall 或最终答案质量提升数据，不修改固定 RAG 的已有结论。

## 8. 日志目录导航

- `run/`、[首轮原始调用](run/actual_chat_calls.json)、[首轮 HTTP 审计](actual_http_calls.json)：前 5 次，失败原文保留。
- `recheck/`：第 6 次，已绑定片段但人工语义不通过。
- `isolated_recheck/`：第 7 次及调用时原始 failed 记录，输入隔离后的真实响应未改。
- [accepted_h10_replay.json](accepted_h10_replay.json)：最终校验通过的离线回放，标明额外调用为 0。
- `source_before/`、`source_snapshot/`、`final_source_snapshot/`、`isolated_source_snapshot/`、`delivery_source_snapshot/`：原版、各修订及最终代码；当前使用 delivery_source_snapshot。
- [本轮人工核对](manual_review.md)、[完整核验](verification.json)、[最终测试](tests_final.log)、[项目旧资产清单](baseline_hashes.json)。
- [原 P2 首次实现与 2/3 结果](../agent_step1_20261020/report.md)、[P1 基线](../holdout_v1_20261020/report.md)、[最新项目进度](../../../PROGRESS.md)。
