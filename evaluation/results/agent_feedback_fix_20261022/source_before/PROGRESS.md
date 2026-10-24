# Advanced-LLM-RAG 当前进度与交接

更新：2026-10-22（Asia/Shanghai）。工作区：`/Users/j/Desktop/Advanced-LLM-RAG`；Git 基点 `c2cd612`，已有大量未提交和未跟踪成果。本次核对并清理文件与文档，没有提交或推送。

**结论：本地 RAG/Agent 功能、`main` 三模式和两批对照均已实现；最新版 Auto 已改为 RAG 优先。P2.5 有可复核结果，但 Agent/Auto 的整体质量收益尚未成立；最终版本独立新题验收未完成，P3/P4 未开始。**

本页负责当前状态、约束与下一步；多轮原始交接转入[完整历史](docs/history/PROGRESS_THROUGH_2026-10-22.md)，包括全部失败、调用量、实验口径和复现命令。各实验原始文件及路径保留，[实验索引](evaluation/results/README.md)可逐轮查阅。桌面《RAG项目全流程与进度总览.md》与 [PROJECT_WORKFLOW](docs/PROJECT_WORKFLOW.md)内容一致，二者只描述预期路线，不表示实际完成。

## 1. 阶段状态

| 阶段 | 已完成 | 仍未完成或边界 |
| --- | --- | --- |
| 基础 RAG 与检索改进 | PDF、分块、混合检索、重排、问题分解、证据保留、规则补查、引用检查 | 解析/分块不保证无损，引用结构通过不等于语义正确 |
| P0 论文与知识库 | 三篇、五篇、八篇配对版本及校验、切换、回退 | 通用去重和完整增量导入生命周期延期 |
| P1 评测基线 | 检索指标、小规模12题固定 RAG 回答/拒答/成本记录 | 同助手出题审阅，非第三方盲评或大规模泛化 |
| P2.1～P2.4 | 需求绑定、证据判断、搜索/邻段、预算循环、生成与有限复核 | 早期h10/h11属于已知开发验收，不能覆盖最新版失败 |
| main 接入 | `rag`、`agent`、`auto` 共用初检与资源，保留各模式记录 | 函数默认rag；CLI默认auto；历史“尚未接main”已过时 |
| P2.5 对照与收尾 | 首轮12题 RAG/Agent、第一版Auto的8题三路径对照及原文审阅 | 实验完成与质量收益通过是两个状态；最新版尚无独立新题总成绩 |
| 最新 Agent/Auto 改进 | 排版引文/已知主体绑定修复、输入隔离、RAG优先Auto；251项历史离线回归通过 | h10仍降级，反馈稳定性与隐性漏答尚未解决 |
| P3 / P4 | 尚未开始 | 联网补证据、展示、交付材料待后续明确范围 |

## 2. 当前三条执行路径

- **固定 RAG**：分解 → Dense/BM25 → RRF → 全局BGE/子题局部证据 → 按来源信号最多两轮补查 → 生成 → 引用检查/必要时一次修复。常规完整问题通常为分解、回答两次调用。
- **固定 Agent**：共用一次初检后，独立规划需求、逐项检查，模型选择搜索/读取邻段/回答/停止，Python校验并执行；回答阶段逐项复核、必要时修订一次。
- **Auto**：先用固定RAG相同提示和证据生成/修复引用；出现明确缺口、无法回答或比较、引用失败才升级原Agent。普通路径没有额外门控调用。Agent事实输入只含问题、绑定需求、原文与论文目录，RAG草稿不作为事实证据。

`main(..., mode='rag')`保持Python原默认；命令行默认`--mode auto`。RAG未指定版本时读三篇激活指针；Auto/Agent仅支持八篇，不切换指针。同库比较必须让RAG显式使用八篇。运行命令见 [README](README.md)，保存记录模式见 [Agent 操作](docs/AGENT_REPLAY_GUIDE.md)。

**预算与失败：** 固定Agent最多1次分解+6次决策+4次回答=11请求；Auto另保留最多2次前置草稿/引用修复，最坏13请求。工具最多3行动，证据最多32段/24000字符；规划、状态修正或重复行动改选共用一次额度，不能因升级重置。回答最多初稿/复核/修订/再复核4次。全部missing时回答阶段本地说明缺口、0请求。网络/截断失败不自动重试，`finish_reason='length'`不能算完整输出。

Auto升级失败仅在原草稿引用结构合格时允许`degraded`保留，CLI非零；loop失败、草稿与原因均留档，不能计作完整成功或保证草稿事实正确。隐性漏答可能没有升级信号。新输出目录须为空，旧运行受输入/源码哈希约束，不强行覆盖或续写。

## 3. 已有质量与成本证据

| 冻结对照 | 固定 RAG | Agent | 第一版 Auto | 证据 |
| --- | --- | --- | --- | --- |
| P2.5 首轮12题严格通过 | 10/12 | 7/12 | 当时未加入 | [报告](evaluation/results/agent_p25_20261021/report.md) |
| 同12题可答核心macro | 94.17% | 64.17% | — | [原文审阅](evaluation/results/agent_p25_20261021/manual_review.md) |
| 同12题归因token | 34470 | 95440 | — | [复算](evaluation/results/agent_p25_20261021/summary.json) |
| 第一版Auto的8题严格事实/引用通过 | 8/8 | 6/8 | 6/8 | [报告](evaluation/results/auto_closeout_20261022/report.md) |
| 同8题必答完整且可交付 | 8/8 | 7/8 | 6/8 | [原文审阅](evaluation/results/auto_closeout_20261022/manual_review.md) |
| 同8题归因token | 23780 | 75091 | 62276 | [复算](evaluation/results/auto_closeout_20261022/summary.json) |

两批不可答题各路径均正确拒答2/2。12题Agent有3题规划失败，8题Agent/Auto也有校验失败；分母包括无交付题。8题的6道可答题初检Gold均齐，未验证可答题的补证增益。两批均同库、同模型、共享真实初检；归因token不可直接相加当实际账单。12题实际61请求/121397 token，8题实际68请求/149573 token。严格评分中背景定义与引用要求的差异及敏感性见原报告，不回改历史主成绩。

**最新开发回归，不能拼接成新准确率：** a03/a04的最终Auto复用已保存真实初检，各1次新生成恢复直答；固定Agent的a04恢复交付但仍过处理，a02回归不再附加原错误公式解释。h10触发升级且真实search一次，未取到所需RAG判据段落；已支持的Self-RAG需求反复被标partial却不给gap，唯一修正用完后`degraded`，核心仍1/2，未通过。

该轮跨版本开发累计32次新HTTP、98399 token（输入89087/输出9312），全部stop、HTTP失败/usage缺失/自动重试0；另精确复用1次已成功的同提示probe，33条逻辑调用不双计账单。联合门控试验未采用，阶段源码与全部失败保留。最新输入隔离版本真实走到反馈阶段，未进入最终生成/复核，后两者最新真实验证不能冒称完成。[改进流程与失败](evaluation/results/agent_auto_improvement_20261022/report.md) · [设计与采用理由](evaluation/results/agent_auto_improvement_20261022/design.md) · [分阶段汇总](evaluation/results/agent_auto_improvement_20261022/summary.json)

**选型：** 固定RAG继续作为质量和成本基线；Auto作为按需升级入口；固定Agent只在需要多步补证据的任务上考虑。普通路径调用从旧Auto通常4次降到2次是路径改进，尚无当前全题集token降幅或总体质量收益证明。

## 4. 优先级与下一步

完整性以用户所问和避免误解所必需的条件为准，保留用户已确认的三层标准：

1. **必须修复**：漏明确子问题、改变结论的单位/条件/范围缺失、跨论文或数据集混淆、编造事实/引错引用、正常问题无交付。
2. **按任务补充**：复现实验需要的定义/步骤/参数，做决策需要的限制条件。
3. **可以省略**：不影响当前任务的背景、例外和延伸。b03的S定义、b06的VGG背景不继续专门调试，原冻结严格1/3、核心7/9保留。

当前首要P1是**反馈状态稳定性**：没有相关新证据时，已完成需求被反复误标，无效partial/空gap消耗共享修正额度。可研究只复查受新证据影响的需求，同时允许真实冲突重新打开；当前未实现，不能把无效partial自动改supported或重置预算。

后续顺序：先明确反馈修复边界并作最小行为回归 → 另冻必答/补充和补证场景的新题，比较质量、升级/误升级、拒答、失败和成本 → 根据收益决定是否继续P3。**当前不再针对h10付费调试，不重跑旧32/68/61次请求来恢复上下文。** 旧失败题参与修复后只算开发集；不以背景细节满分作为推进条件，不为增加工具数量扩展项目。

本次任务只核对进度与清理文件，以上属于接续待办，没有实施新的Agent算法、评测或P3。

## 5. 配置、知识库与关键约束

| 项目 | 当前值 |
| --- | --- |
| Embedding / reranker | MiniLM `paraphrase-multilingual-MiniLM-L12-v2`，384维 / `BAAI/bge-reranker-base`，CPU |
| 候选 / RRF / 最终证据 | 每路120、RRF候选120、秩平滑常数60；最终10，子题局部3 |
| 规则补查 / 增强 | main按来源覆盖信号最多2轮，候选深度120/240；rewrite/HyDE关闭 |
| 评估入口 | 候选默认120；补查需显式启用，CLI轮数默认1；不同K独立选证据与补查 |
| 生成API | 配置模型`cn:deepseek-v4.1-flash`；历史响应标识`deepseek-v4.1-flash`；标识不独立证明上游权重 |
| 生成选项 | `thinking.type=disabled`、`temperature=0`、`max_tokens=4096`；本次未请求API验证连通性 |

| 知识库版本 | 分块数 / 维度 | 使用状态 |
| --- | --- | --- |
| `legacy-3papers-20261019` | 378 / 384 | 原三篇逐字节配对快照 |
| `semantic-mac-20261019` | 378 / 384 | **激活指针**；RAG省略版本时使用 |
| `arxiv-pilot-5-20261019` | 1019 / 384 | RAG/DPR/ColBERT/Self-RAG/CRAG，独立先导库 |
| `all-papers-8-20261020` | 1397 / 384 | 三篇/五篇已验证向量精确合并，Auto/Agent使用 |

原三篇为Transformer、DCNN/AlexNet、VGG，不含ResNet；五篇版本分别为RAG v4、DPR v3、ColBERT v2、Self-RAG v1、CRAG v3。各版`faiss.index`、`chunks.json`、`manifest.json`成套保留，位置ID不能跨版本混用。默认PDF构建只遍历本层，不能假定会递归导入全部八篇。[版本操作](docs/KNOWLEDGE_BASE_VERSIONS.md)

- 普通函数、字典、列表与原文件结构优先；重要Python代码补目的/输入输出/预算的中文注释，不新增无必要框架或CLI。
- MacBook Air/PyCharm为主开发环境，本次确认项目Python 3.11.9；具体芯片/内存不推测。Windows RTX 5060 Laptop/约8GB显存是历史用户记录，本次未实测Windows。
- 本项目不做Fine-tuning/LoRA/QLoRA；本地Embedding/BGE与API生成不要求新增GPU。两台电脑的虚拟环境、模型缓存、本机代理和未提交资料不会自动同步。
- 私有API配置、凭证、原始论文、成对索引、Gold、实验/失败和用户未提交工作保留；Git只同步已提交并推送的内容。
- FAISS为归一化`IndexFlatIP`，非HNSW；Chunk保留来源/页码/标题/章节，但标题未作为Embedding正文；Semantic参数500字符/percentile10不保证无损。
- 固定原问题增强前RRF锚点，保护初次局部Top-3；每个K独立补查，不能拿Top-20前缀冒充Top-10。BM25没有有效英文/数字词项时返回空。
- 引用编号结构、词法主体绑定、原文连续引文和模型review_passed均不等于独立语义验收；仍需核对重要断言与原文。

## 6. 检索基线与验证口径

42道历史Gold可答题，候选120、最多两轮、rewrite/HyDE关闭：

| 预算 | Precision | 整体nP | 宏Recall | MAP | MRR | 全Gold入选 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-10 | .1310 | .6790 | .7679 | .4837 | .5708 | 28/42 |
| Top-20 | .0714 | .7407 | .8115 | .4857 | .5727 | 30/42 |

Top-20 Recall增加4.37个百分点，未达当时预定5点门槛，默认10。逐题nP=`H/min(K,G)`，整体=`sum(H)/sum(min(K,G))`，不能平均逐题值；本集81条Gold均G≤K，整体nP等于micro recall，原Recall是macro。Gold非穷尽，不代表其他段落无用；检索覆盖、回答质量和成本分开报告。[量化入口](docs/PROJECT_METRICS.md) · [nP口径](docs/NORMALIZED_PRECISION_2026-10-20.md)

本次重新通过251项离线测试、网络尝试0；清理前后文件核验见[清理记录](docs/CLEANUP_LOG_2026-10-22.md)。本次无模型生成、无付费API、无重建索引或扩大评测。此前受控线程可稳定运行，但批量退出139根因仍未定位；完整实验已有结果不重复跑。

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m unittest discover -s tests -v
```

## 7. 文件导航与本次整理

[运行与模式](README.md) · [文档分类](docs/README.md) · [代码阅读](docs/CODE_READING_GUIDE.md) · [Agent工具/回放](docs/AGENT_REPLAY_GUIDE.md) · [实验目录](evaluation/results/README.md) · [完整历史交接](docs/history/PROGRESS_THROUGH_2026-10-22.md)

清理前README/PROGRESS/忽略规则/历史索引逐字节保存在[备份](docs/history/20261022_before_cleanup.zip)。实验路径与得分保持，当前说明从多轮历史中独立整理；删除范围仅可再生成的Python缓存和macOS元数据。[完整清理范围与验收](docs/CLEANUP_LOG_2026-10-22.md)
