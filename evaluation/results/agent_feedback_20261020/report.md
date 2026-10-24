# P2.3：单次执行与反馈接线及真实检查

日期：2026-10-20（Asia/Shanghai）。用户授权先完成执行与反馈，观察结果后再加循环。本轮代码及离线控制流程通过；真实搜索/合并成功、模型反馈已返回，但未通过本地校验，效果未验收。

## 代码实现

在[agent.py](../../../agent.py)新增两个普通函数，保留现有规划、范围校验、证据检查和本地工具实现。

- `execute_action(action, resources)`：接收已通过`validate_assessment()`的行动。search按原query/source调用搜索；read_neighbors按原chunk_id/source读取前后各一段。answer/stop返回未执行，不生成答案。
- `merge_evidence(evidence, resources, tool_result=None)`：核对知识库版本、manifest、配对文件哈希以及片段原文/页码/来源/标题；按版本和chunk ID去重，保留旧证据在前、追加新段。只向模型传原文字段和版本，工具分数及轨迹留在日志。
- `run_diagnostics(..., execute_once=False, resources=None)`：默认诊断行为保留。新模式每题最多执行一个工具，合并原文后再次调用原`assess_evidence()`；反馈提出的下一行动只保存。单次模式最多两题，全批次最多六次API请求。
- 反馈最多32段/24000字符；超限报错，不静默删段或裁剪正文。工具执行前先落盘，完成后保存结果；中断可复用已完成调用和工具结果，未完成或失败的尝试不自动再执行。

整体为：规划 → 初次检查 → 执行一个工具 → 合并原文 → 再次检查 → 结束。当前仍没有自动行动循环或最终回答生成。

新增16项行为测试，**全部158项离线unittest通过**，失败/错误/跳过/网络请求均0。覆盖真实小型邻段读取与反馈、搜索分派、白名单输入、旧证据保留与去重、空结果、终止行动、校验失败、工具/API失败、精确中断续接和预算。见[测试汇总](tests.json)及[完整日志](tests.log)。

## 真实检查经过

使用已知开发题h10，知识库固定`all-papers-8-20261020`。原题询问RAG的短答案开放域QA评价准则，与Self-RAG对PopQA/TriviaQA所用准则的区别。本轮不是新留出、最终答题或固定RAG/Agent收益对照。

最初自动审批要求明确目的地与发送数据，拒绝发生在进程创建之前，未产生API调用。用户随后明确授权`http://127.0.0.1:7863/v1`、`cn:deepseek-v4.1-flash`，发送h10问题、需求、论文目录与论文原文，最多3次；提示词不含源码或私有配置。后续两次失败后的续接也分别来自用户明确指示，见[授权经过](authorization_history.json)。

| 尝试 | 阶段 | 实际结果 |
| --- | --- | --- |
| 1 | 新规划 | 正常返回，需求绑定通过 |
| 2 | 新的初次检查 | 正常返回，但把Self-RAG需求中的PopQA/TriviaQA条件转到RAG缺口，范围校验拒绝；未执行工具 |
| 3 | 复用P2.1已验收行动后的反馈 | 原样执行search并合并成功；反馈请求HTTP503，无模型判断 |
| 4 | 用户明确要求重发同一反馈 | 连接失败；lsof未发现7863监听 |
| 5 | 用户启动反代并要求继续检查 | lsof观察到wb2api监听7863；原样反馈提示正常返回stop，但partial/空gap矛盾被校验拒绝 |

初次失败完整保留在[run/h10.json](run/h10.json)及[原始两次调用](run/actual_chat_calls.json)。为隔离新接的执行与反馈，后续使用[P2.1已验收行动](../agent_p21_closeout_20261020/run/h10.json)，重新核对原题、需求、证据和版本后执行；未放宽校验，也未修改模型给出的query/source。因此，后续样例属于“已验收行动回放＋新执行/反馈”，不能称为全新自主链路通过。

HTTP503的原因未确认；其后连接失败与端口未监听的检查一致。恢复服务后已收到模型响应，没有依据把之前全部失败都归因于额度。

## 工具结果与模型反馈

回放行动为search，source=null，使用当时绑定的原查询：

```text
RAG: how does the correctness criterion reported by RAG differ | how does the correctness criterion reported by RAG differ
```

实际执行一次全库搜索，返回ID：1289、1130、788、786、1325、1235、1213、796、779、1326。10段均为原证据之外的新段，身份与配对库核对一致。保留原10段在前，合并后20段、8717字符。执行原文及合并证据见[saved_feedback_result.json](saved_feedback_result.json)；该文件status=failed表示之后反馈遇HTTP503，不表示其中已保存的工具执行失败。

用户恢复反代后的反馈输入与先前保存的反馈提示逐字一致，不重跑规划或搜索。最新[完整调用](proxy_restarted_calls.json)、[解码模型原文](feedback_raw_model_output.json)和[校验结果](proxy_restarted_result.json)均已保存。

| 需求 | 之前已验收判断 | 最新模型原始判断 | 核对结论 |
| --- | --- | --- | --- |
| r1：RAG评价判据 | missing | missing | 新检索没有带回直接说明该判据的原文，缺口仍在 |
| r2：Self-RAG在PopQA/TriviaQA的准则 | supported | partial，但gap="" | 引用1002、1003真实存在并支持所述事实；partial必须说明尚缺内容，空gap与状态矛盾 |

本地抛出`ValueError: gap must be a nonempty string.`，没有将该响应当成有效反馈写入`feedback_assessment`。未自动补写gap或把partial改成supported来通过验收。两个引用另经独立原文核对，见[人工审阅](manual_review.json)。

模型又建议search，type、需求ID、query、source和chunk_id与执行前相同，仅reason文字变化；该建议未执行。新增片段数量并不等于补齐关键证据，更不等于回答质量提升。

## 调用与成本边界

本轮及用户明确续接合计**5次API尝试、3次正常返回、2次连接/HTTP失败**。正常响应均finish_reason=stop，报告输入7437、输出893、合计8330 token。两次失败无usage，按未知保留；不把它们计为0 token，不推算价格。初次范围校验和最新状态校验虽失败，其已返回响应仍计入实际用量。

真实工具执行1次search，read_neighbors在本轮通过真实小型库离线测试覆盖；没有真实模型自然选择read_neighbors的新增实测。自动重试、自动行动循环、最终答案生成均0。汇总与逐次来源见[api_usage_summary.json](api_usage_summary.json)。

## 复现与保留

查看上述JSON恢复上下文，不需要重复调用。`run_one_step.py`、`run_saved_feedback.py`、`retry_feedback_once.py`、`retry_after_proxy_start.py`分别记录首次诊断、接受行动回放及两次人工续接，已有协议时拒绝自动重跑。源码快照保留在`source_snapshot/`。

需要未来新实验时可使用新输出目录和`agent.py --execute-once`；新命令会产生API请求，线程条件与示例见[README](../../../README.md)。源码哈希已变化，不能向P2.1旧目录续接；旧协议及结果保持原样。

修改范围仅agent.py、一个新测试文件、README、PROGRESS和代码阅读说明，以及本轮结果目录。main、两个工具、知识库、激活指针、旧实验、桌面纯路线图均保留。完整哈希与编译核对见[verification.json](verification.json)。

**当前结论：单次执行和合并能力已实现并实测，模型收到新证据后给出的反馈尚未通过验收。** 后续先查看本轮结果，再按用户指示处理反馈质量及循环的重复行动、无新增证据、预算和停止条件，本轮未加入循环。
