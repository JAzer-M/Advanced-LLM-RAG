# P2 第一步：需求分析与首轮证据检查

日期：2026-10-20（Asia/Shanghai）。本轮按用户确认实现独立入口，复用P1三题的真实原文，最多6次API调用；不执行补查工具，不生成新的最终答案。

**实现与本地验证完成；语义验收尚未全部通过。** 三题均正常返回结构化结果，人工核对h01/h11通过、h10不通过。新增20项测试及原有79项全部通过，共99项。实际6次chat、9,784 token、零本地自动重试；行动执行数为0。

## 1. 实现内容

新增[agent.py](../../../agent.py)，沿用普通函数、字典和列表，复用现有`src.api_llm`配置与调用方式，无新运行依赖。

- `plan_requirements`：仅根据用户问题列出1～6条需求，记录主体、需要建立的事实和原问题范围引文。
- `assess_evidence`：读取生成的需求、P1原始片段及完整八篇目录；逐项输出supported/partial/missing/conflicting、原文依据、缺口和一条行动建议。
- 行动仅允许`answer/search/read_neighbors/stop`，分别校验所需参数；本轮只保存建议，不执行它们。
- 检查需求ID、原问题引文、主体字面出现、当前chunk ID、原句存在性、来源、工具参数及是否仍有缺口。NFKC/空白/大小写归一化与现有项目口径一致。
- 调用前后逐次保存提示、响应、模型标识、token用量和耗时。输入、源码与公开API选项相同才允许续接；已完成请求复用，失败和格式错误不自动重试；总上限6次。

**原句出现、主体名字出现，都不能证明关系绑定或语义正确。** h10正是这一限制的实测失败，不能把程序校验通过解释成语义通过。

## 2. 输入与范围

显式使用`all-papers-8-20261020`：1397 chunks、384维、8篇论文。原三篇激活指针保留。

复用P1的h01/h10/h11 `citation_registry`全部原文，分别12/10/10段，包含原账本附加片段，保持原ID、来源、页码、标题和正文。只重新组织这些原文供检查器读取，不重跑Dense/BM25/BGE，也不复用旧生成答案、旧分解或数值规则提示。

需求分析模型只看到问题；证据检查模型只看到问题、当前生成的需求、原始片段和八篇论文目录。Gold、reference_points、题型、旧答案和本轮人工预期均不进入模型提示。输入预检核对了旧记录与当前配对知识库的SHA-256、ID及正文一致性，详情见[input_preflight.json](input_preflight.json)。运行前人工预期单独冻结在[protocol_before_run.json](protocol_before_run.json)。

h01/h10/h11现在用于开发诊断；原P1文件与评分未改。后续独立验收须另冻结新题，不能把调试这些题后的表现叫独立留出效果。

## 3. 三题实际结果

| 题目与逐题日志 | 生成需求数 | 模型状态 | 建议行动 | 结构/引文校验 | 人工语义验收 |
| --- | ---: | --- | --- | --- | --- |
| [h01](h01.md)：标签平滑 | 3 | supported×3 | answer | 通过 | 通过：69/70支持数值与指标方向 |
| [h10](h10.md)：RAG/Self-RAG评测判据 | 5 | supported×1、partial×4 | search，目标RAG论文 | 通过 | 不通过：PopQA范围错绑，搜索参数延续错误 |
| [h11](h11.md)：Mamba规格 | 3 | missing×3 | stop | 通过 | 通过：原文不在目录内，不填参数数值 |

三题程序执行3/3成功；完整语义验收2/3。行动大类分别为answer/search/stop，但h10的search参数不正确，不能称三题决策全部正确。这里是三道已知开发题的诊断结果，不是总体Agent准确率或独立盲评。

h01：需求值0.1由69支持；perplexity变差、accuracy/BLEU改善由70支持。h11：训练数据量、隐藏状态维度及主来源缺失都被识别，明确停止。

### h10保留的具体失败

原题将PopQA/TriviaQA附着于Self-RAG。模型的r3却写成：

> 确定 RAG 与 Self-RAG 各自针对 PopQA 的 correctness criterion 是如何界定或应用的

其`question_quote`只是原题中的`for PopQA`。这段字符确实存在，但不能证明它也修饰RAG。模型随后建议：

> RAG 在 short-answer open-domain QA（PopQA、TriviaQA）评估中采用何种正确性判据（exact match 还是 answer inclusion）？

搜索文件`2005.11401v4.pdf`正确，查询范围错误。模型同时识别出了RAG评测判据未被当前片段建立，Self-RAG包含式判据由1003支持；这些正确局部判断不能抵消范围漂移。

另一个问题：r1引用763中的训练负对数似然并标partial。训练目标不能作为评测正确性判据的部分支持，这个状态偏宽松。两处都说明还需要语义约束，不能仅靠名字/引文存在校验。

所有原始输出保持不变，人工判定另存[manual_review.json](manual_review.json)。本轮6次额度已用完，没有追加提示修改后的付费重跑；没有把失败隐藏为通过，也没有让错误查询实际执行。

## 4. 实际成本

| 项目 | 实测值 |
| --- | ---: |
| 需求分析 / 证据检查 | 3次 / 3次 |
| 实际chat调用 | 6次，全部stop |
| API失败 / 本地自动重试 | 0 / 0 |
| 代理报告输入 / 输出token | 7,850 / 1,934 |
| 合计token | 9,784 |
| 三题程序耗时合计 | 16.983秒 |
| API耗时合计 | 16.958秒 |
| 补查 / 邻段读取 / 最终回答生成 | 均为0 |
| 完成后续接新增调用 | 0 |

沿用现有请求模型`cn:deepseek-v4.1-flash`、thinking disabled、temperature=0、max_tokens=4096；实际模型标识和逐调用响应见[真实调用](run/actual_chat_calls.json)。标识不独立证明上游权重。由于本轮复用检索结果，没有实际检索或最终生成，耗时不能与P1完整main直接比较。

## 5. 验证与保护

- 全部99项unittest通过，原79项+新20项；网络连接禁止，无真实API。新增检查包括伪造原句、引用序号冒充chunk ID、未知动作/来源、证据缺失却提出完整回答、跨来源邻段、预算耗尽、中断恢复、失败保存和输入变化拒绝续接。
- 真实运行的10个引文引用均按当前chunk校验，来源/页码可还原，原句归一化匹配。该检查不等同引用语义或需求范围正确。
- 1,986项旧文件在源码新增与运行后哈希不变，包含原main、知识库配对文件、激活指针、旧题/Gold和旧实验；最终只更新原README/PROGRESS进度说明，并新增独立文件。
- 完成后用禁止新调用的桩再次进入相同输出目录，新增调用0，原调用审计hash相同。
- 私有配置和凭证未进入产物；没有提交或推送。

测试日志见[full_tests.log](full_tests.log)，运行核对见[verification.json](verification.json)，发布核对见[delivery_verification.json](delivery_verification.json)。本轮程序返回completed指结构化诊断完成；人工语义是否通过以manual_review为准。

## 6. 下一步

**P2第一步的程序和诊断记录已交付，h10语义验收待修正。** 接入自动工具之前，先修主体与数据集/条件的绑定，审查无关背景是否被误算为partial支持；必要时让证据检查器拒绝超出问题范围的需求。先在保存输出上定位和补本地约束，再用预先限定的新调用预算复核，不能宣称修改提示后已验证有效。

随后才实施“执行建议工具→再检查证据”的受预算约束循环。本轮未完成自动检索Agent，未重新生成最终答案，因此不报告新的P@10/nP/Recall或回答质量提升。

## 7. 文件与复现

- [独立入口](../../../agent.py)、[新增测试](../../../tests/test_agent_step1.py)。
- [运行前预期](protocol_before_run.json)、[实际运行协议](run/protocol.json)、[白名单输入](run/inputs.json)。
- [h01](h01.md)、[h10](h10.md)、[h11](h11.md)逐题需求、证据、来源/页码与建议；原始JSON在`run/`。
- [调用审计](run/actual_chat_calls.json)、[汇总](run/summary.json)、[逐处引文定位](verified_quote_provenance.json)、[人工审阅](manual_review.json)。
- [旧输入hash](baseline_hashes.json)、[本地测试](full_tests.log)、[运行后核对](verification.json)、[发布核对](delivery_verification.json)。

入口示例（新输出目录会发生新调用；完成目录仅续接核对）：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python agent.py \
  --replay-dir evaluation/results/holdout_v1_20261020 \
  --question-id h01 h10 h11 \
  --output-dir evaluation/results/agent_step1_20261020/run
```

上述已完成目录在代码、输入和公开API选项不变时不会重复请求；发生变化则显式拒绝续接。这里的缓存只用于本步诊断，不冒充全流程Agent执行。
