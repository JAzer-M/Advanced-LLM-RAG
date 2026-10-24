# Advanced-LLM-RAG

面向科研论文的 RAG 问答项目：PDF 解析 → Semantic 分块 → Dense/BM25 检索 → RRF 融合 → 问题分解补检索 → Cross-Encoder 重排 → 证据整理 → API 回答与引用检查。

当前生成模型为 `cn:deepseek-v4.1-flash`。Embedding 与重排在本机 CPU 运行；问题分解、回答和必要时的一次引用修复共用本机反代 API。

问题分解支持 2～4 个有效子题，比较题按实体及维度拆分，并保留向量/相似度等检索术语。主流程与评估共用选证据函数，默认每路与 RRF 候选 120、最终 10；main 默认按需最多补查两次，重写与 HyDE 关闭。生成上下文补充已有真实论文标题，便于识别数字文件名对应的论文。

**main双模式入口已接通。** 默认固定RAG；运行时加`--mode agent`，共用一次初检后进入现有Agent循环和回答复核，按证据选择搜索／邻段／回答／停止。入口由用户或程序明确选择，当前没有自动模式路由；同一API模型承担不同阶段。Agent使用已验收八篇库，默认RAG仍读取原激活指针。全部230项离线测试通过，真实CLI两题合计8请求／13631 token，可答题原文引用及缺原论文拒答已核对；不是新题质量提升证明。详见[接入流程、预算与使用](evaluation/results/main_agent_integration_20261022/report.md)，完整性优先级保存在[PROGRESS](PROGRESS.md)。

**此前2026-10-22：三种规划阻塞已修复。** 单一主体回指、紧邻联合主体的确定性投影及循环内一次规划校验修正已接好；与状态／行动修正共用原一次额度，六次决策与四次回答上限保持。新增15项回归，全部217项离线测试通过。b02/b03/b06均恢复交付并review_passed，实际15次新chat／39103 token；按原冻结细粒度评分仍为1/3严格、核心7/9，剩余定义／架构背景遗漏保留。这是三道旧失败题的开发回归，未重算12题分数、未接生产main、未改知识库；详见[修复流程与原文证据](evaluation/results/agent_plan_fix_20261022/report.md)。

**此前P2.5首轮成对量化已完成，修复前Agent未证明质量收益。** 12道新题（4单篇／6跨篇／2不可答）在首次调用前冻结评分，同八篇库／模型／参数，共享真实初检。固定RAG严格通过10/12（83.33%），Agent 7/12（58.33%）；可答核心覆盖macro94.17%／64.17%，正确拒答均2/2。Agent有3题规划校验失败；生产代码与索引未改。全轮实际61次chat、121397 token，全部stop、零HTTP失败／自动重试；归因token为RAG34470、Agent95440，共享初检不能重复计入实际用量。评分歧义与敏感性、逐题原文、失败和成本见[完整报告](evaluation/results/agent_p25_20261021/report.md)，最终项目量化入口见[PROJECT_METRICS](docs/PROJECT_METRICS.md)。该实验10月22日的交接续接仅做离线核验，无新模型请求；随后规划修复的15次调用另行记账。

**此前P2.4：最终回答与有限复核已接好，已知题小规模验收通过。** `agent.py --answer-from`复用已完成记录；`--max-actions 3 --finalize`可在循环后接回答。初稿→逐项复核→必要时修订一次→再复核，回答阶段最多4次新请求；全部missing时本地说明缺口、0请求。全部202项离线测试通过。已知h10本轮4次新模型调用后复核通过，h11零调用拒答；源码、原文核对、首次复核失败和22777 token记账见[回答报告](evaluation/results/agent_answer_20261021/report.md)。该轮从保存的P1检索输入启动；目前P2.5首轮成对评测已完成，生产统一main入口与更大规模泛化仍待实施。预期路线见[项目全流程](docs/PROJECT_WORKFLOW.md)，实际进度见[PROGRESS](PROGRESS.md)。

**此前P2.3：有预算工具循环已实现。** 已知h10回归最终3个工具行动、两项需求均supported，停在answer_ready；第三步由明确记录的本地章节规则改选。该轮复用了相同提示的真实响应前缀，不能说成全新盲跑；详见[循环报告](evaluation/results/agent_loop_20261020/report.md)。此前[单次反馈失败记录](evaluation/results/agent_feedback_20261020/report.md)原样保留。

**P2.1已完成约定小规模验收**：收尾时完整新跑h01/h10/h11的“规划→证据检查→行动建议”，程序及人工均3/3；建议依次为answer/search/stop。该次实际6次API、9,907 token、全stop，零重试/工具执行；当时生产代码未改、没有重复跑测试。完整[收尾MD](evaluation/results/agent_p21_closeout_20261020/report.md)、[人工核对](evaluation/results/agent_p21_closeout_20261020/manual_review.md)已保存；完整Agent和独立泛化不作已验收声明。此前[修正及失败记录](evaluation/results/agent_scope_fix_20261020/report.md)保留。

**P1新12题留出基线已完成**：先冻结PDF Gold和评分点，运行4单篇、6跨篇、2边界题。10可答题P@10 / nP@10 / Recall / MAP / MRR为 **.1800 / .7200 / .7900 / .5337 / .7833**；严格核心点完整覆盖macro70.0%，可答严格通过4/10。两道边界题拒答内容正确，h12附带数值缺引用使总体严格通过5/12。实际24次chat、34,556 token、全部stop，无重试；生产代码/索引未改，不调参。完整[Markdown日志](evaluation/results/holdout_v1_20261020/report.md)和[逐题审阅](evaluation/results/holdout_v1_20261020/manual_review.md)已保存。该P1记录保留为固定RAG基线；其中三题现用于P2开发诊断。

**五题快速收尾已完成**：使用候选 120 / Top-10 / 最多两轮，真实运行 q2、p3、n07、a12、n11；四题复用已有 API 分解，最终回答全部真实生成。两道单篇核心完整；n07 仍缺证据；a12 分别事实正确却过度拒绝比较；n11 正确拒绝编造 P95 延迟。新增 chat 6 次、11,665 token，失败 / 自动重试 / 引用修复均为 0。按用户要求保留瑕疵，不继续调参；基线快照及原文核对见 [快速收尾报告](docs/RAG_QUICK_CLOSEOUT_2026-10-20.md)。新增五篇已导入，基础P0按用户确认视为完成；通用导入增强延期。

**2026-10-20 最新修复与预算对照**：固定增强前的原问题锚点，保留初次入选的子题局部证据，补查按每个 K 独立执行。全部 8 篇、120 页、1,397 条、42 道英文可答题，在候选 120、最多两轮下，Top-10 的 Precision / Recall / MAP / MRR 为 **0.1310 / 0.7679 / 0.4837 / 0.5708**，Top-20 为 **0.0714 / 0.8115 / 0.4857 / 0.5727**；完整 Gold 28/42→30/42，上下文字符比值中位数 1.92。按预先预算门槛保留默认 10，20 可显式试用。该离线预算对照新增 API 调用为 0；较大候选池没有在所有指标上优于 60。方法、完整对照、验证边界和交接见 [修复与预算报告](docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md)与 [PROGRESS](PROGRESS.md)。

此前完整语料评估比较了四种查询设置及 0/1/2 轮补查：原流程 Recall@10=0.7361、MAP@10=0.4899；重写 + HyDE + 两轮为 0.7242、0.4797，完整 Gold 27/42→25/42，当时三个开关默认关闭。旧结果及八次真实回答留在 [全部论文评估日志](docs/ALL_PAPERS_EVALUATION_2026-10-20.md)，不作为本轮新参数的回答验收。

此前十二道英文新题验证中，十道可答题 Recall@10=0.4833、MAP@10=0.2144，其中跨篇召回仅 0.2222。两种离线排序候选没有稳定收益，已保留原排序；此前六道开发题 Gold 全覆盖不能代表泛化。闭卷/原文/无关证据对照及剩余过度拒答见 [新题与模型知识对照日志](docs/INDEPENDENT_VALIDATION_2026-10-19.md)。历史[英文优化](docs/RETRIEVAL_OPTIMIZATION_2026-10-19.md)及[分解修复](docs/DECOMPOSITION_EVALUATION_2026-10-19.md)保留。

历史一轮限定论文补检索原型使同十道新题 Recall@10 达到 0.6000、跨篇达到 0.4167，但旧六题 Recall 从 1.0000 降到 0.9167，当时未通过采用门槛，仅显式启用且只支持 Top-10。现已支持多个 K 独立补查，量化仍需显式加 `--complete-evidence`。原实现、失败案例与零 API 调用记录见 [一轮补检索日志](docs/EVIDENCE_COMPLETION_2026-10-19.md)。

此前按用户授权比较 0/1/3 轮：同十题 Recall 为 0.4833/0.6000/0.5500，三轮 MAP=0.2252、MRR=0.3161，均低于一轮；旧六题三轮仍为 0.9167。三轮采用 60→120→180 的限定论文候选深度，当时保持补查默认关闭。用户本轮最终选择覆盖旧默认：启用最多两轮、候选 120；重写与 HyDE 继续关闭。显式调用仍可传 `completion_rounds=3`，evaluation 可加 `--completion-rounds 1 3`。旧结果、成本与局限见 [三轮补查日志](docs/COMPLETION_ROUNDS_2026-10-19.md)。

**归一化指标补充**：保留原四项，新增整体 `nP@K = sum(H)/sum(min(K,G))`；原42题集的 Top-10 / 20 为 **0.6790 / 0.7407**。逐题字段为 `H/min(K,G)`，汇总时不能平均逐题 nP。当前所有题 G≤K，整体 nP 等于 Micro Recall；原 Recall 仍为 Macro Recall。新列只表达指定 Gold 在预算内的完成程度，不代表检索结果改善或回答正确率。已有日志的 3,696 条逐题记录、880 条汇总均复核一致，无新模型或 API 调用，详见 [归一化报表与进度核对](docs/NORMALIZED_PRECISION_2026-10-20.md)。

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

选择Agent时，在PyCharm运行参数中加入`--mode agent`，或在Mac项目根目录运行：

```bash
.venv/bin/python main.py --mode agent
```

可在命令末尾传入带引号的问题；不传则交互输入。Agent日志默认保存到`logs/agent_runs/`新目录，或用`--output-dir`指定一个空目录；已有记录直接阅读，不自动重跑。函数调用为`main(query, mode="agent")`。Agent模式仅支持`all-papers-8-20261020`，比较两种模式时可给RAG显式传`--kb-version all-papers-8-20261020`，不会更改知识库激活指针。

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

回答评估会调用 API；`run_evaluation.py` 默认启用分解与改写，也会调用 API，默认候选 120、最终 10，输出 Precision、整体归一化 Precision、Recall、MAP、MRR。评估与主流程共用当前选证据实现，同时保留原全局重排等对照行。量化补查需显式传 `--complete-evidence --completion-rounds 2`（CLI 轮数默认仍为 1），不随 main 开关隐式启用。`--candidate-k 20 --top-k 5` 可复现旧预算。Gold/reference_answer 仅供评估，不传给模型。

上一轮英文六题同分解候选池、同十条预算对照：Recall@10 从 0.6667 到 1.0000，MAP@10 从 0.3542 到 0.3998。Top-20 无额外召回收益，正文约为十条的 1.95 倍，因此保留默认 10。每个预算独立选证据，固定列表的前缀分数另存。五道单篇验证题及旧库五题的原问题 Top-10 指标未退步。详见 [开发集检索优化日志](docs/RETRIEVAL_OPTIMIZATION_2026-10-19.md)；[此前中文 Top-5 分数](docs/RETRIEVAL_EVALUATION_2026-10-19.md)保留为历史基线。

上述六题属于开发集。后续十二道新英文题、两种失败的排序尝试、四题三条件生成及两题标题复核见 [新题验证日志](docs/INDEPENDENT_VALIDATION_2026-10-19.md)。新题集为 `evaluation/arxiv_next_questions_en.json`，缓存为 `evaluation/results/independent_validation_20261019/auxiliary.json`；其中改写关闭以匹配主流程。两道无 Gold 题不计检索分数，生成仅抽测 n11。正确证据组是标注原文的正向控制，不是端到端检索答案。

只评估原问题、不调用辅助 API：加 `--no-auxiliary`，但这也会禁用分解，不能当作同分解对照。固定输入比较预算：用 `--auxiliary-cache 已保存的auxiliary.json`，同题查询不会重复生成。当前八篇缓存为 `evaluation/results/all_papers_20261020/auxiliary.json`；旧六题缓存为 `evaluation/results/retrieval_optimization_20261019/auxiliary_final.json`。受控线程的 Mac 条件见 PROGRESS。

完整八篇语料的查询增强对照使用 `--query-ablation`：追加与 `main.py` 对齐的 base、rewrite、HyDE、both 四组，支持多个 K 分别选证据与补查，并记录补查前及指定轮数后的分数。必须提供含 `rewritten_query`、`hypothetical_document` 和分解结果的匹配缓存，离线回放不调用 API。2026-10-20 实验题集为 `evaluation/all_papers_questions_en.json`，独立库为 `all-papers-8-20261020`；默认激活库仍是三篇，旧库保留。

```bash
python -m evaluation.run_evaluation --questions evaluation/all_papers_questions_en.json --kb-version all-papers-8-20261020 --candidate-k 120 --top-k 10 20 --auxiliary-cache evaluation/results/all_papers_20261020/auxiliary.json --query-ablation --complete-evidence --completion-rounds 2 --output-dir evaluation/results/new_all_papers_run
```

仅从现有四组预算对照生成归一化补充报表，不加载模型、不调用 API：

```bash
python -m evaluation.summarize_normalized_precision --output-dir evaluation/results/new_normalized_precision
```

该命令重新计算本地检索和重排；本次使用保存于结果目录中的分题驱动共享重复推理，完整产物保存后无需重复跑分。

新题集可用 `python -m evaluation.run_answer_evaluation --questions 题集.json --question-id 题目ID --kb-version 版本名 --output-dir 结果目录`；默认仍使用已有六题。`evaluation.run_arxiv_pilot` 是五篇语料的离线原问题 Top-10 检查，跳过 API 分解与生成。

DeepSeek 已完成首次六题运行、固定证据调试及清理后的全流程复核。核心事实明显好于历史本地 2B；对绝对化措辞与配置例外的处理仍有瑕疵，不能宣称全面优于 Kimi。引用检查验证编号结构，语义支撑仍需人工核对。

- [三个新题、rewrite/HyDE 与本地模型同题对照](docs/REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md)
- [本次调试日志](docs/DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md)
- [本次清理日志](docs/CLEANUP_LOG_2026-10-18.md)
- [当前交接状态](PROGRESS.md)
- [历史实验概览](docs/experiments.md)与[历史结果归档](docs/history/README.md)

本地回归使用 `python -m unittest discover -s tests -v`，当前202项（123项是P2.1历史数量；随后增加工具、执行反馈、循环与回答复核检查），覆盖 API 未完成状态、失败留档、BM25、版本发布/回退/固定、真实四子题响应、预算与评估对齐、缓存回放、RRF 证据保留、引用别名、生成标题元数据、旧上下文兼容性、查询增强真实候选隔离与缺失缓存拒绝，以及限定论文补查的名称识别、多轮深度、预算、重复计划和无新增候选停止条件。本轮新增 main 调用点锚点保护、局部 Top-3 保留及 10/20 独立补查回归；另新增归一化的整体聚合、G>K、无 Gold、重复 ID、CLI 输出与报表保护检查；这些检查不调用生成 API。

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

P2现有独立的需求/证据诊断入口，尚未形成自动工具循环；LangGraph与演示界面未实现。固定RAG的规则化证据整理继续保留，语义判断需单独核验。

- `tests/test_reliability.py`：上述两个缺陷的本地回归测试，使用标准库 unittest，无新增测试依赖。

## P2第一步诊断入口

本节保留P2.1当时的诊断入口；当前`agent.py`已支持普通函数/字典实现的诊断、工具单步/循环与最终回答复核，P2.5成对验收结果见本文顶部。此前46个Python文件已补中文注释，新增的搜索工具与测试也保留中文说明，阅读顺序与文件职责见[代码阅读说明](docs/CODE_READING_GUIDE.md)。

P2.1收尾时已完整运行下述三题规划/证据检查，目录内保存当时的真实输出；只记录建议，不执行工具。以下为当时的历史运行命令，查看已有日志即可恢复上下文：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python agent.py \
  --replay-dir evaluation/results/holdout_v1_20261020 \
  --question-id h01 h10 h11 \
  --output-dir evaluation/results/agent_p21_closeout_20261020/run
```

上面是已完成目录；当时相同源码/输入/公开选项续接新增调用0。**此前加注释改变了原文件哈希，当前源码不能向该旧目录续接**，历史源码快照/协议/结果保留。新目录会发生新API请求，每批硬上限6次、失败不自动重试。规划模型只收原问题并抽取片段；事实检查只收绑定需求/查询、原文和目录，Gold/旧答案/完整比较题不传入。P2.1人工核对3/3见[报告](evaluation/results/agent_p21_closeout_20261020/report.md)；该P2.1历史运行未执行工具；当前工具循环见后文P2.3。

## P2.2 本地搜索与邻段读取工具

`load_search_resources()`加载一次八篇配对库和CPU模型；`search_local_kb(query, resources, source=None)`执行Dense/BM25 → RRF → BGE，候选120、返回最多10条。`source`须为库内精确文件名，传None则搜索全库；它只检索，不调用分解或生成API。

```python
from src.agent_tools import load_search_resources, search_local_kb

resources = load_search_resources()  # 同一进程复用；沿用PROGRESS中的离线/受控线程条件。
result = search_local_kb("What evaluation criterion does RAG use?", resources,
                         source="2005.11401v4.pdf")
```

本轮已执行的原文结果见[search_result.json](evaluation/results/agent_local_search_20261020/search_result.json)，无需重跑恢复上下文。来源为验收时人工指定，尚未验证Agent自动路由或补查后的语义判断。

`read_neighbors(chunk_id, resources, source, window=1)`用于读命中片段附近的上下文：先限定同篇论文，再按入库顺序返回中心段及前后各一段；`window`可设0～2，最多返回5段，论文首尾自动截断。`source`必须与中心段的精确文件名一致。它不加载模型、不检索、不重排、不生成答案。

```python
from src.agent_tools import read_neighbors

hit = result['results'][0]  # 使用上面的搜索结果和同一份 resources，避免混用知识库版本。
nearby = read_neighbors(hit['chunk_id'], resources, source=hit['source'])
for item in nearby['results']:
    print(item['offset'], item['chunk_id'], item['page'], item['text'])
```

`offset=-1/0/1`分别表示前段、中心段、后段。分块检索可能命中主题相关段，但定义、条件或实验判据在紧邻处，读取邻段用于补齐这些上下文。这里的“邻段”指已保存分块的顺序，无法恢复解析或分块时遗漏的原文。只读取时，资源字典提供经`load_knowledge_base()`校验的`chunks`和`knowledge_base`即可，不需要调用`load_search_resources()`加载模型。真实人工样例和完整返回见[邻段报告](evaluation/results/agent_neighbors_20261020/report.md)。

## P2.3 单次执行与有预算循环

默认运行`agent.py`仍只做规划和诊断；显式增加`--execute-once`后，每题最多执行一个工具，再做一次证据检查。搜索沿用模型给出的query/source，邻段固定前后各一段；answer/stop不调用工具或最终生成器。反馈提出的新行动只记录，不继续执行。

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python agent.py \
  --replay-dir evaluation/results/holdout_v1_20261020 \
  --question-id h10 --execute-once \
  --output-dir evaluation/results/agent_once_new_run
```

这条命令会产生新的API请求，需要本机反代运行；查看已有结果无需执行。单次模式最多两题、全批次最多6次请求。证据核对版本、manifest及原文，按版本/ID去重，保留旧证据在前；最多32段、24000字符，超限时报错，不静默删段。工具失败或请求失败均不自动重试；中断后可复用已完成的同输入调用和工具结果，未完成的尝试不会自动再执行。

代码重点为`execute_action()`、`merge_evidence()`和`run_diagnostics()`中的`execute_once`分支。逐步说明见[代码阅读指南](docs/CODE_READING_GUIDE.md)，这轮真实结果及所有失败见[验收报告](evaluation/results/agent_feedback_20261020/report.md)。真实搜索基于P2.1已验收行动的回放，最新反馈被校验拒绝；不把它描述为全新自主链路通过或h10答题成功。

以上是此前单步模式的实现及验收。新循环模式用以下命令，仍沿用受控CPU线程；命令会产生新API请求，阅读已保存记录无需重跑：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python agent.py \
  --replay-dir evaluation/results/holdout_v1_20261020 \
  --question-id h10 --max-actions 3 \
  --output-dir evaluation/results/agent_loop_new_run
```

循环一次只接受一题，最多3个工具行动、6次模型请求、32段/24000字符；前后各读两段。answer表示可以进入回答，stop表示边界停止；不加`--finalize`时只保存循环结果。反馈没有新增片段时停止；相同type/query/source/chunk_id的行动不会因reason变化而重复执行。

工具查询保留原题已有、且不含方法名的公共场景前缀，分别记录模型query和实际effective_query。重复行动或读取范围重叠超过一半时，若有同篇、匹配公共任务章节的未读区域，本地规则可选该区域，并记录action_overrides/action_origin。没有合适候选时保留原提议；若行动本身重复，最多再给模型一次改选机会，仍重复就停止。改选与非法状态修正共用一次预算，修正响应仍经过原校验，网络失败不自动重试。

最新轨迹在[novelty_followup/run/h10.json](evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json)：搜索新增9段，读结果表附近新增4段，避免重叠后改读任务说明新增3段，最终26段、10198字符；两项需求语义核对通过。单次成功轨迹是6个模型回合，开发不同方案累计9次实际新请求，缓存复用没有重复计为新请求。完整失败、成本及局限见[本轮报告](evaluation/results/agent_loop_20261020/report.md)。

## P2.4 最终回答与复核

只查看已保存的[最终答案](evaluation/results/agent_answer_20261021/network_followup/h10/answer.md)和[出处核对](evaluation/results/agent_answer_20261021/manual_review.md)不产生请求。要亲自新跑回答阶段，可在项目根目录执行以下命令；它会调用已配置的反代，最多4次，不重跑规划、搜索或邻段读取：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python agent.py \
  --answer-from evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json \
  --output-dir evaluation/results/agent_answer_new_run
```

要运行“工具循环→回答复核”，在前一节循环命令上增加`--finalize`，并使用新输出目录。程序分别写入`loop/`与`answer/`；决策最多6请求、回答最多4请求，总计最多10请求，不额外启动检索修复循环。`--finalize`只与`--max-actions`配合，原诊断与单步模式保持。

回答阶段重新核对保存输入、知识库版本和原文，不把Gold、旧答案或执行理由作为证据。`answer.md`是可交付文本；`inputs.json`中的`passages`给出[n]对应的source/page/chunk_id及完整原文；逐题JSON另保留初稿、修订稿、复核与引用检查，`actual_chat_calls.json`记录原始请求和响应。引用编号是当前26段证据的顺序号，与chunk_id不同。

全缺失时返回`insufficient_evidence`；有证据时必须通过引用结构检查和模型逐项复核，才能返回`review_passed`。两次复核仍失败则`review_failed`，保留被拒草稿，交付明确的未通过说明；网络失败或截断直接留档，不自动重试。模型复核与本地引文存在性检查仍不是正确性的保证，具体实现与边界见[代码阅读指南](docs/CODE_READING_GUIDE.md)。
