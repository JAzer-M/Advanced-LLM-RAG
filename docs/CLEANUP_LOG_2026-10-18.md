# Advanced-LLM-RAG 目录清理日志

日期：2026-10-18。授权范围：用户要求清理测试内容、冗余代码和已无用途的内容，并保留清楚的代码风格与必要注释。

## 清理结果

移除 31 个废弃 Python 文件，共 4406 行；另将 124 个旧评估输入/产物归档后从原位置移除。合计从原位置移除 155 个文件。旧 PROGRESS 额外收入归档，所以历史压缩包共 125 项。以上行数只计算删除的 Python 文件，不把存续文件的局部删改重复计入。

另外移除了项目自己的 4 个 __pycache__ 目录、共 36 个缓存文件；没有清理第三方环境缓存。

当前保留 26 个 Python 文件。根目录 Python 入口为 main、llm、list_api_models、两个索引构建脚本；`evaluation/` 只保留四个必要评估/核对文件。当前 DeepSeek 结果集中到一个目录，失败过程也保留。

详细逐文件路径、大小、原 SHA-256、恢复来源和目录移动见 [机器可读清单](CLEANUP_MANIFEST_2026-10-18.json)。

## 删除了什么，为什么

| 类别 | 内容与依据 |
| --- | --- |
| 根目录一次性代码 | demo_grounded_qa、diagnose_entity_attribution、diagnose_q5_evidence、diagnose_q5_numeric_pipeline、diagnose_single_chunk、generate_q5_answer_baseline、inspect_hyde_misses：依赖冻结样例，功能已进入正式证据流程或实验已结束 |
| 旧测试 | 根目录 3 个 HyDE test 文件、evaluation 中 6 个 test 文件；已先执行相关组件验证，按本次要求移除 |
| 重复评估/诊断入口 | compare_api_answers、diagnose_chunk_241、run_citation_repair、run_context_selection_evaluation、run_grounding_generalization、run_hyde_evaluation、run_kimi_diagnostics、run_main_evidence_smoke、run_production_hyde_claim_evaluation、run_production_topk_evaluation：旧阶段专用逻辑多份重复维护，当前真实运行/固定证据对照合并到一个收集器 |
| 兼容壳 | evaluation/citation_checks.py 只转导一个函数；存续调用直接使用 src.citation_validation |
| 已退出主线的实现 | evaluation/baselines 中的旧 Qwen 生成实现和旧数值解析副本；当前 API 与证据模块均无调用 |
| 无调用原型 | src/pdf_loader_v2.py 未接入构建链路；src/chunking.py 的 Fixed 分块无存续调用或构建入口。保留正式 PDF Parser、Semantic 和 Recursive 构建 |
| 旧数据与产物 | 旧候选池、claim/grounding 专用样例、旧阶段报告和反复生成的中间 JSON/MD/日志；归档原始内容，不伪造或抹去失败实验 |

没有仅凭文件名删除生产模块：先检查实际 import/调用关系，再执行删除，最后核对所有存续的本地模块导入。

## 存续文件的局部整理

- `main.py`：删除无调用的实验上下文选择器和无用 dedent import；保留正式全局重排、Top-10、证据视图及原文来源；更新过时的注释。为评估器允许直接传入 query，日常交互输入不变。
- `src/hyde.py`：删除第一次 return 之后不可达的重复生成与 return；没有删掉可选 HyDE 功能。
- `src/query_decomposer.py`：重复两遍的相同示例保留一遍。最终六题的分解与检索结果保持一致。
- `llm.py`：保留共享 API 入口，移除指向已删除本地模型实现的过时说明。
- `requirements.txt`：移除只为历史本地生成保留的 accelerate/torchvision 声明；保留检索所需 torch、transformers、sentence-transformers 等。没有卸载现有虚拟环境中的库，也未宣称依赖已完全锁定。
- `evaluation/run_answer_evaluation.py`：合并真实全流程与固定证据对照；删掉对历史 integration/checks JSON 的强制依赖及 unittest.mock 输入替换；失败保存调用与错误，不会把旧成功 MD 留作新失败结果，也不会隐式无限重试。
- README、PROGRESS、API 指南：更新实测状态、入口和历史归档位置。旧交接全文保留在历史压缩包中。

上述提示词修正属于本次调试，详见 [调试日志](DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md)。其余修改保持原有函数式结构，不引入框架或通用配置层。注释用于解释证据范围、分支作用及失败处理。

## 保留了什么

论文与 9 个数据文件、API 本地配置、embedding/reranker 缓存、`.venv`、`.git`、`.idea` 均保留。遍历检查时，`.venv` 约 3454 MiB，是正常依赖环境，不能按“冗余代码”删掉；第三方包附带的测试也未清除。项目自己的 test_*.py 已移除。

保留 `run_answer_evaluation.py`、`run_evaluation.py`、`check_evidence.py`、`metrics.py`，因为它们分别承担回答留档、检索方法对照、Gold 原文核对和指标计算，是仍有用途的工具。用户不需要为了日常提问运行它们。

旧方法对照的 Top-5 参数没有强行改成主流程 Top-10；README 已说明两种结果不能混算。没有运行这些脚本去覆盖历史候选池。

## 归档与恢复

项目内的 `docs/history/20261018_experiments.zip` 为历史结果归档，共 125 项、483238 字节，保存原仓库相对路径，CRC 校验通过。解压到独立目录，可继续核查 Kimi、2B 和此前失败案例；该归档不包含废弃 Python 源码。

清理前完整代码/文档/评估产物快照位于：

`C:/Users/J/.codex/visualizations/2026/10/18/01a14f0e-47d4-7f62-8fca-0b58c78658d1/Advanced-LLM-RAG-backup/before_cleanup.zip`

同目录的 manifest.json 记录快照哈希，protected_hashes.json 记录配置与数据哈希。该快照在调试提示已经修改、目录清理尚未执行时创建，包含所有被删除的 Python 文件。恢复时按原相对路径选择需要的文件，避免整包覆盖当前有效修改。Key 配置文件没有收入归档。

执行环境第一次临时目录快照无法跨后续沙箱调用访问，实际清理前已改存以上稳定、可写位置并验证可读，机器清单使用这个位置。

## 验证与边界

1. 清理前 34 个既有组件测试通过；清理后不保留测试脚本。
2. 所有 26 个存续 Python 文件语法与本地导入检查通过。
3. 六题真实主流程最终完成；q5 的一次 HTTP 503 原样保留，并仅定向重跑一次。
4. 六题 Top-10 和完整 context 与清理前相同；143 条最终证据记录通过类型/原文校验。
5. 从三篇 PDF 重新执行解析、Semantic 分块、embedding 与内存 FAISS 构建；378 条分块完全相同，向量最大绝对差为 0.0；临时保存/加载往返通过。
6. 本地配置和全部数据文件哈希保持一致；历史与清理快照压缩包完整性通过。
7. 最终六题记录的代码/输入哈希仍与当前文件匹配；维护中的 Markdown 链接和 git diff --check 通过；公开文件及历史归档未出现实际配置 Key。最终核对记录见 evaluation/results/deepseek_v41/checks/final_audit.json。

检查针对当前环境与现有案例，没有运行全新环境重装、全部历史参数实验或可选 HyDE/改写分支。语义评价仍有人工作出的边界判断，不能由引用格式检查替代。

未执行 Git 提交或推送；原有 staged/unstaged 成果由当前工作树与快照保留。已删除的历史工具不再属于当前可运行入口，不应按旧日志中的命令直接调用。
