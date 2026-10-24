# Advanced-LLM-RAG

面向科研论文的问答项目：PDF 解析、Semantic 分块、Dense/BM25 混合检索、RRF 融合、问题分解、BGE 重排和带引用回答；本地 Agent 可按证据缺口搜索与读取邻段。

**当前：Auto比较意图和过度升级已修复，331项离线回归通过。** 同一用户VGG/RAG问题从101.85秒/8请求/28092 token降到30.98秒/2请求/4037 token，主要任务与方法比较有原文支持；附带训练细节的引用仍待完善。网页已恢复，可双击[Mac启动文件](ui_prototype/start.command)。这是同题开发验证，不是独立准确率；五轮合计21请求/54187 token及失败均留档。CLI默认auto，Python函数默认rag。[修复与全部成本](evaluation/results/auto_comparison_20261023/report.md) · [后端结果字段](docs/BACKEND_RESULT.md) · [此前故障交付](evaluation/results/backend_reliability_20261023/report.md)。

[当前进度与下一步](PROGRESS.md) · [文档导航](docs/README.md) · [量化结果](docs/PROJECT_METRICS.md) · [实验目录](evaluation/results/README.md) · [预期全流程](docs/PROJECT_WORKFLOW.md)

## 本地网页试验版

在项目根目录运行`.venv/bin/python ui_prototype/app.py`，浏览器打开[http://127.0.0.1:8848](http://127.0.0.1:8848)。可以回放三个真实案例、输入问题、选择三种模式、查看答案/引用/运行过程和成本。回放不调用模型，点击实时运行才使用现有API；联网默认关闭，界面固定使用八篇库，不改变激活指针。

一条真实RAG提问已从网页完成：VGG步长和padding均为1像素，引用第2页；2模型请求、2805 token、约15.3秒，无arXiv请求。这是首次界面验收记录；后续比较题后端改动见上方当前状态。尚未做正式发布或持久会话。[启动说明](ui_prototype/README.md) · [本轮验收](evaluation/results/ui_prototype_20261023/report.md)

## 运行

本机环境为 `.venv` / Python 3.11.9，Embedding 和 BGE 使用 CPU；生成及问题分解走本机反代。新环境安装 `requirements.txt`，现有环境与配置无需重建。首次配置参照 `api.example.json` 填写本地 `api.local.json`，已有配置不要覆盖。启动本机反代后，在项目根目录执行：

```bash
.venv/bin/python main.py --mode auto "What batch size does DPR use?"
.venv/bin/python main.py --mode agent "What batch size does DPR use?"
.venv/bin/python main.py --mode rag --kb-version all-papers-8-20261020 "What batch size does DPR use?"

# 显式允许arXiv补证据；仍使用现有生成API，并产生相应调用。
.venv/bin/python main.py --mode agent --allow-network "According to the Mamba paper, what inference throughput advantage over Transformers is stated in its abstract?"
```

不传问题则交互输入。Windows 使用 `.venv\Scripts\python.exe` 替换解释器；配置说明见 [PyCharm API 指南](docs/PYCHARM_API_GUIDE.md)和 [Mac 接续指南](docs/MAC_HANDOFF.md)。上述问答会调用 API。

| 模式 | 行为 | 知识库与调用预算 |
| --- | --- | --- |
| `rag` | 固定检索、最多两轮规则补查、生成、必要时修复引用 | 不指定版本读取三篇激活指针；常规完整问题通常2调用 |
| `agent` | 共用初检，再规划需求、检查证据、按需执行工具、生成并复核 | 当前仅八篇库；含分解最多11调用、3个工具行动 |
| `auto` | 先完成原 RAG；明确缺口、无法回答/比较或引用失败才升级原 Agent | 当前仅八篇库；直答通常2调用，升级最坏13调用 |

Auto/Agent记录写入`logs/auto_runs/`、`logs/agent_runs/`，或用`--output-dir`指定新的空目录。Python入口`main(query, mode="auto")`省略mode时仍为RAG。三模式都有状态、非空答案/说明、原文、行动、停止原因及模型调用成本。运行时故障返回`failed`结果；`degraded`表示补查未完成但有有限交付，两者CLI退出码均为1。外部获取失败后可依据本地证据回答，全部缺失则直接说明尚未核实；Auto保留的初检草稿仅通过引用结构检查。隐性漏答未必触发升级。[返回约定与回答优先级](docs/BACKEND_RESULT.md)

`--allow-network`仅开放arXiv补证据，默认关闭；Python对应`allow_network=True`，只支持Agent/Auto。它在本地正常缺源停止后，最多做3次联网决策、1次搜索和1次PDF读取；全部模型请求上限Agent为14、Auto为16。搜索最多3篇，选读1篇，追加最多6段，合并原文仍限32段/24000字符；未找到原论文则保留缺口，不使用摘要或后续论文替代原文。外部材料只用于本轮，不自动入库；失败不自动重试。[实现与取舍](evaluation/results/p3_integration_20261022/design.md)。

## 当前结果怎么理解

此前六题冻结Agent-off/on对照的任务完整且事实/引用通过4/6→5/6，开启路径token为关闭的2.532倍；Auto只预注册两道缺源题，1/2。随后书目修复298项离线通过，上一轮n04/Auto及n06/Agent却均遇搜索429，完整任务0/2。本轮修复后的n06遇超时，故障交付通过，原事实问题仍未核实。旧成绩不改，没有新的独立质量总分。[此前原文核对](evaluation/results/p3_validation_20261022/manual_review.md) · [本轮工程验证](evaluation/results/backend_reliability_20261023/report.md)。

| 实验版本 | 固定 RAG | Agent | Auto |
| --- | --- | --- | --- |
| P2.5 首轮12题，严格通过 | 10/12 | 7/12 | 当时未加入 |
| 第一版 Auto 的8题，严格事实/引用通过 | 8/8 | 6/8 | 6/8 |
| 同8题，必答完整且可交付 | 8/8 | 7/8 | 6/8 |

以上是历史冻结结果，失败保留在计划分母中；8题成绩属于旧 Auto。最新 RAG 优先 Auto 仅完成已知开发回归：a03/a04 恢复直答，旧h10 升级搜索后降级已保留；本轮反馈机制修复只作离线回归，尚无最终版本独立新题总成绩。不能把不同版本的成功案例拼成准确率。[详细对照与成本](docs/PROJECT_METRICS.md) · [最新改进与失败](evaluation/results/agent_auto_improvement_20261022/report.md)

## 知识库与检索配置

激活指针仍为三篇 `semantic-mac-20261019`（378段、384维）；八篇库 `all-papers-8-20261020` 为1397段，Auto/Agent显式使用它而不修改指针。另保留原三篇快照与五篇先导库。索引、分块和 manifest 必须成套保存，构建、切换与回退见[版本操作](docs/KNOWLEDGE_BASE_VERSIONS.md)。默认构建不会递归重建子目录中的全部八篇论文。

当前每路和 RRF 候选120、最终 Top-10、子题局部 Top-3；最多两轮按来源信号补查，rewrite/HyDE关闭。42道历史可答题的 Top-10：Precision=.1310、整体 nP=.6790、宏 Recall=.7679、MAP=.4837、MRR=.5708；检索指标不等于回答质量。Top-20 的 Recall 只多4.37个百分点，未达到当时5点预算门槛，默认保持10。见[指标口径](docs/NORMALIZED_PRECISION_2026-10-20.md)和[预算依据](docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md)。

## 验证与阅读入口

```bash
# 现有离线行为回归；模型缓存已具备，测试使用替身而非真实生成。
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m unittest discover -s tests -v

# 只从保存的结果生成新归一化报表，不调用API；输出目录须为新目录。
.venv/bin/python -m evaluation.summarize_normalized_precision --output-dir evaluation/results/new_normalized_precision
```

`evaluation.run_evaluation`、`evaluation.run_answer_evaluation` 的默认运行可能调用 API；检索评估的补查须显式传 `--complete-evidence --completion-rounds 2`。预算对照、缓存回放和历史命令见[清理前完整交接](docs/history/PROGRESS_THROUGH_2026-10-22.md)，已有实验无需为恢复上下文重跑。

| 目录/入口 | 用途 |
| --- | --- |
| `main.py` / `agent.py` | 新问题统一入口 / 保存记录诊断与有预算循环 |
| `src/` | 检索、证据、工具、回答、引用和知识库版本 |
| `data/` | 原始论文、配对索引、版本清单和激活指针 |
| `evaluation/` / `tests/` | 题集与评估入口 / 离线行为回归 |
| `docs/` | 当前说明与历史索引，见[文档导航](docs/README.md) |

[代码阅读顺序](docs/CODE_READING_GUIDE.md) · [Agent 工具与保存记录操作](docs/AGENT_REPLAY_GUIDE.md) · [历史归档与恢复](docs/history/README.md)
