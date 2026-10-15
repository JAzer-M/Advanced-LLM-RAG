# Advanced-LLM-RAG — 项目总进度、实验记录与跨对话交接文档

> **最后更新：2026-10-15（根据用户最新 Windows 运行日志、源码与 VGG 调试输出）**  
> **当前阶段：Query Rewriting + Multi-Query 已实现并完成六组对照评估；通用 `main.py` 已恢复并完成 Transformer 问答验证。下一步优先 Query Decomposition（面向跨论文比较问题），然后 HyDE、扩大 Evaluation、Generation/Citation 评估、Single-Agent 与 UI。**  
> **文件用途：**这是 `Advanced-LLM-RAG` 的长期项目事实、技术决策、代码模块、实验数据与跨对话交接文件，不是通用 RAG 笔记。新对话优先阅读 **0、7、9、11、13、14 节**；需复盘时通读全文。
>
> **用户明确要求的提醒：清楚详细的尽你最大努力的回想起RAG项目的所有对话与内容**
>
> **准确性说明：**基于用户上传的 2026-10-14 旧版进度文件、可见的 RAG 项目对话、用户贴出的源码与终端日志，以及已提供的 Evaluation 文件整理；**不代表逐字扫描过所有历史对话，也不代表已远程读取用户 Windows/Mac 本地最新仓库**。对用户实际运行结果与上传源码区分标注；数据冲突时以最新实测为准，不凭空推断 Git HEAD、未见文件内容或新功能已完成。

---

## 0. 新对话一分钟交接——最重要的事实（2026-10-15）

1. **最终目标不变**：面向 AI/LLM 实习简历的**科研论文分析 Advanced-LLM-RAG / Single-Agent（Agentic RAG）**：PDF 知识库、页码/章节证据、单篇问答、跨论文比较、复杂 Query Decomposition、条件性多步检索、引用/可信度/拒答、评估及 UI。**Agentic 部分仍未实现**。
2. **硬性边界**：RAG 项目**不做 Fine-tuning / LoRA / QLoRA**；独立 PyTorch Transformer 架构项目不混入本项目。现阶段手写核心组件，不依赖 LangChain/Matt Skills；LangGraph 只是后期潜在的单 Agent 编排工具。
3. **设备**：MacBook Air + PyCharm 主要开发；Windows RTX 5060（约 8GB VRAM）已运行本地 **`Qwen/Qwen3.5-2B`**，兼执行需要 Query Rewriting 的 Evaluation。通过 Git/GitHub 同步**被跟踪代码**，目前**没有** Mac→Windows 实时模型 API。Windows 本地 Qwen 不能被 Mac 直接 import 调用。
4. **已完成数据处理与检索主干**：三篇论文共 **32 页**、Parser V1 约 **86 Documents**、Fixed/Recursive/Semantic = **340 / 340 / 385 Chunks**；MiniLM 384d + FAISS FlatIP；Dense/BM25/RRF；CrossEncoder MiniLM 和 BGE；本地 Qwen 生成、引用式 Prompt、Gold Evidence、Candidate Pool、12 组早期检索基线。
5. **最近新增**：`src/query_rewriter.py` 已实现两版 Prompt 实验；`src/hybrid_retriever.py` 的 RRF 已支持可选 `extra_results`（两路/四路）；`main.py` 已整理为可开关的通用 Retrieval → BGE → Qwen，不再硬编码 VGG Source Filter 或 Chunk ID；`evaluation/run_evaluation.py` 已重写为**公平的六组对照**，Original Baseline 不受改写污染，每题只调用 Qwen 重写一次。
6. **最新确认的检索实测（Semantic 385、BGE、5 题、Top-5）**：Dense **0.2400 / 0.3733 / 0.1844 / 0.4333**，BM25 **0.2800 / 0.4500 / 0.4106 / 0.6000**，Hybrid **0.2800 / 0.5667 / 0.4367 / 0.7000**，**Original Hybrid+BGE、Rewritten Hybrid+BGE、Multi-Query+BGE 三者均为 P@5 0.4000 / R@5 0.6900 / MAP@5 0.4119 / MRR@5 0.5800**；更关键：在 q1～q5，**三者最终 Top-5 Chunk ID 和顺序逐题完全相同**（详见第 7、13 节）。这是在 5 题的小评估集下**没有观测到改写/四路融合的额外收益**，不是宣称该技术普遍无用。
7. **不同模型/配置的历史不要混淆**：10-14 的 **Fixed + Hybrid + `ms-marco-MiniLM-L6-v2`** 曾得到最高 R@5=**0.7167**，属旧模型比较；10-15 主线实际选择 **Semantic + BGE** 做 Query Optimization 对照，不能把两者数值变化归因于 Query Rewriting 或认为后者绝对更优。
8. **重要失败案例**：q5（VGG vs DCNN）跨论文比较仅找回 1/5 Gold Chunks，说明需要 **Query Decomposition / 双源证据覆盖**。VGG 另一条口语化查询的手工测试揭露 RRF Top-20 截断（关键 Chunk 246 在 RRF Rank22）、BGE 跨论文干扰、上下文碎片、2B 生成/引用错误；Parser V1 确有跨页/表格/公式问题，已研究 Block-Level Parser V2，但**决定暂缓深度 PDF 解析开发，回归主线**。
9. **当前最近一次 `main.py` 实测**：关闭 Multi-Query，提问 Transformer 为何使用位置编码；BGE Top-5 包含 `Attention is all you need.pdf` p5 `3.5 Positional Encoding`（Rank 5），Qwen 答案正确并引用 `[5]`（只是编号仍放在末尾）。通用问答流程已恢复。
10. **唯一近期开发方向**：**Query Decomposition**（从 q5 的双论文比较切入），之后再 HyDE 的独立实验、扩充 Evaluation、Generation/Citation/Abstention 评估、Single-Agent、UI/README。若用户先要落盘实验摘要，可另建 `evaluation/results/query_optimization_v1.md`，但本文件已保留全部关键结果。保持**一次一个操作**，除文件混乱或用户明确要求才给整文件；不自动 commit/push。

---

## 1. 项目定位、路线与“最终成品”的准确理解

### 1.1 要做的是什么

项目名：**`Advanced-LLM-RAG`**。目标使用场景是**科研论文分析**，不是通用聊天机器人，也不是只展示 FAISS 搜索结果的 demo。预期可对已导入 PDF 提出以下类型的问题：

- **单篇精确问答**：例如 VGG 为何使用 3×3 卷积核，Transformer 为什么使用位置编码、缩放点积注意力。
- **跨论文分析**：例如比较 VGG 与 `DCNN.pdf` 对卷积核尺寸的选择，必须分别查到两篇文章的证据再综合。
- **复杂查询处理**：必要时识别查询类型、改写模糊查询、拆解复合问题、组合多个检索结果。
- **基于证据回答**：结果应有相关论文、页码、尽可能提供章节和可核查引用；找不到依据时不能让模型凭空编造。
- **Agentic 行为（最终目标）**：一个 Agent 能根据当前问题和证据情况决定使用哪类检索、是否改写/拆解、是否再检索，以及何时停止并生成回答；不默认要求多 Agent 架构。
- **可复现的对照实验与展示**：能比较 Basic RAG、Hybrid、Reranker、Query Optimization、Agentic 与无 RAG 的差异，报告检索、生成、引用和时延方面指标，最终形成 README 与 UI。

### 1.2 离线知识库建设流程（已经实现主干）

```text
本地科研论文 PDF（3 篇）
  │
  ├─ src/pdf_loader.py：PyMuPDF 读取 / 标题与章节识别 / 布局处理
  │       └─ Document：text、source、page、title、section
  ├─ src/chunking.py / src/chunking_recursive.py / src/chunking_semantic.py：对应分块方案（模块名称按当前真实仓库核对）
  │       └─ 保留 Metadata 的 Chunks
  ├─ src/embedding.py：Sentence-Transformers MiniLM，384 维，归一化
  ├─ src/vector_store.py：FAISS IndexFlatIP，持久化 *.index
  └─ src/chunk_storage.py：保存/加载对应的 chunks*.json

查询时另在内存中由 Chunks 创建 BM25 索引。
```

### 1.3 当前线上/交互查询主线（检索已实现，Windows 上曾成功生成答案）

```text
User Question
  → Dense Query Embedding → FAISS Top-20 ──────┐
  → BM25 Query Retrieval → BM25 Top-20 ───────┤
                                              ↓
                                     RRF(k=60) 融合 Top-20
                                              ↓
                                     Cross-Encoder Reranking
                                              ↓
                                            Top-5
                                              ↓
                                  Context / Prompt Construction
                                              ↓
                                  Windows 本地 Qwen3.5-2B
                                              ↓
                                      Answer（引用仍待完善）
```

**2026-10-15 状态更新**：通用 `main.py` 已从 VGG 硬编码调试版整理为 **Original Query（默认）或可选 Multi-Query → Dense/BM25 → RRF → BGE → Top-5 Context → Windows 本地 Qwen**。用户已实际跑通 Transformer 位置编码题，得到正确、引用 `[5]` 的答案。**Citation Validation、自动 Source Routing、Context Expansion 正式版及 Agent 仍未实现。**

### 1.4 后续智能查询主线（Rewriting / Multi-Query 已完成实验；其余仍待实现）

```text
User Question
  → Query Analysis / Routing（后期）
      ├─ 简单问题：原始查询；Query Rewriting / Multi-Query 已有实验开关，当前未验证收益
      ├─ 跨文档 / 多方面问题：Query Decomposition → 子问题检索 → 合并证据
      └─ HyDE：按对照实验需要启用，非所有查询必开
  → Dense + BM25 → RRF → Reranker
  → Context Management（去重、片段组织、token 预算、上下文扩展）
  → Qwen Answer Generation（证据约束、来源/页码/章节）
  → Faithfulness / Citation / Abstention 检查
  → Single-Agent 规划、观察、条件性补查（后期）
  → UI 展示和完整 Eval
```

**不在路线内**：本项目的 Fine-tuning/LoRA/QLoRA；与独立 Transformer 模型架构研究项目混合；现阶段用 LangChain 替代手写检索器。

---

## 2. 环境、Git 与两台电脑之间的真实关系

| 内容 | 已知情况 | 备注 |
| --- | --- | --- |
| Mac | MacBook Air，PyCharm | 主代码开发、文档解析、数据处理、检索、评估 |
| Mac Python | 项目内 `.venv`，历史配置 **3.11.9** | 不要混淆用户其他 Python 3.13/3.14 学习项目 |
| Mac 库 | `pymupdf`、`sentence-transformers`、`numpy`、`faiss-cpu`、`torch`、`transformers` 等 | 列表取自项目历史核查，不是实时 pip freeze |
| Windows | RTX 5060 Laptop GPU，约 8 GB VRAM，PyCharm | Qwen 推理、需要重写查询的完整评估也在 Windows 成功运行；独立 `.venv` |
| Windows Python | 历史使用 3.11.9 | 与 Mac 独立安装、独立环境 |
| Windows PyTorch/CUDA | 历史核实 `torch 2.13.0+cu130`、CUDA 可用 | 当前版本以 `torch.__version__` 实测为准 |
| Windows Transformers | 历史记录 `5.19.0` | Qwen3.5 `AutoProcessor` / `AutoModelForMultimodalLM` 接口可导入 |
| LLM | Hugging Face **`Qwen/Qwen3.5-2B`** | Windows 本地缓存、BF16、`device_map='auto'`、`local_files_only=True` |
| GitHub | `https://github.com/JAzer-M/Advanced-LLM-RAG.git` | 历史 commit `4c6c168`、后来检索基线 commit `6e644b`；**未确认当前 HEAD 或最近改动是否已推送** |
| Mac 历史路径 | `/Users/j/Desktop/Advanced-LLM-RAG` | 路径以用户电脑为准 |
| Windows 历史路径 | `C:\Users\J\Desktop\Advanced-LLM-RAG` | 路径以用户电脑为准 |

**Git/GitHub 注意**：

- Git 在本机保存被跟踪文件的版本；GitHub 提供远程托管与两机同步，clone / pull / push 只同步被追踪的内容。
- 项目 `.gitignore` 历史上排除了 `.venv/`、IDE/Python 缓存、模型权重/缓存、`data/raw/` 和 `data/processed/`；**原 PDF、索引、Chunk JSON 可能必须在 Windows 单独准备或生成**。新增的 `evaluation/pool_*.json` 和 `questions.json` 是否被 Git 跟踪，应以实际 `git status` 为准。
- HF 模型缓存不在 GitHub 中；**Windows 本地模型 ≠ Mac 模型、也 ≠ 已有远程推理服务**。
- 两台电脑不共享进程或 GPU；`@lru_cache` 也不能让 Mac 跨网络复用 Windows 模型。当前若运行含 `generate_answer` 的完整脚本，通常应在已准备模型与所需数据的 Windows 上执行。
- 不要擅自 commit/push；优先让用户了解当前更改与原因。

**历史 Windows LLM 相关排错**：曾遇 `Qwen3VLVideoProcessor requires the Torchvision library`，安装 `torchvision` 后解决；缺失 `causal_conv1d` / `flash-linear-attention` 时会有优化内核 fallback 警告，但不必然妨碍成功生成。曾观察 `Loading weights ... 617/617`、`cuda:0`、BF16，独立生成成功；`max_new_tokens=128` 曾造成答案可能截断，后续 Windows 曾调高到 512 并打印 `Generated Token Count`；最终实际参数以当前 `llm.py` 为准。

---

## 3. 论文语料、Parser V1 与 Metadata

### 3.1 确认的 PDF 语料

| `data/raw/` 文件 | PDF 页数 | 内容与用途 |
| --- | ---: | --- |
| `Attention is all you need.pdf` | **11** | Transformer，位置编码、Scaled Dot-Product Attention 等 |
| `DCNN.pdf` | **7** | 早期 CNN（AlexNet）论文相关内容；具有**双栏布局** |
| `VGG.pdf` | **14** | VGG，小卷积核、网络深度、性能等 |
| **合计** | **32** | 当前仅这三篇，不含 ResNet |

重要历史纠错：早期项目里曾把第三篇记为 `ResNet.pdf`；实际内容是 VGG，已经更名 `VGG.pdf`。**当前语料不是“Transformer + DCNN + ResNet”**。任何基于 ResNet 的旧说明都不能当成当前知识库事实。

### 3.2 `src/pdf_loader.py`（Custom PDF Parser V1，已实现/测试）

- 使用 PyMuPDF 读取文档，而非仅仅把整个 PDF 当作一个大字符串。先前最简单版本按页提取 `text/source/page`。
- 后来提取 Block / Line / Span 的内容、字体大小、字体、位置/BBox 等布局信息，借助字体和章节编号模式识别标题、小节标题。
- 处理标题被拆成多个 Span/Line 的情况；曾专门修复 `Attention is all you need` 的 `3.2 Attention`、`3.2.1 Scaled Dot-Product Attention`，也检查过 `DCNN.pdf` 的 `4.2 Training on multiple GPUs`、`4.3 Local response normalization`、`4.4 Overlapping pooling`。
- 将检测到的 Section 分配给其后的正文，并在跨页时继承当前章节；`title` 找不到时使用文件名回退。
- `DCNN.pdf` 是双栏，因此提供了类似 `load_pdfs(raw_dir, two_columns_files={"DCNN.pdf"})` 的文件级布局处理入口，避免简单按页坐标排序导致左右栏阅读顺序交错。
- 近期成功产出 **86 个按章节/区域拆分的 Documents**（区别于物理 PDF 的 32 页）；每个 Document 预期携带 `text/source/page/title/section`。
- 仍有工程限制：PDF 复杂公式/表格、列阅读顺序、标题误判、跨页文本与特殊字符解析不一定完美；Parser V1 完成≠工业级文档解析完成。

### 3.2.1 2026-10-15 发现的 VGG 解析局限（详见第 14 节）

- Page 2 `2.3 DISCUSSION` 在 `... effective receptive field of 5 × 5; three` 处结束；Page 3 先出现 Table 1、Table 2，再出现 `such layers have a 7 × 7 effective receptive field`。这是 PDF 原始分页/布局的事实，**不是单凭 Semantic Embedding 阈值造成**。
- PyMuPDF Text Blocks 将 Table 2 和续接正文识别为不同 Block，但 `page.find_tables()` 在 VGG p3 检测到 **0** 张表（无明显网格的表格不能仅依赖自动识别）。
- 公式 `3 × 3²C² = 27C²` 抽取为含异常字符的文本（例如 `32C2`），对公式问答存在直接风险。
- 已创建独立 `src/pdf_loader_v2.py` 小型实验（Block/BBox/初步 `table_candidate` 与 `figure_candidate`），**还没有正式的表格区域划分、跨页合并或 V2 索引**。保留原有 V1/Semantic 385 Baseline，暂缓 Parser V2 深度开发。

### 3.3 Metadata 的结构与使用边界

常见 Chunk 格式（结构示意）：

```python
{
    "text": "...",
    "source": "VGG.pdf",
    "page": 3,
    "title": "VGG",
    "section": "2.3 DISCUSSION",
    "chunk_id": 223,   # 依操作/文件而定，可能在持久化或检索阶段指定
}
```

已做过检查：三套 Chunk 中 `text/source/page/title/section` 等关键字段存在，`title` 不为空；**`section` 允许为 `None`**，不能把“字段存在”误读为“每个 Chunk 都有非空章节”。统计曾显示 Fixed/Recursive 各 **330** 个 Chunk 有有效 Section、Semantic **374** 个有有效 Section。

必须区别：**保存 Metadata、在返回结果中传递 Metadata、将 Metadata 拼入 Embedding/BM25 索引文本，是三个不同的动作。** 当前实验没有确认将 `title/section` 统一加入 Embedding 输入或 BM25 文本，因此不能说此次分数变化是“Metadata 融入向量”带来的提升。

---

## 4. Chunking、Embedding、FAISS 与持久化——最新核对过的版本

### 4.1 Chunking 实验历史

三种 Chunking 由不同脚本/模块实现与调用；其中最新已经直接审查了 `src/chunking.py`（Fixed）和 `src/chunking_semantic.py`（Semantic）：

- **Fixed**：按固定字符长度切割，历史参数 `chunk_size=500`、`chunk_overlap=100`；单位为**字符**不是 tokenizer token。
- **Recursive**：尽量沿自然分隔符（段落/换行/句子等）拆分，再在需要时进一步递归切割，维护上限与一定重叠。
- **Semantic**：真实代码位于 **`src/chunking_semantic.py`**，先正则切句→句子 Embedding（归一化）→相邻余弦相似度→低分位语义边界→最多 500 字符合并；用于**当前 385-Chunks 索引的构建入口实参为 `max_chunk_size=500, percentile=10`**（函数默认值 20，测试入口也曾用 20）。逐 `document`（按页/章节）处理，无法跨页接句。单句超 500 字符时回退强制字符切割；过滤长度 ≤10 字符的短句、<50 字符的 Chunk，存在少量文本被丢弃的设计风险；不要把它当成无损的段落重组。

**历史中曾有多个不同语料/Parser/阈值对应的数量：**

| 阶段 | Fixed | Recursive | Semantic | 解释 |
| --- | ---: | ---: | ---: | --- |
| 最早 Basic RAG | **330** | — | — | 旧版简单 PDF 按页提取后的固定分块 |
| 中间一次 Metadata-Aware 测试 | **330** | **331** | **403** | **旧历史快照；已过时**，不能用于最新评估 |
| **最新 Custom Parser V1 + Index** | **340** | **340** | **385** | **当前有效实验资产** |

最新曾比较 Fixed 与 Recursive：两者虽然都为 340 Chunks，但不是同样文本——按对应位置对齐只有 **13** 个文本完全相同；平均长度 Fixed 约 **450.24** 字符、Recursive 约 **424.34** 字符。不要因为数量相等而判断算法效果相同。

### 4.2 Embedding 与 FAISS

- 模型：`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`。
- 文档 Embedding 维度：**384**；历史采用归一化向量，FAISS 使用 `IndexFlatIP`。**归一化向量的内积才可以对应 cosine similarity**，必须确保 Query 与 Document 编码处理一致。
- `IndexFlatIP` 为**精确内积近邻搜索**，不是项目中实际用了 HNSW/NSW 等 ANN 图索引；用户虽然学过 HNSW，但本项目当前实现是 FlatIP。
- `src/vector_store.py`：`build_index()`、`save_index()`、`load_index()`；`src/chunk_storage.py`：`save_chunks()`、`load_chunks()`；`src/embedding.py`：`load_embedding_model()`、`embed_chunks()`；`src/retriever.py`：`retrieve()`。
- 数据对齐十分关键：`FAISS` 的向量序号必须与对应 `chunks` 列表的 `chunk_id`/位置对应。用户曾对 Fixed Index 重构向量并用重新 Embedding 做抽查：位置 **0、170、339** 的余弦相似度均为 **1.0**，没有观察到错位。
- 已验证三套 Index 的 `index.ntotal == len(chunks)`；向量维度 **384**。

### 4.3 当前六个重要产物（必须成对使用）

| 方案 | `data/processed/` Chunks | `data/processed/` FAISS | Chunk/Vector 数量 |
| --- | --- | --- | ---: |
| **Fixed** | `chunks.json` | `faiss.index` | **340** |
| **Recursive** | `chunks_recursive.json` | `faiss_recursive.index` | **340** |
| **Semantic** | `chunks_semantic.json` | `faiss_semantic.index` | **385** |

切换实验方案时，必须**同时切换索引与 Chunk JSON 路径**。不能拿 Fixed `faiss.index` 对 Semantic `chunks_semantic.json`，也不应该只看向量数碰巧相等就认为 Fixed 与 Recursive 可互换。

---

## 5. Retrieval：四条已经实现并实验过的检索方法

| 方法 | 模块 / 主要接口 | 要点 |
| --- | --- | --- |
| Dense | `src/retriever.py` → `retrieve()` | Query 同模型嵌入、归一化、FAISS Top-K |
| BM25 | `src/bm25_retriever.py` → `build_bm25_index()` / `retrieve_bm25()` | 从 Chunks 建立词项统计与关键词检索 |
| Hybrid | `src/hybrid_retriever.py` → `reciprocal_rank_fusion()` | 按 Dense/BM25 的排名做 **Reciprocal Rank Fusion (RRF)**，解决两类得分量纲不同的问题 |
| Hybrid + Reranker | `src/reranker.py` → `rerank_results()` | CrossEncoder Query–Chunk 打分，重排 Hybrid 候选 |

实际使用/评估的典型配置：

```text
Dense Top-20 + BM25 Top-20
    ↓
RRF (k=60) → Hybrid Top-20
    ↓
CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")
    ↓
Final Top-5
```

RRF 的 `k=60` 是**融合公式中的秩平滑常数**，不是最终返回 60 个文档。所有检索方法在 Evaluation 中统一比较 Top-5；`candidate_k=20` 用于给 Reranker 更大的选择池。

**实现上的经验**：

- 检索记录应保留 `text/source/page/title/section/chunk_id`，而不是只返回相似度分数或只返回字符串。
- 为避免一个 Chunk 在 Reranking 后丢失身份，优先将原始候选 dict 复制并保留 `chunk_id`；`evaluation/run_evaluation.py` 的 `get_result_ids` 有基于 `source/page/text` 反查的兜底，但不应把兜底当常规流程。
- 在评价代码中 CrossEncoder 应只初始化一次，避免每题重复加载。
- CrossEncoder 不是在 FAISS 中进行初检；它是对初检候选的二次排序。
- 单次检索结果看上去主题相近，不等于能够直接回答用户所问的问题；后续按完整引用与覆盖度判断。

### 5.1 2026-10-15：BGE Reranker 与四路 RRF 新增功能

- 除原来的 `cross-encoder/ms-marco-MiniLM-L6-v2`，又测试了 **`BAAI/bge-reranker-base`**，`CrossEncoder(..., device="cpu")`；BGE 不一定在每种 Chunking 或每项指标上胜出（量化见 7.5）。
- `src/hybrid_retriever.py` 的接口现为 `reciprocal_rank_fusion(dense_results, bm25_results, k=60, top_k=5, extra_results=None)`，遍历 `[dense_results, bm25_results, *(extra_results or [])]`，支持 Original Dense/BM25 与 Rewritten Dense/BM25 的**等权四路 RRF**。按 `chunk_id` 汇总 RRF 分数并去重，保存 `source/page/title/section/text`。默认不传额外列表时与旧两路调用兼容。
- 检索 Top-20 指**每一路**的候选数；RRF Top-20/40 指**融合后进入 BGE 的数量**；最终 Top-5 指重排输出。三者互不相同，调试时不可混淆。
- 为单题 VGG 故障诊断，曾临时将四路 RRF Top-20 改成 Top-40，并对候选硬过滤 `source=="VGG.pdf"`；它们只是诊断手段，**干净 `main.py` 已移除 VGG 强制筛选，默认 RRF Top-20**。

---

## 6. Gold Evidence、问题集与 Candidate Pool——本轮已完成

### 6.1 Evaluation 的实际问题集

`evaluation/questions.json` 当前定义 **6 个问题**，其中 **5 个可回答，1 个 Out-of-Scope**：

| ID | 类型 | 主题 |
| --- | --- | --- |
| q1 | `single_document` | `Why does VGG use small 3x3 convolutional filters?` |
| q2 | `single_document` | `Why does the Transformer use positional encoding?` |
| q3 | `single_document` | `Why does the Transformer use scaled dot-product attention?` |
| q4 | `single_document` | `How does the DCNN paper use data augmentation to reduce overfitting?` |
| q5 | `multi_document` | `How do VGG and DCNN differ in their use of convolutional filter sizes?` |
| q6 | `unanswerable` | `What was NVIDIA's stock price on October 10, 2026?` |

**q6 在当前 `run_evaluation.py` 中被跳过**（没有 Gold Evidence），所以现在的 P/R/MAP/MRR **不能用于评价“模型是否会拒绝回答”**。Abstention 要在后续答案级评估中单独测试。

### 6.2 Gold Evidence 如何判断

`evaluation/run_evaluation.py` 中的 `normalize_text()` 使用 NFKC + 规范化空白 + 转小写；`get_gold_chunk_ids(question, chunks)` 要求：

1. `chunk["source"] == evidence["source"]`；
2. `chunk["page"] == evidence["page"]`；
3. 标准化后的 `quote` 是标准化后的 `chunk["text"]` 子串。

将满足条件的 Chunk ID 汇总为 `set`，避免同一 Chunk 被多条 Quote 重复计入；无法匹配的 Evidence 列入 `unmatched`。因此不同 Chunking 可能各自对应不同数量的 Gold IDs，**不应跨方案直接比较 Chunk ID 的数值**。

### 6.3 最近的人工标注完善（2026-10-14）

- q1 原本只有部分证据，候选池揭示漏掉了小卷积核的局部感受野、堆叠感受野、空间上下文和大核分解的正则化信息。用户现已补到 **7 条 Evidence**。对三种 Chunking 都验证全部匹配，分别得到：

```text
Fixed:     [204, 209, 217, 222, 223, 254]
Recursive: [202, 207, 215, 220, 221, 253]
Semantic:  [229, 237, 246, 250, 251, 287]
```

  即每种方案 **7 条 Evidence → 6 个去重 Gold Chunks**，因为部分 Quote 命中同一 Chunk；不匹配数量为 0。
- q4 原有 4 条 Evidence，分别覆盖随机裁剪/水平翻转以及 RGB PCA；经 Candidate Pool 审查，补充 `DCNN.pdf` p4 `"artificially enlarge the dataset"` 后成为 **5 条 Evidence**。用户反馈 Fixed/Recursive/Semantic 的 **unmatched=0**。
- q2 当前为 2 条、q3 为 3 条、q5 为 5 条，已对照上传的 Candidate Pools 审查；本轮没有明确必要继续添加。
- **快照差异提醒：**本次聊天上传到可访问容器的 `questions.json` 是**添加 q4 第五条之前**的旧快照（里面 q4 仍 4 条）；但用户随后明确报告已添加并三种方案匹配失败均为 0，最新 12 组评估又由用户实测给出。不能把这个旧上传快照覆盖到用户已经改好的本地 `questions.json`；后续再次核查应以本地最新文件为准。

### 6.4 Candidate Pool 的作用与文件

为防止因为 Gold Evidence 漏标而误把有效检索判为错误，曾临时在 `evaluation/run_evaluation.py` 里加入 Pool 收集逻辑：对每题每种方法 Top-5 汇总去重 Chunk，保存 Query、`chunk_id`、源文件/页码/标题/章节、文本以及 `retrieved_by: [{method, rank}, ...]`。

| 文件（在 `evaluation/` 下） | Fixed/Recursive/Semantic | q1 | q2 | q3 | q4 | q5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `pool_chunks.json` | Fixed | 11 | 10 | 13 | 10 | 14 |
| `pool_chunks_recursive.json` | Recursive | 11 | 10 | 11 | 9 | 13 |
| `pool_chunks_semantic.json` | Semantic | 13 | 11 | 10 | 9 | 16 |

已上传三份 Pool 做交叉审查：不同 Chunking 内的 ID **互不通用**；相似/重叠文本不可只按 ID 去重。Pool 只覆盖各 Retriever Top-5 的候选**并非全部语料的穷尽人工标注**，审查后仍可能存在没被捞出来的 Relevant Chunks。

**现在的状态**：这些 Pool 属于一次性 Evaluation 审计材料。用户已被指导从 `run_evaluation.py` 中删除 `pool = {}`、`question_pool` 收集循环、`pool_path`/`json.dump(pool, ...)` 三处临时逻辑，保留 `test_cases`、检索方法字典与指标计算；之后确实已经重新跑出 Evaluation 输出。**旧 Pool JSON 不应每次评估重新覆盖，也无须反复要求用户上传。**

### 6.5 标注与实验方法的局限

- 当前只有 **5 道可回答问题 / 3 篇 PDF**，样本太小，不适合据此声称泛化最优。
- 目前采用 **Chunk-Level** 标注：多个重叠 Chunk 可能包含同一段信息；跨方案 Gold Chunk 数不同，Recall/MAP 等指标会受到分块粒度影响。
- Gold Evidence 是基于原文 Quote 的**部分相关性标准**。Pool 减少漏标，但不能证明相关 Chunk 已被穷尽。
- 后续如有必要，可补充 **Evidence-Level Coverage/Recall**（某个回答所需证据是否被覆盖），或文档级覆盖度、Generation/Citation 评估；不必因此阻塞当前 Query Decomposition 主线。
- 修改 Evidence 后重新算出的数字**不是 Retriever 模型训练后提升**，仅仅是相关性判断基线变化；旧版数字不能当成同一数据集下的公平对照。

---

## 7. Retrieval Evaluation：10-14 历史 MiniLM 基线 + 10-15 BGE / Query Optimization 最新六组

**以下 12 行专指 2026-10-14 的历史比较**：三篇论文、5 道可回答问题，`k=5`，检索候选 `candidate_k=20`；Dense 使用 MiniLM 384d/FAISS；Hybrid 通过 RRF(k=60)；Hybrid+Reranker 使用 **`cross-encoder/ms-marco-MiniLM-L6-v2`**（不是 BGE）。q6 不计入平均数。当前 10-15 BGE/Query Optimization 的最新结果另见 §7.5–7.7。

| Chunking | Retriever | Precision@5 | Recall@5 | MAP@5 | MRR@5 |
| --- | --- | ---: | ---: | ---: | ---: |
| **Fixed** | Dense | 0.1600 | 0.1833 | 0.1267 | 0.4400 |
| Fixed | BM25 | 0.2400 | 0.4333 | 0.4028 | 0.6000 |
| Fixed | Hybrid (RRF) | 0.3200 | 0.5667 | 0.3506 | 0.6000 |
| **Fixed** | **Hybrid + Reranker** | **0.3600** | **0.7167** | 0.3981 | 0.6500 |
| Recursive | Dense | 0.2000 | 0.3500 | 0.1833 | 0.5067 |
| Recursive | BM25 | 0.2800 | 0.4667 | **0.4517** | 0.6000 |
| Recursive | Hybrid (RRF) | 0.3200 | 0.6333 | 0.4089 | **0.7000** |
| Recursive | Hybrid + Reranker | 0.3200 | 0.6167 | 0.3331 | 0.6000 |
| Semantic | Dense | 0.2400 | 0.3733 | 0.1844 | 0.4333 |
| Semantic | BM25 | 0.2800 | 0.4500 | 0.4106 | 0.6000 |
| Semantic | Hybrid (RRF) | 0.2800 | 0.5667 | 0.4367 | **0.7000** |
| **Semantic** | **Hybrid + Reranker** | **0.3600** | 0.6633 | 0.3510 | 0.6667 |

### 7.1 哪些结论可以得出

- **最高 Recall@5：Fixed + Hybrid + Reranker = 0.7167**。
- **最高 Precision@5：Fixed + Hybrid + Reranker / Semantic + Hybrid + Reranker 并列 = 0.3600**。
- **最高 MAP@5：Recursive + BM25 = 0.4517**。
- **最高 MRR@5：Recursive + Hybrid / Semantic + Hybrid 并列 = 0.7000**。
- 三种分块下，Hybrid 的 Recall@5 均高于对应 Dense；但 Hybrid 不保证所有排序指标都更好。
- Semantic 在三种方案中的 Dense Recall@5 最高（0.3733），却**不是**最终全流程的全面冠军。
- Cross-Encoder 不保证加入后必涨分：Recursive 的 Hybrid R@5 **0.6333**，Reranker 后 **0.6167**；MAP **0.4089 → 0.3331**。Fixed 则 R@5 **0.5667 → 0.7167**。

### 7.2 工程选择，而不是“证明绝对最佳”

**2026-10-14 的阶段性选择：Fixed + Hybrid + MiniLM-L6 Reranker**。理由是该配置在当时测试中 Recall 最高、Precision 并列最高；**2026-10-15 为 Query Optimization 的实验便利，切换为 Semantic + BGE，并不意味着证明它取代前者成为全局最优。**保留 Recursive、Semantic 和固定分块作为对照。为什么不声称最优：样本少、金标非穷尽、Chunk 粒度与标注数量不同；还未进行足够多的用户真实问题和端到端答案评估。

### 7.3 值得保留的真实失败案例

1. **q1 Gold 漏标**：Fixed Dense 的相关段落 `VGG.pdf` p3 Chunk 223 说明 3×3 对 7×7 的分解、正则化，最初未算 Relevant；后补 quote 并验证。它说明 Evaluation 本身会出错，不能看到低分就立刻改模型。
2. **q5 多文档覆盖不足**：问题需要 VGG 和 DCNN 两份证据。在 Fixed 与 Recursive 四种 Retriever 的候选池 Top-5 中，缺少直接说明 DCNN 卷积核配置的有效片段；而 Semantic 的 Reranker 曾返回 `DCNN.pdf` 的 Chunk 160（11×11 卷积）。这是 Query Decomposition 的理想真实测试问题。
3. **q4 方法语义与邻近主题混淆**：Dropout 虽然也减轻 Overfitting，却不是问题要求的数据增强方法。对检索和 Gold 判断都要严格围绕问题。
4. **Reranking 效果不稳定**：某些题会把主题相近但不能回答问题的片段排到前面。优先保留并分析这一局限，不要为了让指标好看删除不利案例。

### 7.4 历史基线的版本区别

早期 330 Chunks 的旧 Evaluation、首次三种 Chunking 对比、旧 Parser 的 330/331/403 分块结果，以及本轮补 Gold 之前的指标，全部属于**不同代码/Parser/标注版本的历史记录**。可用来说明开发过程，**不得与本节 12 组指标在同一表里作为公平消融实验**。此前 `PROGRESS.md` 关于“Metadata Index 尚待重建/尚未重新评估”的状态已过时。

### 7.5 2026-10-15：更换 Cross-Encoder 模型的对照实验

同一批 Gold Evidence、Top-5，改用 `CrossEncoder("BAAI/bge-reranker-base", device="cpu")`，其 Hybrid+BGE 指标为：

| Chunking | Precision@5 | Recall@5 | MAP@5 | MRR@5 |
| --- | ---: | ---: | ---: | ---: |
| Fixed + BGE | 0.3200 | 0.5000 | 0.4372 | 0.5000 |
| Recursive + BGE | 0.2800 | 0.4000 | 0.3433 | 0.6000 |
| **Semantic + BGE** | **0.4000** | **0.6900** | 0.4119 | 0.5800 |

与 §7 的 MiniLM-L6 比较应按**同一 Chunking、同一 Gold、同一候选配置**谨慎进行；有的指标改善、有的下降。为了后续 Query Rewriting，对照实验固定采用 **Semantic（385 Chunks）+ BGE**，不是因为已经证明其全局最优。

### 7.6 2026-10-15：最终成功运行的六组 Query Optimization 对照

**真实配置**：三篇 PDF；Semantic `faiss_semantic.index` / `chunks_semantic.json`（385 × 384）；`questions.json` q1～q5、q6 无 Gold 跳过；MiniLM 向量检索与 BM25 每一路 Top-20；RRF `k=60`，重排候选 Top-20；BGE CPU Top-5；重排一律用 **Original Query**。`evaluation/run_evaluation.py` 已重构且用户在 Windows 成功运行，**退出代码 0**。Original Baseline 不经过改写；对每道有效题只调用一次 Qwen 重写，并复用该结果给 Rewritten-Only / Multi-Query 方案。

| Strategy | Precision@5 | Recall@5 | MAP@5 | MRR@5 |
| --- | ---: | ---: | ---: | ---: |
| **Dense（Original）** | 0.2400 | 0.3733 | 0.1844 | 0.4333 |
| **BM25（Original）** | 0.2800 | 0.4500 | 0.4106 | 0.6000 |
| **Hybrid（Original，未重排）** | 0.2800 | 0.5667 | **0.4367** | **0.7000** |
| **Hybrid + BGE（Original）** | **0.4000** | **0.6900** | 0.4119 | 0.5800 |
| **Rewritten Hybrid + BGE** | **0.4000** | **0.6900** | 0.4119 | 0.5800 |
| **Multi-Query（四路 RRF）+ BGE** | **0.4000** | **0.6900** | 0.4119 | 0.5800 |

**关键事实（不只是平均数相同）**：用户贴出全部逐题终端日志，最后三组方法在 q1～q5 的最终 **Top-5 Chunk ID 和顺序完全一致**：

| qid | Gold IDs | 三组 BGE 方法相同的最终 Top-5 IDs | 命中 Gold |
| --- | --- | --- | ---: |
| q1 | `[229,237,246,250,251,287]` | `[224,229,237,287,161]` | 3 / 6 |
| q2 | `[45]` | `[38,17,83,12,45]` | 1 / 1（Rank 5） |
| q3 | `[31,32]` | `[32,12,17,31,38]` | 2 / 2 |
| q4 | `[165,166,167,170]` | `[165,166,170,123,105]` | 3 / 4 |
| q5 | `[160,161,162,246,251]` | `[238,119,362,380,160]` | **1 / 5** |

**解释**：当前小规模测试中 Rewriting / Multi-Query 的新增计算没有改善最终相关 Chunk 排名；不代表不同 RRF 候选列表完全一样，也不代表未来复杂问题不能从 Decomposition/HyDE 获益。q5 跨论文比较失败尤其显著。BGE 相对未重排 Hybrid 提高 P@5（0.28→0.40）和 R@5（0.5667→0.69），但 MAP（0.4367→0.4119）和 MRR（0.70→0.58）下降；不能称作所有指标均提升。

### 7.7 实验代码污染的根因及修复（重要，避免新对话重复犯错）

- **旧 `run_evaluation.py` 错误**：设了 `use_rewriting=True`，将 `retrieval_query = rewrite_query(query)` 用于被称为「Original Baseline」的 Dense/BM25；然后又在 Multi-Query 分支重写一次。这样并非公平的 Original vs Rewritten 试验，同时额外耗费 LLM 调用。曾观察到“本次 Dense 四项指标恰好等于先前 Rewritten Dense”这一异常。
- **修正版**：`retrieve_two_ways(original_query, ...)` 固定生成 Original Dense/BM25；`fuse_and_rerank(original_query,...)` 固定使用原始问题排序；每题重写一次，分别创建 Rewritten 两路与四路 RRF；使用同一组 Gold IDs 和相同的 20/20/5 候选预算。`ENABLE_REWRITING=False` 可只测原始四法，`True` 测六法。
- **本轮 Rewriting V1/V2 手工测试**：V1 曾将口语化 VGG Query 改写成更抽象的“underlying rationale ... filter dimensions”，导致检索变差；V2 强调保留技术词、实体、不随意形式化、不给答案。标准五题的 V2 文本变化是：q1/q5 主要删除问号，q2 增加 *lack of inherent sequence order*，q3 原样，q4 改成 *utilize data augmentation techniques to mitigate overfitting*（主要同义替换）。另一条口语化 `What makes the small conv kernels in VGG useful?` 曾改写为 `What are the functional advantages of small convolutional kernels in VGG architectures?`，手工结果反而因跨论文干扰变差。
- **早期单路 Rewritten vs Original 复评（与最终六组实验不混淆）**：Semantic+BGE 的 Rewritten Dense P/R/MAP/MRR 曾达到 **0.2800/0.5733/0.3961/0.6667**，相对 Original Dense **0.2400/0.3733/0.1844/0.4333** 更高；但对应 Hybrid+BGE 最终仍为 **0.4000/0.6900/0.4119/0.5800**。说明早期确有 Dense 受益，却未传递到最终 Top-5；不能因 V2 在一题变差而断言全部重写有害。
- **结论有效范围**：只有 5 道可回答题、3 篇 PDF、Chunk-Level 部分 Gold；需要在未来评估集扩充后复测。实验结果最好另备 `evaluation/results/query_optimization_v1.md`；本节已完成长期归档，不能声称独立实验报告文件已经存在。

---

## 8. `llm.py`：Windows 本地模型推理与刚讨论过的缓存优化

### 8.1 模型及真实接口

用户最近给出的 `llm.py` 使用：

```python
import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM
from functools import lru_cache

@lru_cache(maxsize=1)
def load_llm():
    model_name = "Qwen/Qwen3.5-2B"
    processor = AutoProcessor.from_pretrained(
        model_name, local_files_only=True
    )
    model = AutoModelForMultimodalLM.from_pretrained(
        model_name,
        dtype=torch.bfloat16,
        device_map="auto",
        local_files_only=True,
    )
    model.eval()
    return processor, model
```

`generate_answer(prompt)` 基于 `processor.apply_chat_template(...)` 构造 `role="user"` 的文本消息，转为 PyTorch Tensor 并移动到 `model.device`，使用 `torch.inference_mode()` 包裹 `model.generate(**inputs, max_new_tokens=..., do_sample=False)`，截掉输入 Token 后用 `processor.decode(..., skip_special_tokens=True)` 返回答案。

### 8.2 之前已发现的缓存 Bug，及 10-15 的新运行迹象

用户第一次改造缓存时写了 `processor, model = load_llm()`，**但在 `generate_answer()` 后面仍重复调用了 `from_pretrained()`，还引用了只在 `load_llm()` 局部作用域内定义的 `model_name`**，这既会重复加载，也会 `NameError`。已指导改为：

```python
def generate_answer(prompt):
    processor, model = load_llm()  # 本进程首次加载，以后复用
    # 下方直接进入 message / inputs / generate / decode；不要再 from_pretrained
```

**状态更新**：2026-10-15 的 Windows 五题 Evaluation 日志中，Qwen 权重加载进度仅在第一道有效题首次重写前明显出现，后续 q2～q5 打印 `Generated Token Count` 时没有重复展示完整模型加载，**与单进程模型复用相符**。但尚未再次拿到完整最新版 `llm.py` 文件逐行确认，因此标记为“运行现象支持缓存/复用、源码细节仍待核验”，不夸大成已做专门缓存基准测试。

### 8.3 理解 `model.eval()` 与 `torch.inference_mode()`

- `model.eval()`：切换模型为 Evaluation Mode，影响 Dropout、BatchNorm 等层的行为；**不会关闭 Autograd**，也不会自行生成答案。
- `torch.inference_mode()`：禁用梯度记录并优化推理相关开销；**不会自动切换模型的 train/eval 状态**。
- 两者可共同使用。模型只需在 `load_llm()` 初始化时设为 eval（如果后续不调用 `train()`），不必每次 `generate_answer()` 再重复调用。
- `lru_cache` 的缓存仅在**同一 Python 进程**、相同函数参数下复用，程序退出即消失；不能跨电脑、跨独立 Python 进程共享权重。

### 8.4 对下一阶段的重要意义

现在 Query Rewriter 已复用 `generate_answer()`，在一次五题 Evaluation 中每题通常触发一次 Rewrite。一次完整 RAG 问答还可能额外调用 Qwen 生成最终答案；无缓存则每次重新加载代价很高。若未来需要真正从 Mac 实时访问 Windows，应另行设计服务/API；目前还**没有**这条远程链路。

---

## 9. 下一开发阶段与完成标准（2026-10-15；一次只推进一个操作）

### 9.1 **当前下一步：Query Decomposition（计划，尚未编码）**

**为何优先于继续 Rewriting 微调**：六组实验确认 Original/Rewritten/Multi-Query 的 BGE Top-5 在五题上完全相同，且 q5 比较 VGG 与 DCNN 时仅命中 1/5 相关 Chunks。普通 Rewriting 只是改句子表述，不会保证分别收集两篇论文的证据。先独立设计面向**多个实体、多个方面、对比请求**的子查询拆分。

```text
用户问题：How do VGG and DCNN differ in their use of convolutional filter sizes?
    ↓ Query Decomposition
    ├─ What filter sizes does VGG use and why?
    └─ What filter sizes does DCNN use and why?
         ↓
    分别执行 Dense/BM25 → 合并/去重/排序 → 检查双论文证据覆盖 → Qwen 综合比较
```

**开发边界**：仍然使用现有 Semantic 385 Index、MiniLM、BM25、RRF 与 BGE，不借拆分机会同时换 Embedding / Chunking；先做 `src/query_decomposer.py` 的输入输出设计与有限测试，再接到主线，最后增加 Query Decomposition 的独立 Evaluation。子问题可能需要 Metadata 路由，但**不能把 `source="VGG.pdf"` 永久硬编码**；q5 可以作测试用例，不可据此声称整套方法普遍有效。

**紧接着唯一的操作**：当用户说继续项目，先与用户一起设计/实现 `src/query_decomposer.py` 的最小接口和提示词（按用户“自己手打、一步一步”习惯）。不再重复要求用户修改已完成的 Query Rewriting/RRF/Evaluation。

### 9.2 HyDE（尚未实现）

让 Qwen 对问题生成**假设性文档/答案**，只把它作为 Dense 查询向量的检索输入，而不把这段假设文本当作真实证据引用。与 Original / Rewritten / Decomposed 对照，在固定数据与候选预算下考察可能的收益及额外时延；不默认每道题都开启。

### 9.3 扩大 Retrieval + End-to-End Evaluation（尚未完成）

- 把 5 道 Gold Evidence 问题扩充为更具代表性的集合：单篇事实、原因/机制、跨篇比较、长句、歧义、复合子问题、表格/公式及无法回答的问句；需要继续人工审计 Gold，避免只用一个 VGG 案例优化。
- 持续计算 P@5/R@5/MAP@5/MRR@5；增加双方论文覆盖度/证据覆盖、No-RAG/Basic/Hybrid 对照、响应时延与可能的 token/cost（本地模型无 API 计费，但有算力消耗）。
- q6（2026-10-10 NVIDIA 股价）仍按 Out-of-Scope 题处理：检索指标跳过，但在 Answer-Level 评估中测试知识库不足时能否明确拒答；**不能拿它冒充当前检索平均值的一题**。

### 9.4 Context Management + Citation/Generation Evaluation（原型探索过，尚未通用）

- 已诊断 VGG p2/p3 的跨页证据碎片，并通过手工 `source` 过滤、章节扩展和 Gold-Only Context 试验观察到 Context 的影响；这些不是当前主线已上线功能（详见第 13 节）。
- 后续实现可控、去重、来源/章节敏感且带 token 预算的 Context Expansion 或 Parent-Child Retrieval；不能无约束引入整章或使用 `chunk_id+1` 来盲目扩展。
- 研究 Faithfulness、Citation Support/Precision、答案覆盖率、公式保真度、拒答和错误归因；Qwen 可能把引用号堆到末尾、错读感受野或把另一篇论文解释套到 VGG 上。Prompt 约束单独不能保证正确。

### 9.5 PDF Parser V2（**明确延后**，不要自动重启）

`src/pdf_loader_v2.py` 的 Block Extraction + `table_candidate` 标记已完成初步测试（第 14 节）；`find_tables()` 在 VGG p3 返回 0。还没有布局分类全覆盖、跨页段落合并、公式解析修复或 V2 Index。**用户 10-15 明确决定：现有问答可用、当前不把 Parser V2 作为主线阻塞项**；只有未来扩充的 Evaluation 显示解析缺失是广泛瓶颈时才提前重启。保留旧版 Index 作为对照，禁止直接覆盖 Semantic 385 文件。

### 9.6 Single-Agent / Agentic RAG（未来目标，尚未实现）

根据查询复杂度、证据质量与检索结果，决定是否 Query Decomposition、是否 HyDE、是否二次检索、何时停止及何时拒答；控制最大步骤/时延。之后再视需求引入 LangGraph 做编排（并非强制），最后加论文证据展示 UI（Streamlit 可选）、README、可复现命令与简历实验报告。**不会单独做 Fine-tuning 项目。**

---

## 10. 当前已知项目文件结构（根据用户上传与实测整合，非实时 `ls`）

```text
Advanced-LLM-RAG/
├── .git/ / .gitignore / .venv/     # 各电脑独立，本地虚拟环境不提交
├── data/
│   ├── raw/
│   │   ├── Attention is all you need.pdf      # 11 pages
│   │   ├── DCNN.pdf                           # 7 pages
│   │   └── VGG.pdf                            # 14 pages
│   └── processed/
│       ├── chunks.json / faiss.index                         # Fixed 340
│       ├── chunks_recursive.json / faiss_recursive.index     # Recursive 340
│       └── chunks_semantic.json / faiss_semantic.index       # Semantic 385
├── src/
│   ├── pdf_loader.py                 # Parser V1，正在使用
│   ├── pdf_loader_v2.py              # Block/Classify 初步实验，不在 main.py 中启用
│   ├── chunking.py                   # Fixed（已审查源码）
│   ├── chunking_semantic.py          # Semantic（已审查源码）
│   ├── [Recursive Chunking 模块]      # 已实现/运行；最新文件名未在本轮核对
│   ├── embedding.py
│   ├── vector_store.py
│   ├── chunk_storage.py
│   ├── retriever.py
│   ├── bm25_retriever.py
│   ├── hybrid_retriever.py           # RRF 支持 extra_results
│   ├── reranker.py
│   └── query_rewriter.py             # 调用 Windows 本地 Qwen
├── evaluation/
│   ├── questions.json                # q1-q5 Gold, q6 Out-of-Scope
│   ├── check_evidence.py
│   ├── metrics.py
│   ├── run_evaluation.py             # 六组公平对照，2026-10-15 已跑通
│   ├── pool_chunks.json              # 旧 Candidate Pool 审计档案
│   ├── pool_chunks_recursive.json
│   ├── pool_chunks_semantic.json
│   └── results/                     # 旧 baseline_v1.md；新增实验报告建议待落实
├── main.py                           # 已恢复通用 Original/Multi-Query 开关
├── llm.py                            # Qwen 本地加载/生成，在 Windows 实际运行
└── PROGRESS.md                       # 本文件
```

**2026-10-15 `main.py` 清理关键点**：之前临时 `vgg_candidates`、`target_ids=[246,250,251]`、Source Filter、章节扩展、重复 Context 覆盖全部去除；现在固定读取 Semantic Index，缺少索引则报错，不再错误地用 Fixed Chunking 自动覆盖 Semantic 路径。`USE_MULTI_QUERY=False` 为默认；`RETRIEVAL_TOP_K=20`、`RRF_TOP_K=20`、`RERANK_TOP_K=5`、`RRF_K=60`；Reranker 为 `BAAI/bge-reranker-base` CPU。Windows 用 Transformer 位置编码题成功验证 Retrieved Top-5/生成回答；证据是 Transformer p5 `3.5 Positional Encoding`，在 BGE 排名 **5**，Qwen 回答正确并引用 `[5]`（仍未满足逐句内联引用）。

**2026-10-15 `evaluation/run_evaluation.py` 清理关键点**：已有函数 `retrieve_two_ways`、`fuse_and_rerank`、`record_results`、Gold Quote→Chunk ID 映射、四指标汇总；`ENABLE_REWRITING=True` 时比较六方法；`False` 时四方法。Baseline 强制 Original Query，Qwen 每题重写一次；用户 Windows 运行完整六组成功（q6 跳过）。

**状态谨慎表述**：现有文件目录并非从用户真实机器实时采集；本轮 `src/pdf_loader_v2.py`、`src/query_rewriter.py`、RRF 接口、`main.py`、Evaluation 的逻辑来自用户贴出的代码或运行结果，但实际 Git status / 远程同步仍待用户确认。两台电脑 `data/` 内容不会因 Git 自动同步。

---

## 11. 协作守则、记忆防丢与新对话完整交接 Prompt（已更新）

### 11.1 必须遵守的工作习惯

1. **清楚详细的尽你最大努力的回想起RAG项目的所有对话与内容**。先读本进度文件与用户最新源码/运行日志，必要时检索可访问的项目对话；不要假称已经逐字扫描全部历史消息。
2. **最新结果优先**：10-15 六组 BGE/Query Optimization 已完成；不要复述旧状态“Query Rewriting 未开始”“RRF 只能两路”“Parser V2 尚未创建”“现在只有 330 Chunks”。
3. **严格一次一个操作**：先讲目的、代码与预期输出，等用户回报再做下一步。用户倾向自己手打与理解；仅当多次零散修改导致混乱或用户直接要整理时，才给完整文件。
4. **Mac / Windows 分工**：Mac 开发，Windows RTX 5060 Qwen；无跨机实时 LLM API。含 `rewrite_query` 或 `generate_answer` 的运行通常在具备 Qwen 缓存的 Windows 上执行；本地模型未因 Git 同步而出现在 Mac。
5. **不加入 Fine-tuning/LoRA/QLoRA**，不把独立 PyTorch Transformer 项目混入 RAG；不把 LangChain/Agent/GLiNER/HyDE/Parser V2 等计划技术冒充已实现。
6. **保留可对照实验**：不要更改现有 `faiss_semantic.index` + `chunks_semantic.json` 或任意其他成对索引而不标版本；不同 Reranker/Chunking 结果不能混在一起归因。q6 未包含在五题检索指标中。
7. **不要只优化单题 VGG**：所有 VGG Source Filter、三个 Gold Chunk ID、Top-40 扩展是诊断，已经从干净主线移除；真正优化需关注 q5 等多类型问题，并扩大 Evaluation。
8. 不擅自 Git commit/push、不下载不必要的模型，不对未核查的目录/参数/评估结果做保证。发生信息冲突请直接指出并索取最小必要材料。
9. 每完成重要阶段更新**日期、已实现/已验证/尚未实现、参数、真实指标、失败案例、下一件事**；首页必须与正文同步，不要在文件末尾无限累积互相冲突的“当前状态”。

### 11.2 新对话开场指令（可直接复制）

> 请先完整阅读本项目根目录的 `PROGRESS.md`（尤其第 0、7、9、11、13、14 节），并结合我最新贴出的源码/终端日志修正过时信息。**清楚详细的尽你最大努力的回想起RAG项目的所有对话与内容**，但不要假称逐字扫描无法访问的历史。项目目标是可复现、可评估的科研论文分析 **Advanced-LLM-RAG / 单 Agentic RAG**，后期包含跨论文比较、复杂问题拆解、条件性检索、证据/引用、拒答、UI；**不包含 Fine-tuning/LoRA/QLoRA**。MacBook Air + PyCharm 主开发，Windows RTX 5060 本地 `Qwen/Qwen3.5-2B`，Git 同步代码但没有实时跨机 LLM API。当前三篇论文，Fixed/Recursive/Semantic 340/340/385 Chunks；已有 PDF Parser V1、Semantic Index、Dense/BM25/RRF、CrossEncoder MiniLM/BGE、Qwen 生成、Gold Evidence、检索评价。**Query Rewriting 和可选四路 Multi-Query 已实现，并在 2026-10-15 用 Semantic+BGE 公平比较六组指标；Original/Rewritten/Multi-Query+BGE 在五题的最终 Top-5 Chunk ID 和顺序完全一致（P@5 .4000、R@5 .6900、MAP@5 .4119、MRR@5 .5800）**。旧 Eval 基线污染已修复，通用 `main.py` 已恢复并在 Transformer 位置编码题跑通。VGG 跨页/表格/公式解析问题及 `pdf_loader_v2.py` 已诊断，但当前**决定暂缓 PDF Parser V2**，不要继续追单题故障。**下一步是 Query Decomposition**（尤其 q5 VGG vs DCNN），之后 HyDE、扩大 Evaluation、Generation/Citation、Single-Agent、UI。**务必一次只推进一个操作**，先让我理解再手打代码，除非我要求完整整理。

---

## 12. 重要开发时间线及过时信息清单

| 时间（2026） | 发生的事情 | 对今天的意义 |
| --- | --- | --- |
| **10-05** | 系统学习 RAG：BM25、Dense/Hybrid/RRF、Precision/Recall/MAP/MRR、KNN/ANN/HNSW、分块、Query Parsing/NER/GLiNER/HyDE、BiEncoder/CrossEncoder/ColBERT；确定以科研论文为场景做手写综合项目，先不用 LangChain/Matt Skills。 | 理论讨论不代表已在仓库实现 GLiNER、ColBERT、HNSW 等。 |
| **10-09** | Mac PyCharm/Python 3.11.9 `.venv` 搭项目、GitHub，同步 Windows；PyMuPDF→Fixed Chunks→MiniLM→FAISS→Dense Retrieval/Index Persistence；当时 330 Chunks。 | 早期进度文件的“下一步 Dense Retriever”已失效。 |
| **10-09～10-10** | Windows RTX 5060 安装 CUDA/PyTorch/Transformers/Qwen，解决 Processor 依赖；GPU 本地独立生成成功。 | 模型在 Windows，本地缓存不在 Mac。 |
| **10-10～10-11** | Windows 上检索 Top-5 + Context/Prompt + Qwen 输出完成 Basic RAG；随后 BM25/RRF/Reranker 演进与调试。 | 不要再把 Basic RAG 写成未打通。 |
| **10-12～10-13** | 完成检索评分、三种 Chunking 首轮对比；明确**取消当前 RAG 项目的 Fine-tuning**；从单纯组件组合转向可评估科研论文分析 / Agentic RAG 目标。 | 早期 LoRA 计划作废。 |
| **10-13～10-14** | Parser 增强：Title/Section 识别、跨页继承、DCNN 双栏；产出 86 Documents，最终三套 340/340/385 Chunks 和配套索引，核对数据一致性/Metadata。 | 旧 330/331/403 属于中间试验。 |
| **10-14** | 构建/上传三份 Pool、逐问审查 Gold；q1 补齐 7 Evidence、q4 补齐 5 Evidence 并验证；移除每次评估都重新保存 Pool 的临时代码。 | 现在不应重复要求造 Pool。 |
| **10-14** | 以修订后的 Gold 重新跑 Fixed/Recursive/Semantic × 4 Retriever **12 组完整 MiniLM-L6 Evaluation**；当时暂定 Fixed+Hybrid+MiniLM-L6 为阶段基线。 | **这是历史对照，不再是最新 Query Optimization 进度。** |
| **10-14～10-15** | 将 CrossEncoder 替换/对照为 BGE，Semantic+BGE 达 P@5 .4000、R@5 .6900；实现 Query Rewriting V1/V2，观察改写语义变化与错误迁移，比较 Original/Rewritten 检索。 | Rewriting 已实现、效果有得有失，不能再写成“尚未开始”。 |
| **10-15：多查询实验** | 扩展 RRF 为可选四路，Original+Rewritten Dense/BM25；手工 VGG 测试揭露 Chunk 246 RRF Rank22，Top20 截断；Top40 找回但 BGE 没放进最终 Top5。 | 多查询不保证保留 Original 证据，需与单路公平评估。 |
| **10-15：VGG 证据/Parser 诊断** | 临时 VGG Source Filter、章节扩展（5→14 Chunks）、Gold-Only `[246,250,251]`；Qwen 从跨论文错误变成较完整答案，仍有三层 3×3→5×5 错误和引用列表化；确认 VGG p2/p3 断句、表格插入、公式乱码。`find_tables()`=0，Blocks 能隔离 Table2；独立 `pdf_loader_v2.py` 能标识 Table1/2 候选。 | 临时代码不进入生产；**Parser V2 暂缓**，保留诊断记录。 |
| **10-15：主线恢复** | 整理 `main.py`，删除 VGG 硬编码、重复 Context、误用 Fixed 重建 Semantic 的路径；`USE_MULTI_QUERY=False` 默认。Transformer 位置编码问答成功并引用 `Attention is all you need.pdf` p5。 | 通用 Retrieval→BGE→Qwen 已恢复，不再重复 VGG 单题调参。 |
| **10-15：最新六组 Evaluation** | 重写 `evaluation/run_evaluation.py`，修复 Original Baseline 被改写污染/一次题目重写两次；六组同设置复跑成功，退出码0。Original/Rewritten/Multi-Query+BGE 逐题最终 Top5 IDs 完全一致；q5 仅1/5 Gold。 | Query Optimization 阶段 Rewriting/Multi-Query 已完成首轮；**下一步 Query Decomposition**。 |

**已经过时、不得复活的陈述**：

- “下一步实现 Dense/BM25/RRF/Reranker” → **已经实现**。
- “只有 330 个 Chunks” → **当前 Fixed/Recursive 340、Semantic 385**。
- “语料含 ResNet.pdf” → **不含；是 VGG.pdf**。
- “Gold Evidence 还未修复或 Pool 尚未创建” → **本轮已补充审查**。
- “Metadata-Aware 分块尚未重建向量索引/完成复评” → **三套索引已检查，最新版 12 组 Evaluation 已完成**。
- “RAG 项目要做 LoRA/QLoRA” → **明确取消**。
- “Mac 可以直接调用另一台电脑的 Qwen” → **尚未搭建远程 API**。
- “q6 股价题也计入五题检索平均数” → **错误，当前被跳过**。
- “`@lru_cache` 已经由最新完整源码与专用双次推理基准测试验证” → **仍未逐行复核最新 `llm.py`，但 10-15 五题 Windows 日志显示模型仅在第一题初始化，支持同进程复用**。
- “Query Rewriting 尚未开始、RRF 只能融合两路、Evaluation 仍然污染 Original Baseline” → **均已过时；已有重写/四路融合及修复后六组复评**。
- “当前 `main.py` 必须使用 VGG Source Filter / `[246,250,251]`” → **这些只是已移除的消融调试代码**。
- “10-15 Query Optimization 证明 Multi-Query 改善 BGE Top5” → **错误，三组 BGE 逐题 Top5 完全相同；五题有限，不能外推**。
- “PDF Parser V2 已完成/替代 V1” → **错误，仅完成 Block Extraction 和标题候选分类，并已决定延后深度开发**。

---

> **维护约定（2026-10-15）**：继续以第 0、7、9、11、13、14 节为最新交接核心；历史仍保留，但任何“当前/下一步”的描述都必须同步维护首页。不要把单题诊断写成通用成功结论，不要混淆 MiniLM-L6 与 BGE 的评估条件。

---

## 13. 2026-10-15 VGG 故障排查完整链条（已验证的失败案例；非正式功能）

### 13.1 为什么突然出现 Qwen 错误答案

早期 Qwen 能正常回答不少论文问题，并非模型后来突然降级。因为 Query Rewriting / Multi-Query / RRF 候选池 / Source Filter / Context 曾多次变动，**输入给同一个 Qwen 的证据集合改变了**。在没有正确 VGG 证据、Top-5 反而混入 Transformer 与 DCNN 时，Qwen 将 Transformer 的卷积路径长度分析错误归因于 VGG，甚至声称“小卷积核让 VGG 一层连接所有位置”，与论文相反。这个错误直接受到跨论文候选污染的影响，但即使给对证据，Qwen 2B 仍可能误读事实。

### 13.2 原始问题与融合候选诊断

手工问题：`What makes the small conv kernels in VGG useful?`；Qwen V2 改写结果：`What are the functional advantages of small convolutional kernels in VGG architectures?`。在 Semantic+BGE 四路 RRF 实验中，真正解释有效感受野的 **`VGG.pdf` p2 Chunk 246**：

- Original BM25：**Rank 5**；Original Dense / Rewritten Dense / Rewritten BM25：均**不在各自 Top-20**。
- 四路 RRF 全部排名：**Rank 22**，因此 RRF Top-20 **截掉**这条证据；改成 RRF Top-40 后候选中出现 **Rank 22**。
- 改成 Top-40 后，**BGE 的最终 Top-5 仍没有 Chunk 246**，优先了 Transformer p7/p2、DCNN p4 及 VGG 不直接回答问题的性能描述。
- 临时加 `source == "VGG.pdf"`：RRF Top-40 里 VGG 候选 **22** 条，BGE Top-5 将 Chunk 246 排到 **Rank 3**；Qwen 因此能够引用 [3]，但仅凭这段分散的文字回答不完整。

**解释**：RRF 聚合多路排名会优待多路高频 Chunk，即使用户最需要的某条仅靠 BM25 找到也可能被挤出候选；Source Filter 在明确单论文提问上能减少跨篇干扰，但**不适合直接无条件写死到通用系统**（例如 q5 同时需要 VGG 与 DCNN）。Top-40 与 Source Filter 都只是单题 Debug 参数，不是最新六组公平评估设置。

### 13.3 Context Expansion 和 Gold-Only 消融

从 `VGG.pdf` `2.3 DISCUSSION` 人工确认三个核心 Gold Chunks：

| Chunk ID | Page | 核心证据 |
| --- | ---: | --- |
| **246** | 2 | 两层 3×3 卷积有效感受野 5×5，断在单词 `three` |
| **250** | 3 | `such layers have a 7×7 ...`；三层小核替代大核、更多 ReLU / 非线性 |
| **251** | 3 | 参数数目：三层 3×3 的 `27C²`，一层 7×7 的 `49C²`；公式 PDF 提取有异常符号 |

- 手工 **Section-Aware Context Expansion**：BGE Top5 与同源同章节邻近页面的 Chunks 合并，曾扩展到 **14 条**：`[230,380,246,310,305,245,247,248,249,250,251,252,253,254]`。Qwen 答案更完整，包含非线性与参数量；同时引入表格、1×1 卷积等噪声，引用号几乎罗列整段 Context。
- 第一次 Gold-Only 调试因 `context_results` 被重复覆盖，最终出现 **12 条且 250/251 重复**；不是有效的 Gold-Only 消融结果。检查完整 `main.py` 后清理重复赋值、章节追加。
- 真正 Gold-Only 的 **`Final Context Chunk IDs: [246,250,251]`** 已实测。Qwen 在此情况下正确解释 27C² vs 49C²、更多非线性，却仍误将**三层** 3×3 对应的感受野说成 **5×5**（正确为 **7×7**）；仍将 `[1],[2],[3]` 集中写在答案末尾，违反逐论断引用的 Prompt。
- **实测结论**：相关证据的可用性和覆盖度确实影响答案；然而 Parser 文本断裂、2B 模型的事实理解、Citation 遵循度是相互独立又互相关联的风险。不要声称“只要修好 Parser 就能治愈全部 LLM 错误”。

### 13.4 对研发流程的启示

1. 诊断顺序要区分：Retrieval 候选 → RRF 截断 → Reranker → Context 选择/拼接 → Qwen Answer/Citation；不能只凭最终答案差便反复改写 Prompt。
2. 不要针对一题硬编码三个 Gold ID、指定 VGG Source 或无限扩大 Context；诊断代码在 10-15 整理 `main.py` 时已清除。
3. 未来需要自动的 Query Entity/Source Routing、可控 Context Expansion 和 Citation Verification，但目前**仅为计划，不属于正式已交付功能**。

---

## 14. 2026-10-15 PDF / Chunking 排查与 Parser V2 暂缓决定

### 14.1 最初为何排查 PDF 文本

VGG p2 的 `Chunk 246` 在 `... 5 × 5; three` 截断，而 p3 的 `Chunk 250` 在表格数据后才以 `such layers have a 7 × 7 ...` 继续。先检查 Fixed `src/chunking.py`，发现按字符切片，每 500 字符（100 overlap）；随后检查实际用于当前 Index 的 **`src/chunking_semantic.py`** 和构建脚本：`split_documents_semantic(documents, model, max_chunk_size=500, percentile=10)`；**Semantic 并不是 Fixed**，而是相邻句子余弦相似度 + 分位数语义边界 + 最大字符限制。

Sentence Splitting 先将每个 Document 的空白压成空格，再按终止标点切句；按页/章节独立 `document` 循环。单句超过 500 字符则按字符强切，忽略短句/短 Chunk，有潜在无损性问题。但当前 VGG p2/p3 的断句首先已经**存在于 Loader 的两个跨页 Document**，不是 Semantic Threshold 才造成的。

### 14.2 源头输出、坐标及表格检测

`src/pdf_loader.py` 使用 `pymupdf`, Block→Line→Span 解析、按页面与检测章节生成 Documents（`source/page/title/section/text`），并只对 `DCNN.pdf` 特殊处理双栏。实际检查 Loader 原文：

- **VGG p2** 结尾：`... has an effective receptive field of 5 × 5; three
2`。末尾 `2` 是页码，构建 Semantic Chunks 时可识别并移除。
- **VGG p3** 开头：`Published as a conference paper at ICLR 2015`，随后是较长的 **Table 1** 与 **Table 2**，最后才回到正文 `such layers have a 7 × 7 effective receptive field`，然后 `First...` / `Second...`。
- p3 页面大小 `612 × 792`；Block/BBox 调试：Table1 标题行 y≈**88**；Table2 标题行 y≈**455**，Text Block y≈**455–489**；`such layers` 开头 y≈**497.6**，后续 `Second, we decrease` y≈**530.5**。**这反映论文版面的真实顺序，不能简单指责 PyMuPDF 的排序算法“错排”。**
- `page.find_tables()` 在 VGG p3 检测结果：`Total Tables: 0`，因为这种无明显网格的学术表格不保证被自动识别；然而 `page.get_text("blocks")` 能把 Table2 与其后正文识别为不同 Block（只是公式还可能被拆成多个文本块）。
- 公式内容的 PyMuPDF 输出有 ` `、`32C2` 等错误，而正确数学含义来自原论文是 `3 × 3² C² = 27 C²` 和 `7² C² = 49 C²`。**不能未经人工/其他方式核实就对模型宣称公式提取已经修复。**

### 14.3 `src/pdf_loader_v2.py` 已做的范围

已创建 `extract_text_blocks(page)`：通过 `page.get_text("blocks")` 取得 `block_id`、`page`、`bbox`、`text`，丢弃非文本块、空块；增加 `block_type` 初步分类：`text`、正则 `^Table\s+\d+\s*:` → `table_candidate`、`Figure/Fig.` → `figure_candidate`。最初误写 `get_text("blockss")`，随后修正。用户在 VGG p3 真正跑出两个候选：

- **Table1** `table_candidate`，BBox `(107.999..., 88.149..., 504.209..., 134.320...)`；
- **Table2** `table_candidate`，BBox `(188.760..., 455.229..., 421.003..., 488.999...)`。

**已验证的是「表格标题所属 Text Block 的初筛」**，不是自动找到整张 Table1 的范围，更没有跨页合并、公式修复、全论文解析 V2、对三篇 PDF 重建 Index 或比较新的 Retrieval 指标。

### 14.4 用户明确做出的优先级决策

用户询问：当前解析问题是否会严重影响问答，如果不阻碍主线可后续修饰。分析认为：**某些跨页知识、表格、数学公式问题可能严重受影响；但现有通用 Transformer 问答已经可运行，没有证据显示它是当前全系统的主要瓶颈**。随后决定先停 Parser V2、保留源码与诊断证据、回到 Query Optimization / Agentic 主线；若未来更多样的 Evaluation 显示解析广泛失败，则再按测试优先级开展 V2 并保存独立索引。**绝不能误写“Parser V2 已完成 / 当前需要立即继续扩展 Table 区域”。**

---

## 15. 下次更新检查表与清楚的阶段定义

- [x] Basic/Hybrid RAG + Windows Qwen 端到端问答已经运行过。
- [x] Metadata Parser V1，三套 340/340/385 配对索引以及 10-14 的 12 组 MiniLM-L6 对照。
- [x] BGE Reranker 跨 Chunking 对照与 10-15 Semantic+BGE 六组 Query Optimization 评估。
- [x] `rewrite_query`、RRF `extra_results`、主线可开关 Multi-Query、原始 Baseline 修复、Evaluation 重构。
- [x] 调查了 VGG 候选截断、Source Filtering、章节上下文扩展、Gold-Only、跨页、表格及公式问题；VGG 专用调试已从通用 `main.py` 清理。
- [x] Block-Level Parser V2 **初步实验**（不是完成全部 PDF Parsing）。
- [ ] Query Decomposition 正式模块、独立评估与跨论文证据覆盖。
- [ ] HyDE 独立实现、同条件消融。
- [ ] 扩大问答问题集，增加 evidence coverage、Generation/Citation/Abstention 与性能评估。
- [ ] 通用 Context Expansion / Evidence Verification，按需求再优化 PDF Parser V2。
- [ ] 可控 Single-Agent（必要时 LangGraph）+ UI + README + 简历展示材料。

**新对话第一件事**：确认已经看过最新六组日志与本文件 **§0、§7、§9、§13、§14**。除非用户主动要求报告/整理，其后先围绕 **Query Decomposition 的最小接口**展开，而不是回退到 Query Rewriting 初次设计或 Parser V2 表格试验。
