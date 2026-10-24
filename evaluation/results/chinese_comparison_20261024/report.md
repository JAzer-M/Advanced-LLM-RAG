# 中文比较需求绑定：修复与验证

2026-10-24，工作目录 `/Users/j/Desktop/Advanced-LLM-RAG`。

## 结论

修复了“VGG和RAG的区别是什么？”被投影成各自内部区别的问题。生产改动仅为 `agent.py` 中两处中文比较匹配规则；继续使用现有的逐方描述与原始问题引文。原失败回归已先红后绿，345项后端与27项网页测试通过。一次真实 main Agent 运行直接回答双方的任务与核心方法，核心引用经人工原文核对。

这是一道已知问题的开发回归，不是独立质量成绩。真实运行花费9次模型请求、34320 token，没有隐去一次复核登记失败及随后有限修订。

## 复现与根因

旧真实记录：`logs/webui/20261024T072352Z_42be3e80/`。原模型正确抽取了 VGG、RAG，并为两者保留完整原句。错误发生在后续确定性绑定：

```text
原题：VGG和RAG的区别是什么？
旧 need：vgg的区别是什么? / rag的区别是什么?
新 need：Describe vgg for the requested comparison.
          Describe rag for the requested comparison.
```

`isolate_need()` 的中文对称比较规则支持“有什么区别”，不支持后置“区别是什么”。未命中后落入普通共享谓语分支，只删除另一方名称，丢失跨方法比较的关系。于是原循环把 VGG 配置差异、RAG/DPR 差异当成支持证据，最终虽然 `review_passed`，仍然偏题。

先通过公开 `bind_requirements()` 接口重放原抽取，再通过 `plan_requirements()` 注入相同正确抽取作句型对照；不依赖检索、真实模型或事实答案。三个探针及正确抽取保存在 [diagnosis.json](diagnosis.json)，旧问题/答案保存在 [captured_failure.json](captured_failure.json)。

修复在匹配比较谓语、剥离比较谓语的两处都加入后置“是什么”。保留原 `question_quote`、每方主体及共享的明确方面，例如“在相同数据集上的性能”；其他主体独有条件继续由原校验隔离。

## 离线验证

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| 原中文问题回归，修改前 | 1项失败，精确复现单方“区别是什么” | [red_trace_test.txt](red_trace_test.txt) |
| 同一回归，修改后 | 1项通过 | [green_trace_test.txt](green_trace_test.txt) |
| 比较意图、比较上下文及主体范围 | 40项通过 | [targeted_tests.txt](targeted_tests.txt) |
| 全套后端行为回归 | 345项通过，0失败/错误/跳过 | [offline_tests.txt](offline_tests.txt) |
| 网页适配、模型配置、PDF入库 | 27项通过，0失败/错误/跳过 | [webui_tests_with_local_ports.txt](webui_tests_with_local_ports.txt) |

新增3项测试：原中文失败句、明确比较方面保留、旧单方错误需求被拒绝。已有英文概览、具体比较条件、非对称范围及 Agent/Auto 测试保持通过。

首轮网页测试有2项因沙箱不允许绑定临时本机端口而报 `PermissionError: Operation not permitted`；在允许本机端口后仅重跑27项网页测试，通过。没有为绕过失败而改生产代码或测试。首轮输出与 [offline_test_summary.json](offline_test_summary.json) 保留；最终状态见 [final_offline_test_summary.json](final_offline_test_summary.json)。这些测试使用模型替身及本机模拟HTTP，不能代替真实回答质量验证。

可复现命令：在项目根目录使用 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests` 环境，分别运行：

```sh
.venv/bin/python -B -m unittest test_comparison_intent test_comparison_context test_agent_scope -v
.venv/bin/python -B -m unittest discover -s tests
.venv/bin/python -B -m unittest webui.test_server webui.test_config webui.test_library
```

## 一次真实 main Agent 开发回归

运行前冻结 [验收条件](live_criteria.json)，只向模型提供原问题、需求、库目录和真实原文，不提供旧答案或人工验收结论。使用网页当前9篇/1767段版本 `webui-72bf8b69e9cf45f28135637e5ead075c`，请求模型 `cn:glm-5.3`，9次响应均报告 `glm-5.3`。原调用参数保持；本次关闭arXiv，模型请求上限11次，不自动重试。

| 项目 | 实际结果 |
| --- | --- |
| 状态 | completed / review_passed / answer_ready |
| 耗时 | 102.13秒，包含本地资源加载及检索 |
| 模型请求 | 9次：1次分解、4次决策、4次回答/复核 |
| token | 输入29853、输出4467、合计34320；usage缺失0 |
| 工具行动 | 1次 read_neighbors，为VGG描述补充真实相邻原文 |
| arXiv / 自动重试 / 模型失败 | 均0；9次完成原因均stop |

最终回答直接比较：VGG是面向视觉分类的深度卷积网络，RAG检索文本文档并将其作为生成上下文。核心支持来自 VGG 第8页分类任务、第3页3×3堆叠卷积，以及 RAG 第2页方法描述；没有再用 VGG 内部配置、RAG/DPR 的差异代替原问题。逐项人工核对与原文见 [manual_review.json](manual_review.json)。附带的D/16权重层及best-performing只按所引分类/定位实验段落的上下文理解，不扩大为所有VGG设置的全局优劣结论。

首轮回答复核有一次登记错误：`Review cites a source not cited by its answer quote.` 原有校验拒绝该复核，并执行一次有限修订和再复核，最终通过；因此回答阶段实际4次调用。初稿、失败复核、修订及再复核均在 [回答记录](live_agent/answer/question.json) 与 [原始调用](live_agent/answer/actual_chat_calls.json) 中保留。最后一次复核仍有JSON代码块外壳，Claude此前增加的兼容解析继续有效。

旧中文Agent运行是133.77秒/7请求/31338 token，流程通过但内容偏题。本次新鲜分解/初检的片段与旧运行不同，不能把耗时或成本差异归因为严格受控收益；没有重算旧分数。完整结果见 [live_summary.json](live_summary.json)、[运行协议](live_agent/protocol.json) 和 [真实结果](live_agent/result.json)。

## 改动与保全边界

本轮仅修改 `agent.py`、`tests/test_comparison_intent.py`、`PROGRESS.md`，并新增本结果目录。开始前保存4332个既有文件的哈希及相关源码快照；完整核验见 [verification.json](verification.json)，本轮差异见 [task_changes.patch](task_changes.patch)。Claude此前未提交的前端、语言与JSON兼容修改均作为本轮基线保留。

检索参数、提示词、模型配置、知识库与指针、前端及旧实验未作本轮修改；没有提交或推送。真实验证仅覆盖这一道中文Agent问题，其他路径由离线回归覆盖，未另跑真实Auto或英文问题。本次修复的是现有相邻主体对称比较中的具体句型，不宣称覆盖所有中文表达，也不替代独立题集验收。
