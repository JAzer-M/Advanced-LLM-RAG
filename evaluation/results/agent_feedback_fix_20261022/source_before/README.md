# Advanced-LLM-RAG

面向科研论文的问答项目：PDF 解析、Semantic 分块、Dense/BM25 混合检索、RRF 融合、问题分解、BGE 重排和带引用回答；本地 Agent 可按证据缺口搜索与读取邻段。

**当前：`main` 已接通 `rag`、`agent`、`auto` 三种模式，P2.5 已做对照；Agent/Auto 的整体质量收益仍未证明，P3 联网和 P4 展示尚未开始。** 最新 Auto 先走固定 RAG，仅在明确缺口或引用失败时升级。命令行默认 `auto`，Python 函数默认 `rag`。本次重新通过251项离线测试、网络尝试0，清理验证见[清理记录](docs/CLEANUP_LOG_2026-10-22.md)。

[当前进度与下一步](PROGRESS.md) · [文档导航](docs/README.md) · [量化结果](docs/PROJECT_METRICS.md) · [实验目录](evaluation/results/README.md) · [预期全流程](docs/PROJECT_WORKFLOW.md)

## 运行

本机环境为 `.venv` / Python 3.11.9，Embedding 和 BGE 使用 CPU；生成及问题分解走本机反代。新环境安装 `requirements.txt`，现有环境与配置无需重建。首次配置参照 `api.example.json` 填写本地 `api.local.json`，已有配置不要覆盖。启动本机反代后，在项目根目录执行：

```bash
.venv/bin/python main.py --mode auto "What batch size does DPR use?"
.venv/bin/python main.py --mode agent "What batch size does DPR use?"
.venv/bin/python main.py --mode rag --kb-version all-papers-8-20261020 "What batch size does DPR use?"
```

不传问题则交互输入。Windows 使用 `.venv\Scripts\python.exe` 替换解释器；配置说明见 [PyCharm API 指南](docs/PYCHARM_API_GUIDE.md)和 [Mac 接续指南](docs/MAC_HANDOFF.md)。上述问答会调用 API。

| 模式 | 行为 | 知识库与调用预算 |
| --- | --- | --- |
| `rag` | 固定检索、最多两轮规则补查、生成、必要时修复引用 | 不指定版本读取三篇激活指针；常规完整问题通常2调用 |
| `agent` | 共用初检，再规划需求、检查证据、按需执行工具、生成并复核 | 当前仅八篇库；含分解最多11调用、3个工具行动 |
| `auto` | 先完成原 RAG；明确缺口、无法回答/比较或引用失败才升级原 Agent | 当前仅八篇库；直答通常2调用，升级最坏13调用 |

Auto/Agent 记录写入 `logs/auto_runs/`、`logs/agent_runs/`，或以 `--output-dir` 指定新的空目录。Python 入口为 `main(query, mode="auto")`，省略 `mode` 则固定 RAG。`degraded` 表示升级未完成，只保留引用结构合格的初检草稿，命令行退出码为1；该草稿仍可能存在事实错误。隐性漏答未必触发升级。

## 当前结果怎么理解

| 实验版本 | 固定 RAG | Agent | Auto |
| --- | --- | --- | --- |
| P2.5 首轮12题，严格通过 | 10/12 | 7/12 | 当时未加入 |
| 第一版 Auto 的8题，严格事实/引用通过 | 8/8 | 6/8 | 6/8 |
| 同8题，必答完整且可交付 | 8/8 | 7/8 | 6/8 |

以上是历史冻结结果，失败保留在计划分母中；8题成绩属于旧 Auto。最新 RAG 优先 Auto 仅完成已知开发回归：a03/a04 恢复直答，h10 升级搜索后仍降级，尚无最终版本独立新题总成绩。不能把不同版本的成功案例拼成准确率。[详细对照与成本](docs/PROJECT_METRICS.md) · [最新改进与失败](evaluation/results/agent_auto_improvement_20261022/report.md)

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
