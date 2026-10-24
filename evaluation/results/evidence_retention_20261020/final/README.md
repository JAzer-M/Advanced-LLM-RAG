# Advanced-LLM-RAG

面向科研论文的 RAG 问答项目：PDF 解析 → Semantic 分块 → Dense/BM25 检索 → RRF 融合 → 问题分解补检索 → Cross-Encoder 重排 → 证据整理 → API 回答与引用检查。

当前生成模型为 `cn:deepseek-v4.1-flash`。Embedding 与重排在本机 CPU 运行；问题分解、回答和必要时的一次引用修复共用本机反代 API。

问题分解支持 2～4 个有效子题，比较题按实体及维度拆分，并保留向量/相似度等检索术语。主流程与评估共用选证据函数，默认每路与 RRF 候选 120、最终 10；main 默认按需最多补查两次，重写与 HyDE 关闭。生成上下文补充已有真实论文标题，便于识别数字文件名对应的论文。

**2026-10-20 最新修复与预算对照**：固定增强前的原问题锚点，保留初次入选的子题局部证据，补查按每个 K 独立执行。全部 8 篇、120 页、1,397 条、42 道英文可答题，在候选 120、最多两轮下，Top-10 的 Precision / Recall / MAP / MRR 为 **0.1310 / 0.7679 / 0.4837 / 0.5708**，Top-20 为 **0.0714 / 0.8115 / 0.4857 / 0.5727**；完整 Gold 28/42→30/42，上下文字符比值中位数 1.92。按预先预算门槛保留默认 10，20 可显式试用。本轮新增 API 调用为 0；较大候选池没有在所有指标上优于 60。方法、完整对照、验证边界和交接见 [修复与预算报告](docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md)与 [PROGRESS](PROGRESS.md)。

此前完整语料评估比较了四种查询设置及 0/1/2 轮补查：原流程 Recall@10=0.7361、MAP@10=0.4899；重写 + HyDE + 两轮为 0.7242、0.4797，完整 Gold 27/42→25/42，当时三个开关默认关闭。旧结果及八次真实回答留在 [全部论文评估日志](docs/ALL_PAPERS_EVALUATION_2026-10-20.md)，不作为本轮新参数的回答验收。

此前十二道英文新题验证中，十道可答题 Recall@10=0.4833、MAP@10=0.2144，其中跨篇召回仅 0.2222。两种离线排序候选没有稳定收益，已保留原排序；此前六道开发题 Gold 全覆盖不能代表泛化。闭卷/原文/无关证据对照及剩余过度拒答见 [新题与模型知识对照日志](docs/INDEPENDENT_VALIDATION_2026-10-19.md)。历史[英文优化](docs/RETRIEVAL_OPTIMIZATION_2026-10-19.md)及[分解修复](docs/DECOMPOSITION_EVALUATION_2026-10-19.md)保留。

历史一轮限定论文补检索原型使同十道新题 Recall@10 达到 0.6000、跨篇达到 0.4167，但旧六题 Recall 从 1.0000 降到 0.9167，当时未通过采用门槛，仅显式启用且只支持 Top-10。现已支持多个 K 独立补查，量化仍需显式加 `--complete-evidence`。原实现、失败案例与零 API 调用记录见 [一轮补检索日志](docs/EVIDENCE_COMPLETION_2026-10-19.md)。

此前按用户授权比较 0/1/3 轮：同十题 Recall 为 0.4833/0.6000/0.5500，三轮 MAP=0.2252、MRR=0.3161，均低于一轮；旧六题三轮仍为 0.9167。三轮采用 60→120→180 的限定论文候选深度，当时保持补查默认关闭。用户本轮最终选择覆盖旧默认：启用最多两轮、候选 120；重写与 HyDE 继续关闭。显式调用仍可传 `completion_rounds=3`，evaluation 可加 `--completion-rounds 1 3`。旧结果、成本与局限见 [三轮补查日志](docs/COMPLETION_ROUNDS_2026-10-19.md)。

## 运行

从 Windows 转到 Mac 时，先看 [Mac 接续开发说明](docs/MAC_HANDOFF.md)。当前私有仓库同步了三篇论文和三组配对索引，并提供数据哈希清单；本地 API Key、虚拟环境和模型缓存不随 Git 同步。

使用现有 Python 3.11 环境。新环境安装 `requirements.txt`；该清单尚未锁定全部版本。

1. 启动本机反代 `http://127.0.0.1:7863/v1`。
2. 首次配置时复制 `api.example.json` 为 `api.local.json`，填写 Key；已有配置不要覆盖。
3. 在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe main.py
```

交互输入问题即可。详细设置见 [PyCharm API 指南](docs/PYCHARM_API_GUIDE.md)。Key 不写入代码、日志或 Git。

三篇原始论文位于 `data/raw/`；现有 Semantic 索引与 JSON 位于 `data/processed/`，共 378 条、384 维。缓存已下载时，可设置 `HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1`。

另已完成 RAG/DPR/ColBERT/Self-RAG/CRAG 五篇 arXiv 论文先导实验，88 页、1,019 条，独立版本 `arxiv-pilot-5-20261019`，默认三篇库未切换。下载清单、Mac 复现命令、检索/问答结果及跨篇问题见 [五篇实验报告](docs/ARXIV_PILOT_2026-10-19.md)。

当前通过 `data/processed/active_kb.json` 选择成对的 Semantic 知识库版本；旧项目没有指针时继续读取原始 Semantic 文件。重建使用 `python build_semantic_index.py --version 新的版本名`，生成独立版本、校验后发布，默认不切换当前库。切换与回退使用 `python -m src.knowledge_base activate 版本名`。实际示例与 Mac 构建条件见 [知识库版本操作](docs/KNOWLEDGE_BASE_VERSIONS.md)。`build_recursive_index.py` 保留为独立对照入口。

## 评估与结果

```powershell
# 六题真实主流程，保存每次 API 调用、答案、证据和引用编号
python -m evaluation.run_answer_evaluation --output-dir evaluation/results/new_run

# 固定证据，只检查生成；输入和输出目录须不同
python -m evaluation.run_answer_evaluation --question-id q1 q5 --replay-dir evaluation/results/deepseek_v41/initial --output-dir evaluation/results/new_replay

# 检索方法对照，以及 Gold 引文与当前分块的匹配检查
python -m evaluation.run_evaluation
python -m evaluation.check_evidence

# 用五篇 arXiv 论文题集运行同一套量化检索对照
python -m evaluation.run_evaluation --questions evaluation/arxiv_pilot_questions_en.json --kb-version arxiv-pilot-5-20261019 --top-k 5 10 20 --output-dir evaluation/results/new_english_run
```

回答评估会调用 API；`run_evaluation.py` 默认启用分解与改写，也会调用 API，默认候选 120、最终 10，输出 Precision、Recall、MAP、MRR。评估与主流程共用当前选证据实现，同时保留原全局重排等对照行。量化补查需显式传 `--complete-evidence --completion-rounds 2`（CLI 轮数默认仍为 1），不随 main 开关隐式启用。`--candidate-k 20 --top-k 5` 可复现旧预算。Gold/reference_answer 仅供评估，不传给模型。

上一轮英文六题同分解候选池、同十条预算对照：Recall@10 从 0.6667 到 1.0000，MAP@10 从 0.3542 到 0.3998。Top-20 无额外召回收益，正文约为十条的 1.95 倍，因此保留默认 10。每个预算独立选证据，固定列表的前缀分数另存。五道单篇验证题及旧库五题的原问题 Top-10 指标未退步。详见 [开发集检索优化日志](docs/RETRIEVAL_OPTIMIZATION_2026-10-19.md)；[此前中文 Top-5 分数](docs/RETRIEVAL_EVALUATION_2026-10-19.md)保留为历史基线。

上述六题属于开发集。后续十二道新英文题、两种失败的排序尝试、四题三条件生成及两题标题复核见 [新题验证日志](docs/INDEPENDENT_VALIDATION_2026-10-19.md)。新题集为 `evaluation/arxiv_next_questions_en.json`，缓存为 `evaluation/results/independent_validation_20261019/auxiliary.json`；其中改写关闭以匹配主流程。两道无 Gold 题不计检索分数，生成仅抽测 n11。正确证据组是标注原文的正向控制，不是端到端检索答案。

只评估原问题、不调用辅助 API：加 `--no-auxiliary`，但这也会禁用分解，不能当作同分解对照。固定输入比较预算：用 `--auxiliary-cache 已保存的auxiliary.json`，同题查询不会重复生成。当前八篇缓存为 `evaluation/results/all_papers_20261020/auxiliary.json`；旧六题缓存为 `evaluation/results/retrieval_optimization_20261019/auxiliary_final.json`。受控线程的 Mac 条件见 PROGRESS。

完整八篇语料的查询增强对照使用 `--query-ablation`：追加与 `main.py` 对齐的 base、rewrite、HyDE、both 四组，支持多个 K 分别选证据与补查，并记录补查前及指定轮数后的分数。必须提供含 `rewritten_query`、`hypothetical_document` 和分解结果的匹配缓存，离线回放不调用 API。2026-10-20 实验题集为 `evaluation/all_papers_questions_en.json`，独立库为 `all-papers-8-20261020`；默认激活库仍是三篇，旧库保留。

```bash
python -m evaluation.run_evaluation --questions evaluation/all_papers_questions_en.json --kb-version all-papers-8-20261020 --candidate-k 120 --top-k 10 20 --auxiliary-cache evaluation/results/all_papers_20261020/auxiliary.json --query-ablation --complete-evidence --completion-rounds 2 --output-dir evaluation/results/new_all_papers_run
```

该命令重新计算本地检索和重排；本次使用保存于结果目录中的分题驱动共享重复推理，完整产物保存后无需重复跑分。

新题集可用 `python -m evaluation.run_answer_evaluation --questions 题集.json --question-id 题目ID --kb-version 版本名 --output-dir 结果目录`；默认仍使用已有六题。`evaluation.run_arxiv_pilot` 是五篇语料的离线原问题 Top-10 检查，跳过 API 分解与生成。

DeepSeek 已完成首次六题运行、固定证据调试及清理后的全流程复核。核心事实明显好于历史本地 2B；对绝对化措辞与配置例外的处理仍有瑕疵，不能宣称全面优于 Kimi。引用检查验证编号结构，语义支撑仍需人工核对。

- [三个新题、rewrite/HyDE 与本地模型同题对照](docs/REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md)
- [本次调试日志](docs/DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md)
- [本次清理日志](docs/CLEANUP_LOG_2026-10-18.md)
- [当前交接状态](PROGRESS.md)
- [历史实验概览](docs/experiments.md)与[历史结果归档](docs/history/README.md)

本地回归使用 `python -m unittest discover -s tests -v`，当前 68 项，覆盖 API 未完成状态、失败留档、BM25、版本发布/回退/固定、真实四子题响应、预算与评估对齐、缓存回放、RRF 证据保留、引用别名、生成标题元数据、旧上下文兼容性、查询增强真实候选隔离与缺失缓存拒绝，以及限定论文补查的名称识别、多轮深度、预算、重复计划和无新增候选停止条件。本轮新增 main 调用点锚点保护、局部 Top-3 保留及 10/20 独立补查回归；这些检查不调用生成 API。

## 代码结构

- `main.py`：当前问答主流程；候选 120、最终 10、按需最多补查两次；HyDE 和查询改写默认关闭。
- `src/pdf_loader.py`、`chunking_semantic.py`、`chunking_recursive.py`：解析和分块。
- `src/embedding.py`、`vector_store.py`、`chunk_storage.py`：向量与持久化。
- `src/knowledge_base.py`：成对版本、哈希校验、当前选择与切换/回退命令。
- `download_arxiv_papers.py`：按固定版本清单下载小批量论文、校验并跳过已有文件、记录失败供重跑。
- `src/*retriever.py`、`reranker.py`：检索、融合与重排。
- `src/evidence_gap.py`：来源定向补检索；main 默认最多两轮，上限可显式设 1～3 轮，返回覆盖信号、局部保留 ID、逐轮候选、补查与停止记录。
- `src/query_decomposer.py`、`query_rewriter.py`、`hyde.py`：问题分解与可选查询增强。
- `src/numeric_evidence.py`、`grounded_evidence.py`：保守数值解析、有限主体归属及原文证据视图。
- `src/api_llm.py`、`llm.py`、`citation_validation.py`：API 调用、共享入口与引用结构检查。
- `evaluation/`：检索与问答评估入口、旧六题、五篇先导题及运行结果；旧诊断脚本已清理。

Single-Agent、LangGraph 与演示界面尚未实现。当前使用规则化证据整理，不能等同于通用语义验证。

- `tests/test_reliability.py`：上述两个缺陷的本地回归测试，使用标准库 unittest，无新增测试依赖。
