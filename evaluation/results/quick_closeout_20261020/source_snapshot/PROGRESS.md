# Advanced-LLM-RAG 项目进度与新对话交接

更新：2026-10-20（Asia/Shanghai）。当前工作区：`/Users/j/Desktop/Advanced-LLM-RAG`；Git 基点 `c2cd612`，有大量已保留的未提交 / 未跟踪工作，尚未提交或推送本轮改动。

## 1. 新对话先看这里

最新用户决定：**保留原始 Precision、Recall、MAP、MRR，增加整体归一化 Precision（nP@K），复用现有日志生成补充报表，然后核对当前进度。** 本次已实现并验证，不改变检索结果或预算。此前决定继续生效：按需最多补查两次、候选 120、默认 Top-10，Top-20 保留为显式对照。

**已完成**原查询锚点和补查局部证据保留修复；当前 main 为候选 120、最终 Top-10、按需最多两轮补查。Top-20 已独立量化并保留结果，尚未设为默认。重写与 HyDE 关闭。四项指标全部计算，本轮新增 API 调用为 0。

先读本文、[归一化指标与本次进度核对](docs/NORMALIZED_PRECISION_2026-10-20.md)和 [修复 / 预算报告](docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md)，需要旧结论的原话再查 [完整可见对话](docs/chat_history/RAG_2026-10-19_20_完整对话.md)。归档对话仍是上一轮快照，不包含此后的 Precision 讨论；不要重跑整套付费查询或重建索引来“恢复上下文”。

## 2. 用户约束与设备事实

- 默认中文说明；问题题集使用英文。先说明目的、结果和验证边界。讲解 / 下一步讨论不等于实施授权；明确委托执行时在授权范围内完成。
- 保持普通函数、字典、列表及原文件结构；最小改动，不为技术名词增加框架。插件是协作辅助，不是项目运行依赖。
- 本机全局规范位于 `~/.codex/AGENTS.md`，本轮实际收到并遵循；无需重复改插件缓存。Matt Pocock / 鼠鼠实习工具按需要使用，不自动同步到 Windows 或普通 ChatGPT。本轮实际使用 Karpathy 与 Matt 调试技能，没有新增子代理。
- 核心目标是可解释、可复现、有量化证据的科研论文 RAG / Agent 项目，面向大模型应用、RAG、Agent 开发实习，尚未绑定具体 JD。
- **本项目不做 Fine-tuning、LoRA、QLoRA**；不混入独立的 PyTorch Transformer 架构项目。
- MacBook Air + PyCharm 是主开发设备；本机项目 `.venv` Python **3.11.9** 本轮已核对。现有记录没有确认具体芯片和内存，不推断为 M3 或 16GB。
- Windows：用户历史设备 RTX 5060 Laptop GPU、约 8GB 显存，PyCharm、Python 3.11.9。历史本地 Qwen3.5-2B / CUDA 运行记录不冒充本轮 Mac 或 Windows 新实测。
- 当前生成走 API，Embedding / BGE 在 Mac CPU 离线运行；主线不要求额外 NVIDIA GPU。两台电脑不共享进程、虚拟环境、模型缓存或本机代理，`127.0.0.1` 指运行程序所在电脑。
- Git 只同步已提交且推送的内容。当前新增论文、版本、模型缓存、配置与未提交资料不能假定已同步到 GitHub / Windows；本轮没有提交 / 推送授权或操作。
- 保留原有工作、配对索引、题集与实验结果；凭证只保存在本地私有配置 / 环境变量，不进入日志。

## 3. 当前配置、知识库与真实运行范围

| 项目 | 当前值 / 验证边界 |
| --- | --- |
| Embedding | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，CPU、384 维 |
| Reranker | `BAAI/bge-reranker-base`，本机缓存，CPU 离线实测 |
| 每路 Dense / BM25 与 RRF 候选 | `RETRIEVAL_TOP_K=120`、`RRF_TOP_K=120` |
| RRF 秩平滑常数 | `RRF_K=60`，不是候选数 |
| 最终证据 | `RERANK_TOP_K=10`；Top-20 已独立对照 |
| 来源定向补查 | `USE_EVIDENCE_COMPLETION=True`，`main(..., completion_rounds=2)`；按信号触发并可提前停止 |
| 补查候选深度 | 第 1 / 2 轮为 120 / 240，先限定论文再截断；不是固定执行两次 |
| rewrite / HyDE | `USE_MULTI_QUERY=False`、`USE_HYDE=False` |
| 默认知识库 | `semantic-mac-20261019` 三篇库；八篇需显式指定 |
| evaluation | 候选默认 120；本轮显式 `--top-k 10 20 --complete-evidence --completion-rounds 2`；CLI 补查轮数默认仍为 1 |
| 当前真实生成 | API 配置存在；本轮未重新发起生成，不能据此验收新参数回答 |


API 私有配置已填写，当前请求路由 `cn:deepseek-v4.1-flash`；此前实际响应报告 `deepseek-v4.1-flash`，标识不能独立证明上游权重。设置为 `thinking.type=disabled`、`temperature=0`、`max_tokens=4096`。本轮没有发起 API 调用，因此没有重新验收反代连通性或新预算下的回答生成。

### 知识库版本

| 版本 | 语料 / 数量 | 状态 |
| --- | --- | --- |
| `legacy-3papers-20261019` | 原 Transformer / DCNN / VGG，378 条 | 不重编码的旧配对快照 |
| `semantic-mac-20261019` | 同三篇，378 条、384 维 | **当前激活指针**，Mac 重建对照通过 |
| `arxiv-pilot-5-20261019` | RAG / DPR / ColBERT / Self-RAG / CRAG，88 页、1,019 条 | 独立五篇实验库 |
| `all-papers-8-20261020` | `data` 全部八篇，120 页、1,397 条 | 精确合并三篇 / 五篇的已验证分块及向量，仅重映射位置 ID |

五篇固定版本为 RAG v4 `2005.11401v4`、DPR v3 `2004.04906v3`、ColBERT v2 `2004.12832v2`、Self-RAG v1 `2310.11511v1`、CRAG v3 `2401.15884v3`。原三篇是 Transformer 11 页、DCNN / AlexNet 7 页、VGG 14 页，不含 ResNet。

`data/processed/active_kb.json` 仍选择三篇库。使用八篇库时显式传 `kb_version="all-papers-8-20261020"`；本轮未擅自切换指针。每版 `faiss.index`、`chunks.json`、`manifest.json` 必须成对；位置 ID 不跨库通用，Gold 以 source/page/quote 映射，合并 ID 映射另存。操作见 [版本指南](docs/KNOWLEDGE_BASE_VERSIONS.md)。

### Mac 受控线程

批量线程退出 139 的根因仍未定位；本轮稳定运行继续采用：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python evaluation/results/evidence_retention_20261020/run_comparison.py
```

驱动在首次模型加载前设置 `torch.set_num_threads(1)` 和 `torch.set_num_interop_threads(1)`。上述完整实验已有结果时直接读取，**无需再次执行**。新 Python 进程中的真实 main 问答仍会调用 API。

## 4. 当前流程与本轮修复

离线：PDF 解析 → Semantic 分块 → MiniLM 归一化向量 → FAISS 配对版本。构建入口 `build_semantic_index.py --version 新版本名` 不覆盖旧版；整体构建，尚无完整增量导入生命周期。默认 `data/raw` 加载只遍历本层 PDF，五篇另在子目录；八篇版本是既有配对资产的精确合并，不能假定默认构建入口会递归重建全部八篇。

在线：API 分解判断（2～4 个有效去重子题）→ 原问题 Dense / BM25 → 保存增强前 RRF 首条锚点 → 可选 rewrite / HyDE 候选融合 → 子题各路检索并合并去重 → 原问题全局 BGE + 子题局部 Top-3 → 预算内选证据 → 按来源覆盖信号最多补查两轮 → 原文 / 标题 / 规则账本 → API 回答 → 引用结构检查、必要时一次修复。

- **锚点固定**：增强前原问题的 RRF 首条不因 rewrite / HyDE 融合而改变。不开增强时该修复不改变原锚点。
- **局部证据保留**：只把初次已入选且属于子题局部 Top-3 的片段记为 `retained_local_ids`；补查后与锚点一起保护，并复用 `select_evidence` 选择原子题和定向补查候选。去掉另一套“先给全局前五”的规则。
- **K 独立**：原 evaluation 每个最终 K 分别选证据、判断覆盖、运行补查，保存 `evidence_completion_by_k`；不能把 20 条前缀当 10 条结果。
- 补查只对能识别两个以上论文来源且有覆盖信号的题触发；单篇题或无信号时跳过。每轮最多四个来源任务，第二轮增加同一批任务的候选深度；没有动态 LLM 语义缺口判定。
- 当前不是完整 Agent：没有根据结果自主规划任意工具、联网检索、LangGraph 编排或演示 UI。导入的 Self-RAG / CRAG 论文内容不代表本项目已实现它们的方法。

### 不能丢失的数据 / 算法事实

- Chunk 字段：`chunk_id/text/source/page/title/section`。Embedding 和 BM25 主要索引正文；保留 title 不等于 title 进入向量，BGE / 生成上下文使用标题元数据。
- 构建 Semantic 实参 `max_chunk_size=500` 字符、`percentile=10`；单个超长句不硬切，但短句 / 短片段过滤和跨页断句意味着不保证无损。双栏文件显式指定，尚无通用版式保证。
- FAISS 是归一化向量的 `IndexFlatIP` 精确内积检索，不是 HNSW。论文中提到 HNSW 不等于项目使用 HNSW。
- `RRF_K=60` 是秩平滑常数，与每路候选 120、`RRF_TOP_K=120` 和最终 K 不同。
- 引用检查仅验证编号结构；元数据、来源覆盖、局部 Top-3 和保护规则都不是语义正确的证明。
- API 只接受非空正文且 `finish_reason=stop`，截断 / 其他结束状态显式失败并留档；不隐式回退本地 Qwen，也没有隐藏重试。
- BM25 空有效词项返回空，过滤零分，避免无效 RRF 贡献；纯中文仍可走 Dense，英文 / 数字分词不代表中文 BM25 已完善。

## 5. 当前检索指标与归一化结果

八篇库 42 道英文可答题，候选 120、关闭 rewrite / HyDE、按需最多补查两轮：

| 最终预算 | Precision | nP（整体） | Recall（宏平均） | MAP | MRR | 全部 Gold 入选 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-10 | 0.1310 | 0.6790 | 0.7679 | 0.4837 | 0.5708 | 28/42 |
| Top-20 | 0.0714 | 0.7407 | 0.8115 | 0.4857 | 0.5727 | 30/42 |

新字段 `normalized_precision`：逐题为 `H/min(K,G)`，汇总为 `sum(H)/sum(min(K,G))`，汇总不能直接平均逐题归一化分数。H 是前 K 条中去重后的 Gold 命中数，G 为该题去重后的 Gold 数；无 Gold 题跳过，无可计分题时返回 None。原四项字段和计算口径保留。

42 题 Gold 数按题相加为 81，所有 G≤8；原平均 P@10 / P@20 的理论上限为 .192857 / .096429。实际合计命中 55 / 60，因此整体 nP 为 55/81=.679012、60/81=.740741，在本题集等于 Micro Recall。原 Recall 是逐题平均的 Macro Recall；逐题归一化再平均在本题集会得到原 Recall，不能混作整体 nP。若以后某题 G>K，nP 分母按 K 截断，与普通 Recall 不再相同。

新列只重新表达预算内指定 Gold 的完成程度，不代表检索改善、全部上下文的有用比例或回答正确率。完整各方法、旧 / 新题与单篇 / 跨篇结果见 [补充报表](evaluation/results/normalized_precision_20261020/report.md)及同目录 JSON；历史原始结果未覆盖。

Precision 分母随 K 变化，Top-20 下降需要结合 Recall、MAP、MRR 和完整覆盖判断；不是只选 Recall 最大的一组。Gold 为非穷尽原文标注，不等于所有其他段落无用。上下文字符长度只是成本代理，不是实际 token 账单或服务 P95。

Top-20 的 Recall 增加 **4.37 个百分点**、完整 Gold 由 28/42 增至 30/42，MAP / MRR 略增；完整上下文字符比值中位数为 **1.92**。本轮开始前设定 Recall 至少增加 5 个百分点才把默认提高为 20，因此保持 10。此门槛是本轮的工程预算选择，不是通用统计结论；偏重召回时可显式使用 20。候选 120 按用户决定保留，但修复后候选 60 的 Top-10 Recall 同为 .7679、MAP / MRR 更高，不能说候选越大越好。

## 6. 验证记录与仍未验收的内容

- 本次归一化补充：全部 **79 项 unittest** 通过（原 68 项及新增 11 项）；新增检查覆盖整体 / 逐题聚合差异、G>K、无 Gold、重复 ID、CLI JSON 输出、报表拒绝覆盖和旧指标一致性。测试禁止网络连接，无模型生成或 API 调用。
- 只读取保存的四组选择 / 候选对照，复核 **3,696 条逐题记录和 880 条分组汇总**；补充 nP 列，原 Precision / Recall / MAP / MRR、Gold 与入选 ID 均保留。当前配置、四版知识库配对文件哈希、激活指针及九项迁移清单另行核对；结果见新目录的 `verification.json` / `progress_audit.json`。

- 上一轮锚点 / 保留修复：先在旧代码上建立四个失败回归测试，再修复；当时全部 **68 项 unittest** 通过，红灯 / 绿灯原始输出保留。
- 原 `run_evaluation` CLI 完成 42 题 × 修复前后 × 候选 60/120 × 独立 K=10/20；所有方法保存 Precision、Recall、AP/RR，汇总 MAP/MRR。4 道无 Gold 题跳过，未伪造为 0 分。
- 独立脚本重新由原文映射 Gold，并复算 **3,844 组方法/K/题记录的四项指标**（主对照 3,696 组，加增强和三篇入口检查）；分组均值也一致。
- `main.main` 真实检索 / 重排 / 上下文回放 **8 次**，p1 含 rewrite + HyDE 的两种 K，选中 ID 均与 evaluation 对齐；最终回答显式替身，不能称为真实回答成功。
- 当前仍激活的三篇库，通过五道题、候选 120、两种 K、最多两轮的实际 evaluation CLI；原三篇/五篇/八篇资产哈希及 9 项迁移清单一致。
- 原 60 / Top-10 共有方法逐题复现上一轮；全部被标记的局部证据在补查各轮保留，API 调用计数为 **0**，凭证未进入导出产物。
- 主对照耗时约 **20.6 分钟**，共享重排缓存，不能作为单请求延迟或服务基准。

- 新版 default / Top-20 下的真实最终回答与语义效果没有重新调用 API 验证。最新真实回答证据来自上一轮 8 次 main：p3/a10 核心完整，n07/a12 部分完成；这些属于旧参数条件，不能当作本轮新设置的回答验收。
- 原数据、题目、Gold、旧结果、配对索引及私有配置保留；日志脱敏。默认库指针仍三篇，完整八篇需显式指定。
- 来源别名仍不能把 Transformer 简称映射到 `Attention is all you need.pdf`（a09/a15），本轮未改题 / 改标注解决它。
- 复用的 p4 旧分解因五个子题被拒绝，沿用原状态，没有再花 API 重生成。n08 原题条件归属有歧义，保留原题与 Gold。
- 保护可能保留不正确的局部候选；候选 120 会改变首次局部排序。修复不承诺所有 Gold 进入 Top-K，也不代表语义充分。

## 7. 历史实验索引与结论

| 工作 | 可信结论 / 边界 | 报告 |
| --- | --- | --- |
| 保持风格清理 / 早期 API 调试 | 保持普通函数结构；六题与固定证据调试，仍有绝对化措辞问题 | [清理](docs/CLEANUP_LOG_2026-10-18.md)、[DeepSeek 调试](docs/DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md) |
| rewrite / HyDE 与本地 Qwen 对照 | 三篇库三题四条件；增强输出来自 API，本地 Qwen 仅回放最终提示；不是本地生成的增强实验 | [三篇模型 / 增强对照](docs/REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md) |
| Mac 迁移 / 版本配对 | 离线检索、BGE CPU、三题真实 API；版本切换 / 回退已实测 | [Mac 审计](docs/MAC_AUDIT_2026-10-19.md)、[版本指南](docs/KNOWLEDGE_BASE_VERSIONS.md) |
| 五篇下载 / 先导 | 固定版本、幂等下载 / 失败重跑；不等于通用导入阶段完成 | [先导](docs/ARXIV_PILOT_2026-10-19.md)、[选题](docs/ARXIV_PILOT_SELECTION_2026-10-19.md) |
| 分解 / 证据选择修复 | 2～4 子题、局部 Top-3、标题、拒答修正；部分措辞精度仍有限 | [修复与 evaluation](docs/DECOMPOSITION_EVALUATION_2026-10-19.md) |
| 英文六题 / Top-K | 开发六题指定 Gold 全覆盖，排序仍靠后；不能宣称泛化满分 | [原量化](docs/RETRIEVAL_EVALUATION_2026-10-19.md)、[英文优化](docs/RETRIEVAL_OPTIMIZATION_2026-10-19.md) |
| 新十二题 / 模型知识对照 | 十道计分题 Recall .4833，跨篇 .2222；oracle 原文不是实际检索成功，两个排序候选未采用 | [独立新题与有限优化](docs/INDEPENDENT_VALIDATION_2026-10-19.md) |
| 一轮 / 三轮补查 | 有局部收益与旧题退步；三轮未超一轮，轮数与候选深度一起变 | [一轮](docs/EVIDENCE_COMPLETION_2026-10-19.md)、[三轮](docs/COMPLETION_ROUNDS_2026-10-19.md) |
| 全部八篇与增强 / 两轮 | 42 题：原 .7361/.4899，全部增强 + 两轮 .7242/.4797；8 次真实问答未补足两题 | [八篇完整评估](docs/ALL_PAPERS_EVALUATION_2026-10-20.md) |
| 本轮锚点 / 保留 / 预算 | 用户接受两轮，候选 120，独立比较 10 / 20，四项指标及交接完整留档 | [最新修复与预算](docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md) |
| 整体归一化 Precision 与进度核对 | 当前 Top-10 / 20 nP 为 .6790 / .7407；原四项及检索结果保留，79 项测试通过 | [归一化补充](docs/NORMALIZED_PRECISION_2026-10-20.md) |

历史“默认关闭”结论保留在对应报告中；当前用户选择与实际开关以本文件第 1～3 节为准，不把旧报告重写成新结论。

## 8. 新对话的下一步

归一化补充与进度核对已完成。当前阶段仍是科研论文 RAG 主干与离线评估完善，尚未验收新预算下的真实回答，也没有完整 Agent。以下为建议而非已执行工作：

1. 先用显式八篇版本与最终预算做少量真实回答验收（单篇、跨篇、缺证据拒答），同时核对论断、引用和上下文长度。只在生成即将发生时确认 API 连通；已有 Key 不重复索取，不重跑整个题集。
2. 针对仍缺的来源名称识别与跨篇覆盖做一轮有边界处理；沿用缓存、四项指标和旧题回归，避免无止境调参或按 Gold 硬编码运行时选择。
3. 再推进最小 Agent 闭环：记录所需证据 / 已有证据 / 缺口 / 行动 / 调用和时间预算，先接本地检索工具，设停止条件；不需要多 Agent。
4. P0 仍缺通用批量导入 / 去重 / 稳定文档身份 / 增量更新和失败恢复的完整生命周期；P1 仍缺真正独立盲测及服务级性能；P2 Agent、P3 联网证据来源 / 入库边界、P4 LangGraph 与演示 UI 按需推进。

有 arXiv、小批量免费接口的历史调研，但不把旧报告中的价格 / 限速当成永久当前事实；选服务前重新核对。当前主线无需先采购 GPU 或引入微调。

## 9. 文件与复现入口

- [归一化补充报表](evaluation/results/normalized_precision_20261020/report.md)、[完整新增指标 JSON](evaluation/results/normalized_precision_20261020/report.json)、[独立复核](evaluation/results/normalized_precision_20261020/verification.json)、[当前配置与资产核对](evaluation/results/normalized_precision_20261020/progress_audit.json)。
- [最新原始结果目录](evaluation/results/evidence_retention_20261020/comparison.json)、[独立复核](evaluation/results/evidence_retention_20261020/verification.json)、[预算采用依据](evaluation/results/evidence_retention_20261020/adoption.json)。
- [本次可见对话](docs/chat_history/RAG_2026-10-19_20_完整对话.md)、[工具记录压缩包](docs/chat_history/RAG_2026-10-19_20_tools.jsonl.gz)、[导出清单](docs/chat_history/RAG_2026-10-19_20_export_manifest.json)。
- [重写前完整 PROGRESS](docs/history/PROGRESS_BEFORE_RETENTION_2026-10-20.md) 保留原长期路线和全部阶段记录；[旧实验归档说明](docs/history/README.md)。
- `main.py` 问答；`build_semantic_index.py` 离线构建；`src/knowledge_base.py` 成对版本；`src/evidence_gap.py` 有界补查；`evaluation/run_evaluation.py` 原四项检索指标及整体 nP；`evaluation/summarize_normalized_precision.py` 只读取已有日志生成补充报表；`evaluation/run_answer_evaluation.py` 回答与引用检查。

仅重建归一化补充报表，不加载模型或调用 API（须使用新输出目录）：

```bash
python -m evaluation.summarize_normalized_precision \
  --output-dir evaluation/results/new_normalized_precision
```

直接运行 evaluation 默认会生成辅助查询；离线复评必须提供 `--auxiliary-cache`。`--no-auxiliary` 也可避免 API，但会禁用分解 / 改写，不能冒充同分解对照。

如确需重跑量化，以下使用已有辅助查询、不会新调用 API，但会消耗本机 CPU；请使用新的结果目录：

```bash
python -m evaluation.run_evaluation \
  --questions evaluation/all_papers_questions_en.json \
  --kb-version all-papers-8-20261020 \
  --candidate-k 120 --top-k 10 20 \
  --complete-evidence --completion-rounds 2 \
  --auxiliary-cache evaluation/results/all_papers_20261020/auxiliary.json \
  --output-dir evaluation/results/new_retention_replay
```

Mac 仍应使用前述受控线程环境 / Python 设置。已有完整结果无需重复计算；源码变更后再运行 `python -m unittest discover -s tests -v` 做相应回归。
