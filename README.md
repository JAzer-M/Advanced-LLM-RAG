# Advanced-LLM-RAG

面向科研论文的问答项目：PDF解析、Semantic分块、Dense/BM25混合检索、RRF、BGE重排、问题分解、证据保留和带引用回答。本地Agent按证据缺口选择搜索或读取邻段，Auto先走RAG再按需升级。

**当前：本机PaperLens可使用三模式、引用原文、模型设置和PDF入库。** 中文比较需求绑定、回答语言和JSON代码块兼容已修复；此前345项后端测试通过，本轮独立虚拟环境的31项网页检查通过。Mac安装启动闭环与前端操作已验收，本地模型复用已有缓存。当前版本尚无独立新题总体质量成绩。[当前进度](PROGRESS.md) · [安装与首次启动](docs/INSTALL_AND_START.md) · [质量与成本总览](docs/PROJECT_METRICS.md)

## 本机网页

Mac可双击桌面的“PaperLens 启动.command”或[项目启动文件](webui/start.command)，也可在项目根目录运行：

```bash
.venv/bin/python -B -u webui/server.py
```

服务就绪后打开[PaperLens](http://127.0.0.1:8849)，使用期间保持启动终端打开。支持暖白/朱橙阅读布局、答案与原文联动、Enter发送/Shift+Enter换行、中英文界面和已保存案例。打开回放不生成新回答；实时提问使用配置的API。

网页当前是本机9篇/1767段库，包含新增Mamba；由`data/webui/library.json`独立选择。PDF上传后先构建并校验新版本，再切换下一次网页问答。上传数据、指针与新索引被Git忽略，不随本次本地提交迁移。[网页操作及限制](webui/README.md) · [PDF入库验收](docs/WEBUI_PDF_IMPORT_2026-10-24.md)

旧8848页面和启动文件已删除。`ui_prototype/app.py`仍被新服务复用，保留它的辅助函数；不再单独启动旧服务。[保留原因](ui_prototype/README.md)

## CLI与默认值

当前Mac环境为`.venv` / Python 3.11.9，Embedding/BGE使用CPU，分解与生成使用兼容Chat Completions的API。已有环境无需重建；首次安装按[安装说明](docs/INSTALL_AND_START.md)创建虚拟环境、安装固定版本依赖并准备本地模型。私有配置可在网页填写，额外选项参照[示例](api.example.json)。新安装从空网页库上传自己的首篇PDF即可建库；本机网关需先运行。[验收记录](docs/maintenance/installation_ui_acceptance_20261024/report.md) · [GitHub本机下载包方案](docs/LOCAL_DISTRIBUTION.md) · [Mac预览包验收](docs/maintenance/macos_package_20261024/report.md)

以下是真实问答入口，会产生API请求。在项目根目录执行：

```bash
.venv/bin/python main.py --mode auto "What batch size does DPR use?"
.venv/bin/python main.py --mode agent "What batch size does DPR use?"
.venv/bin/python main.py --mode rag --kb-version all-papers-8-20261020 "What batch size does DPR use?"

# 显式允许arXiv补证据；最多一次搜索和一次固定版本PDF读取。
.venv/bin/python main.py --mode agent --allow-network "According to the Mamba paper, what inference throughput advantage over Transformers is stated in its abstract?"
```

不传问题则交互输入。Python函数默认`mode='rag'`，CLI默认`--mode auto`。Windows解释器入口可换为`.venv\Scripts\python.exe`，但网页PDF入库的Windows锁机制尚未验收。[API配置](docs/PYCHARM_API_GUIDE.md) · [Mac环境记录](docs/MAC_HANDOFF.md)

| 路径 | 默认知识库 | 模型调用边界 |
| --- | --- | --- |
| RAG | 全局激活指针；本机为三篇`semantic-mac-20261019` | 常规完整题通常2次；含原引用检查/有限修复 |
| Agent | 未指定时八篇`all-papers-8-20261020` | 含分解最多11次，工具最多3行动 |
| Auto | 未指定时八篇`all-papers-8-20261020` | 直答通常2次，升级最坏13次 |
| 网页三模式 | 提交时固定网页指针版本；本机当前9篇 | 复用上述模式预算 |

三模式都可用`--kb-version`或`kb_version`显式选择合法配对库。同库比较需显式选同一版本。`--allow-network`默认关闭，只支持Agent/Auto，仅开放arXiv；模型上限分别增为14/16。库中已有明确主论文时不会因为开启开关就必然联网，外部补证据也不自动入库。

Agent/Auto日志写入`logs/agent_runs/`、`logs/auto_runs/`，或指定新的空`--output-dir`。三模式返回答案/说明、证据、行动、停止原因、状态和成本；failed/degraded的CLI退出码为1。429/超时不等于论文未报告，完成或自动复核通过不等于独立事实验收。[返回约定](docs/BACKEND_RESULT.md)

## 模型、知识库与检索

截至2026-10-24，本机请求模型为`cn:glm-5.3`，最近响应报告`glm-5.3`；历史冻结评测主要使用`cn:deepseek-v4.1-flash`。回答跟随提问语言，明确指定语言时优先；界面语言开关只改变界面。模型、语言和知识库变化后的结果不直接混入旧成绩。

本机保留3/5/8篇库及当前9篇网页库；索引、chunks与manifest须成套保存。[版本操作及迁移边界](docs/KNOWLEDGE_BASE_VERSIONS.md)

当前每路/RRF候选120、RRF常数60、最终Top-10、子题局部Top-3、按来源信号最多两轮补查；rewrite/HyDE关闭。Top-10/20检索对照和默认预算依据见[实验总览](docs/PROJECT_METRICS.md)。现有小样本结果没有证明当前Agent/Auto总体优于固定RAG；工程行为、已知题修复和独立质量分开记录。

## 验证与阅读入口

此前完整行为回归保存为345项后端、27项网页通过，见[历史测试汇总](evaluation/results/chinese_comparison_20261024/final_offline_test_summary.json)。本轮修复首次启动和标题提取后，独立环境31项网页检查通过；只新增一次真实RAG问答（2请求/3098 token），没有重跑后端全套或质量评测。[本轮验收](docs/maintenance/installation_ui_acceptance_20261024/report.md)。以后行为变更时可在已具备模型缓存的环境运行：

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m unittest discover -s tests -v

.venv/bin/python -B -m unittest webui.test_server webui.test_config webui.test_library webui.test_model_assets webui.test_runtime
```

测试使用模型替身；网页中的两项检查需允许临时本机HTTP端口。`evaluation.run_evaluation`与`evaluation.run_answer_evaluation`可能调用API，恢复上下文先读保存记录；无需因换对话重跑实验。检索评估的补查须显式启用`--complete-evidence --completion-rounds 2`，各K独立运行。

| 入口 | 用途 |
| --- | --- |
| [PROGRESS](PROGRESS.md) | 当前完成范围、配置与待办 |
| [PROJECT_METRICS](docs/PROJECT_METRICS.md) | RAG/Agent/Auto质量、成本、检索和失败证据 |
| [代码阅读](docs/CODE_READING_GUIDE.md) / [Agent操作](docs/AGENT_REPLAY_GUIDE.md) | 文件职责、工具与保存记录 |
| [实验索引](evaluation/results/README.md) / [历史归档](docs/history/README.md) | 原始报告、问题、Gold、失败和版本快照 |
| [预期全流程](docs/PROJECT_WORKFLOW.md) | 阶段目标；不作为实际进度表 |
