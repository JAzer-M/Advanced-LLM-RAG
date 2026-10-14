# Advanced-LLM-RAG — 项目总进度、实验记录与跨对话交接文档

> **最后更新：2026-10-14**  
> **当前阶段：Retrieval Baseline 已完成本轮复评；即将进入 Query Rewriting / Query Optimization。**  
> **文件用途：**这不是泛泛的 RAG 学习笔记，而是 `Advanced-LLM-RAG` 的长期项目事实、决策、代码模块、实验数据和下一步交接记录。新对话务必先读第 0、1、7、9、11 节，必要时再读全文。
>
> **用户明确要求的提醒：清楚详细的尽你最大努力的回想起RAG项目的所有对话与内容**
>
> **准确性说明：**根据本项目可访问的历史对话、此前 `PROGRESS.md`、用户逐次贴出的代码/终端结果及上传的 `questions.json` 和三份 Candidate Pool 整理；**不等于已逐字读取全部历史消息，也没有实时访问或检查用户 Mac/Windows 本地仓库。** 一旦文档与用户最新源码或真实运行结果冲突，以最新源码与用户确认的结果为准。每次更新必须注明“已实现 / 已验证 / 已计划 / 尚待确认”，不得用猜测填补记忆。

---

## 0. 新对话一分钟交接——最重要的事实

1. **最终目标**：做一个适合 AI / LLM 实习简历展示、以**科研论文分析**为场景的、可运行可复现可评估的 **Advanced-LLM-RAG / Single-Agent（Agentic RAG）** 系统。它最终不只回答简单 PDF 问题，还应支持精确证据、页码/章节引用、多论文比较、复杂查询拆解、多步/必要时迭代检索、可靠拒答和可展示 UI。Agentic 是后续目标，**当前并没有实现 Agent**。
2. **硬性边界**：**本 RAG 项目不包含 Fine-tuning / LoRA / QLoRA**；早期将其列为可选扩展的旧计划已作废。用户另有一个独立的 PyTorch Transformer 架构研究项目，**不得混入 RAG**。暂不使用 LangChain / Matt Skills 代替手写基础组件；LangGraph 仅为后期可能采用的 Agent 编排方案，尚未确定/实现。
3. **设备分工**：**MacBook Air + PyCharm** 为主开发、PDF 解析、Embedding、FAISS/BM25 检索与 Evaluation 端；**Windows 笔记本 NVIDIA RTX 5060（约 8GB VRAM）** 是本地 **`Qwen/Qwen3.5-2B`** 的推理端。两机通过 Git/GitHub 同步代码，**并无已实现的 Mac→Windows 在线 LLM API**。`llm.py` 是运行在拥有本地模型缓存的电脑上的本地推理函数。不要让用户在 Mac 上重新下载/启动大模型，也不要将 Git 同步误认为共享 GPU、模型、虚拟环境、PDF 或索引。
4. **已完成**：PDF Custom Parser V1（标题、章节、DCNN 双栏阅读顺序、跨页章节继承）；Fixed/Recursive/Semantic 三种分块；MiniLM 384d Embedding；FAISS `IndexFlatIP` 持久化；Dense/BM25/RRF Hybrid/Cross-Encoder Reranking；Windows Qwen 独立生成、Basic RAG 与 Hybrid RAG 端到端试验；Gold Evidence 匹配/检索评估；三份 Candidate Pool 的构建及人工审查。
5. **最新真实数据**：目前使用三篇 PDF，**11+7+14=32 页**，Custom Parser V1 输出 **86 个按章节组织的 Documents**；Metadata-Aware Chunking/Index：**Fixed 340 / Recursive 340 / Semantic 385**（对应索引向量数分别为 340/340/385，384 维）。**不是**旧文件记载的 330/331/403。
6. **评估已收尾**：最新 `questions.json` 有 q1～q5 五个可回答问题、q6 一个 Out-of-Scope；最新人工补充与匹配验证：q1 **7 条**、q4 **5 条** Gold Evidence，三个分块方案匹配失败数均为 0；12 组 `Precision@5 / Recall@5 / MAP@5 / MRR@5` 已重新运行，见第 7 节。它是 **5 道题、部分相关性标注、Chunk-Level 的工程基线**，不是强统计证明。
7. **当前工程基线**：暂定 **Fixed + Hybrid (RRF) + Cross-Encoder Reranker**，其 **P@5 0.3600 / R@5 0.7167 / MAP@5 0.3981 / MRR@5 0.6500**；只是为了继续搭建下一阶段而选定的默认实验方案，并非宣称在任何数据上都最优。
8. **当前紧接的工作**：先完成/确认 Windows `llm.py` 的 **`@lru_cache(maxsize=1)` 单进程模型复用**（用户刚贴过改造版本，但其中 `generate_answer` 还存在重复模型加载；助理已指出删除重复部分，**修正后的完整源码尚未复查**）；随后**开始 `src/query_rewriter.py` 的 Query Rewriting**，继续 Query Decomposition（q5 为代表用例）、HyDE 独立消融实验。不要再无故重做 Parsing、Chunking、Pool 或 Baseline。
9. **合作节奏**：**一次只布置一个明确操作**；用户希望自己手打代码、理解每一行，先讲清原理和局部改动，除非结构已混乱才给整文件整理版；不要自动执行 Git commit/push。默认 PyTorch。

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
  ├─ src/chunking.py：Fixed / Recursive / Semantic（三种实验配置）
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

**实现状态必须分清**：基础 Prompt→LLM 和 Hybrid RAG 曾在 Windows 测试成功；检索 Reranker 与 Evaluation 已能运行；但**不能据此声称“以上所有模块在当前最新版本 main.py 中已经以完整生产流水线同时验证”**，也不能声称 Citation Validation、Agent 路由已完成。

### 1.4 后续计划中的智能查询主线（尚未完成）

```text
User Question
  → Query Analysis / Routing（后期）
      ├─ 简单问题：原始查询或 Query Rewriting
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
| Windows | RTX 5060 Laptop GPU，约 8 GB VRAM，PyCharm | Qwen 推理、较重 GPU 任务；独立 `.venv` |
| Windows Python | 历史使用 3.11.9 | 与 Mac 独立安装、独立环境 |
| Windows PyTorch/CUDA | 历史核实 `torch 2.13.0+cu130`、CUDA 可用 | 当前版本以 `torch.__version__` 实测为准 |
| Windows Transformers | 历史记录 `5.19.0` | Qwen3.5 `AutoProcessor` / `AutoModelForMultimodalLM` 接口可导入 |
| LLM | Hugging Face **`Qwen/Qwen3.5-2B`** | Windows 本地缓存、BF16、`device_map='auto'`、`local_files_only=True` |
| GitHub | `https://github.com/JAzer-M/Advanced-LLM-RAG.git` | 历史 push commit `4c6c168`；非当前 HEAD 保证 |
| Mac 历史路径 | `/Users/j/Desktop/Advanced-LLM-RAG` | 路径以用户电脑为准 |
| Windows 历史路径 | `C:\Users\J\Desktop\Advanced-LLM-RAG` | 路径以用户电脑为准 |

**Git/GitHub 注意**：

- Git 在本机保存被跟踪文件的版本；GitHub 提供远程托管与两机同步，clone / pull / push 只同步被追踪的内容。
- 项目 `.gitignore` 历史上排除了 `.venv/`、IDE/Python 缓存、模型权重/缓存、`data/raw/` 和 `data/processed/`；**原 PDF、索引、Chunk JSON 可能必须在 Windows 单独准备或生成**。新增的 `evaluation/pool_*.json` 和 `questions.json` 是否被 Git 跟踪，应以实际 `git status` 为准。
- HF 模型缓存不在 GitHub 中；**Windows 本地模型 ≠ Mac 模型、也 ≠ 已有远程推理服务**。
- 两台电脑不共享进程或 GPU；`@lru_cache` 也不能让 Mac 跨网络复用 Windows 模型。当前若运行含 `generate_answer` 的完整脚本，通常应在已准备模型与所需数据的 Windows 上执行。
- 不要擅自 commit/push；优先让用户了解当前更改与原因。

**历史 Windows LLM 相关排错**：曾遇 `Qwen3VLVideoProcessor requires the Torchvision library`，安装 `torchvision` 后解决；缺失 `causal_conv1d` / `flash-linear-attention` 时会有优化内核 fallback 警告，但不必然妨碍成功生成。曾观察 `Loading weights ... 617/617`、`cuda:0`、BF16，独立生成成功；`max_new_tokens=128` 曾造成答案可能截断。

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

三种 Chunking 在 `src/chunking.py` 中实现/调用：

- **Fixed**：按固定字符长度切割，历史参数 `chunk_size=500`、`chunk_overlap=100`；单位为**字符**不是 tokenizer token。
- **Recursive**：尽量沿自然分隔符（段落/换行/句子等）拆分，再在需要时进一步递归切割，维护上限与一定重叠。
- **Semantic**：用语义嵌入与相邻语义距离/阈值决定分块边界；历史上尝试过不同 percentile（如 `20`、`10`），不可将旧测试输出混到当前索引数据。

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
- 后续如有必要，可补充 **Evidence-Level Coverage/Recall**（某个回答所需证据是否被覆盖），或文档级覆盖度、Generation/Citation 评估；无需阻塞 Query Rewriting 阶段。
- 修改 Evidence 后重新算出的数字**不是 Retriever 模型训练后提升**，仅仅是相关性判断基线变化；旧版数字不能当成同一数据集下的公平对照。

---

## 7. 最新 Retrieval Baseline：同一版 Gold Evidence 下的 12 组结果（2026-10-14）

**共同设置**：三篇论文、5 道可回答问题，`k=5`，检索候选 `candidate_k=20`；Dense 使用 MiniLM 384d/FAISS；Hybrid 通过 RRF(k=60)；Hybrid+Reranker 使用 `cross-encoder/ms-marco-MiniLM-L6-v2`。q6 没有计入这些平均数。以下数字来自用户这轮三次运行的终端输出。

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

**暂定默认：Fixed + Hybrid + Reranker**。理由是该配置在当前测试中 Recall 最高、Precision 并列最高，能作为下一阶段的可运行基线。保留 Recursive、Semantic 作为对照。为什么不声称最优：样本少、金标非穷尽、Chunk 粒度与标注数量不同；还未进行足够多的用户真实问题和端到端答案评估。

### 7.3 值得保留的真实失败案例

1. **q1 Gold 漏标**：Fixed Dense 的相关段落 `VGG.pdf` p3 Chunk 223 说明 3×3 对 7×7 的分解、正则化，最初未算 Relevant；后补 quote 并验证。它说明 Evaluation 本身会出错，不能看到低分就立刻改模型。
2. **q5 多文档覆盖不足**：问题需要 VGG 和 DCNN 两份证据。在 Fixed 与 Recursive 四种 Retriever 的候选池 Top-5 中，缺少直接说明 DCNN 卷积核配置的有效片段；而 Semantic 的 Reranker 曾返回 `DCNN.pdf` 的 Chunk 160（11×11 卷积）。这是 Query Decomposition 的理想真实测试问题。
3. **q4 方法语义与邻近主题混淆**：Dropout 虽然也减轻 Overfitting，却不是问题要求的数据增强方法。对检索和 Gold 判断都要严格围绕问题。
4. **Reranking 效果不稳定**：某些题会把主题相近但不能回答问题的片段排到前面。优先保留并分析这一局限，不要为了让指标好看删除不利案例。

### 7.4 历史基线的版本区别

早期 330 Chunks 的旧 Evaluation、首次三种 Chunking 对比、旧 Parser 的 330/331/403 分块结果，以及本轮补 Gold 之前的指标，全部属于**不同代码/Parser/标注版本的历史记录**。可用来说明开发过程，**不得与本节 12 组指标在同一表里作为公平消融实验**。此前 `PROGRESS.md` 关于“Metadata Index 尚待重建/尚未重新评估”的状态已过时。

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

`generate_answer(prompt)` 基于 `processor.apply_chat_template(...)` 构造 `role="user"` 的文本消息，转为 PyTorch Tensor 并移动到 `model.device`，使用 `torch.inference_mode()` 包裹 `model.generate(**inputs, max_new_tokens=128, do_sample=False)`，截掉输入 Token 后用 `processor.decode(..., skip_special_tokens=True)` 返回答案。

### 8.2 最近确认的 Bug 与正确思路

用户第一次改造缓存时写了 `processor, model = load_llm()`，**但在 `generate_answer()` 后面仍重复调用了 `from_pretrained()`，还引用了只在 `load_llm()` 局部作用域内定义的 `model_name`**，这既会重复加载，也会 `NameError`。已指导改为：

```python
def generate_answer(prompt):
    processor, model = load_llm()  # 本进程首次加载，以后复用
    # 下方直接进入 message / inputs / generate / decode；不要再 from_pretrained
```

**状态谨慎表述**：用户表示理解并继续往下走；**没有在本轮收到一份修正后的完整 `llm.py`，也没有看到缓存命中或 Windows 两次推理的运行日志**。所以标记为“已讲解修改方案，待最终源码/运行确认”，不可宣称当前正在运行的版本必然已修好。

### 8.3 理解 `model.eval()` 与 `torch.inference_mode()`

- `model.eval()`：切换模型为 Evaluation Mode，影响 Dropout、BatchNorm 等层的行为；**不会关闭 Autograd**，也不会自行生成答案。
- `torch.inference_mode()`：禁用梯度记录并优化推理相关开销；**不会自动切换模型的 train/eval 状态**。
- 两者可共同使用。模型只需在 `load_llm()` 初始化时设为 eval（如果后续不调用 `train()`），不必每次 `generate_answer()` 再重复调用。
- `lru_cache` 的缓存仅在**同一 Python 进程**、相同函数参数下复用，程序退出即消失；不能跨电脑、跨独立 Python 进程共享权重。

### 8.4 对下一阶段的重要意义

今后一个问题可能会触发 **LLM Query Rewriting + LLM Answer Generation** 两次或更多生成请求；没有复用时每次都重新加载 Qwen 会明显浪费时间/显存。Query Rewriter 应复用 `generate_answer()`，而不是自己再实例化一个 Qwen。若未来需要真正从 Mac 实时访问 Windows，应另行设计服务/API；目前还**没有**这条远程链路。

---

## 9. 接下来的开发顺序及完成标准（下一步只执行一件事）

### 9.1 下一步：Query Rewriting（**未开始编码**）

目标是让 LLM 对用户问题做**检索友好的重写**，保留实体、技术术语和原有语义，不要凭空增加论文事实。计划文件：`src/query_rewriter.py`（名称已讨论，尚不能当已创建）。

预计流程：

```text
Original Query
  → 构造指令式 Rewrite Prompt
  → 复用 Windows `generate_answer(prompt)`
  → 清理输出并检查是否过度改写/空字符串
  → Rewritten Query（必要时回退原 Query）
  → Dense/BM25/RRF/Reranker
```

**实验原则**：先保持 Baseline 的 3 篇 PDF、索引、Top-K、Gold Evidence、Retriever/Reranker 不变，仅替换/补充 Query Rewriting，比较同一 5 题的数据，不能同时更换 Chunking/Embedding/参数后把所有差异归因于 Rewriting。保留原始 Query 作为对照，尤其关注 q1/q2/q3 等术语明确的问题是否会“越改越差”。

**紧接着只推进的一个明确操作**：先**确认 `generate_answer` 已删除重复模型加载**（若已经修改则不必再重复；只核查开头），然后开始 `src/query_rewriter.py` 的输入、输出和 Prompt 设计。用户希望先理解，再自己写，避免一次布置多个文件修改。Mac 可以编写纯 Prompt/接口代码；真正调用 Qwen 的测试应在已部署 Qwen 的 Windows 进行。

### 9.2 下一阶段：Query Decomposition（未开始）

- 明确区别于只改写句子的 Rewriting：将一个复合问题拆成多个有独立检索目标的子问题。
- 重点案例 q5：`What convolutional filter sizes does VGG use?` 与 `What convolutional filter sizes does DCNN use?` 分别检索，再合并两篇证据回答。
- 要评估最终结果是否同时覆盖两篇论文，而不仅有若干看似相关的 VGG Chunks。

### 9.3 HyDE（未开始）

- 让 LLM 先生成一个假设性回答/文档，将其嵌入作为 Dense 检索的辅助输入；假设文本只是**检索工具**，不是可引用的真实文献。
- 先做独立实验：原 Query vs Rewriting vs HyDE，在固定检索条件下比较；避免所有改进一股脑开启无法归因。

### 9.4 Context Management / Citation / Generation Evaluation（待做）

- Reranker Top-5 的去重、相邻/父段扩展、上下文顺序、token 长度预算、来源/页码/章节格式化；避免固定字符切块截断关键句。
- Evidence-grounded Prompt，资料不足时安全拒答；关注答案正确性、覆盖度、Faithfulness、Citation Precision/Support、延迟；将 `max_new_tokens=128` 的潜在截断纳入观察。
- **q6** 测试系统面对语料外、需要时效信息的问题能否说明知识库没有依据，不许将它当作普通五题检索命中率的一部分。

### 9.5 Single-Agent / Agentic RAG 与展示（待做）

- 先把“查询分析 → 检索 → 证据判断 → 可选二次查询 → 生成”做成可控单 Agent 逻辑，定义停止条件/最大迭代次数；再视复杂度决定是否用 LangGraph 做状态编排。
- 后期展示 UI 可考虑 Streamlit，但尚未确定；展示 PDF 文章名、章节、页码、证据与最终答案。
- 对比 Without RAG、Basic Dense RAG、Hybrid/Reranker、Query Optimization、Agentic 版本；整理性能/失败案例/README/环境说明与可复现脚本用于实习简历。

---

## 10. 当前项目文件结构（根据历史已知模块重建，非实时 `ls`）

```text
Advanced-LLM-RAG/
├── .git/
├── .gitignore
├── .venv/                         # 各电脑本地；通常不提交
├── data/
│   ├── raw/                       # 三篇 PDF；通常不提交
│   │   ├── Attention is all you need.pdf
│   │   ├── DCNN.pdf
│   │   └── VGG.pdf
│   └── processed/
│       ├── chunks.json               # Fixed: 340
│       ├── faiss.index               # Fixed: 340 × 384
│       ├── chunks_recursive.json     # Recursive: 340
│       ├── faiss_recursive.index     # Recursive: 340 × 384
│       ├── chunks_semantic.json      # Semantic: 385
│       └── faiss_semantic.index      # Semantic: 385 × 384
├── src/
│   ├── pdf_loader.py
│   ├── chunking.py
│   ├── embedding.py
│   ├── vector_store.py
│   ├── chunk_storage.py
│   ├── retriever.py
│   ├── bm25_retriever.py
│   ├── hybrid_retriever.py
│   └── reranker.py
├── evaluation/
│   ├── questions.json
│   ├── check_evidence.py
│   ├── metrics.py
│   ├── run_evaluation.py
│   ├── pool_chunks.json                # 历史审计材料
│   ├── pool_chunks_recursive.json
│   └── pool_chunks_semantic.json
├── main.py
├── llm.py                           # Windows 本地模型调用，跨机器同步状态待核实
├── PROGRESS.md
└── [计划] src/query_rewriter.py      # 尚未创建/验证
```

`main.py` 历史已导入 `load_pdfs/split_documents/load_embedding_model/embed_chunks/build_index/save_index/load_index/save_chunks/load_chunks/retrieve/build_bm25_index/retrieve_bm25/reciprocal_rank_fusion/rerank_results/CrossEncoder/generate_answer` 等模块。**它当前的确切默认参数、Windows/Mac 的版本差异和是否完整集成所有链路，必须按最新版源码确认**，不能根据单个历史粘贴片段假设。

`evaluation/run_evaluation.py` 的核心逻辑：

```text
加载 questions / MiniLM / FAISS / matching chunks
  → index.ntotal == len(chunks) 检查
  → 创建 BM25、加载一次 CrossEncoder
  → q1～q5：按 quote + source + page 计算 Gold IDs
  → Dense20、BM2520、RRF20、Reranker5
  → 各法拿 Top-5 IDs、单题 P/R/AP/RR
  → 5 道题的 Mean Precision/Recall、MAP、MRR
  → q6 Out-of-Scope 跳过
```

最近用户已经按指导去除了其中 Pool 临时代码；此次三种 Chunking 的最新评估数据来自用户的命令行输出。切换方案历史上通过编辑顶部对应的 `index_path/chunks_path` 两个变量完成，命令：

```bash
python -m evaluation.run_evaluation
```

---

## 11. 协作守则、记忆防丢与新对话完整交接 Prompt

### 11.1 必须遵守的工作习惯

1. **清楚详细的尽你最大努力的回想起RAG项目的所有对话与内容**。先读本进度文件和当前对话/用户提供的最新代码与日志；必要时主动检索可访问的项目历史，而不是只依赖模糊记忆。**无法读取到的历史不要伪称已经完整扫描**。
2. **最新运行结果优先**：历史旧结论如“当前索引 330”“还没实现 BM25”“还没完成 Retrieval Evaluation”“RAG 项目未来做 LoRA”均已失效。
3. **严格一次一个操作**：先解释为什么、会修改哪里、预期输出；等用户给结果再继续，不要一次铺开多个脚本或让用户重复先前完成的步骤。
4. 用户希望**自己动手打代码**并理解 Python、PyTorch、算法的语义、形状和数据流。优先局部代码，只有同一文件反复零散修改造成混乱或用户要求整体整理时再给整文件。
5. **Mac 开发 / Windows RTX 5060 Qwen 推理**不能混淆。Windows 模型不是 Mac 可直接 `import`/调用的在线服务；当前无远程接口。
6. **不加入 Fine-tuning / LoRA / QLoRA**，不把独立 Transformer 项目塞进本项目；现阶段不强制使用 LangChain/Matt Skills，不把 LangGraph、Agent、UI 当已完成。
7. 不擅自操作 Git、不重新构建已确认正确的索引、不反复下载模型、不无依据地夸大性能。发现信息冲突要把冲突说明清楚并向用户索取**最小必要**的最新内容。
8. 每当真正完成一个重要阶段，更新**日期、状态、文件路径、参数、跑出的指标、发现的失败案例和下一项唯一操作**；必要时保留历史版本但不能让旧快照冒充当前状态。

### 11.2 未来对话开场指令（直接复制）

> 请先阅读项目根目录的 `PROGRESS.md`，**清楚详细的尽你最大努力的回想起RAG项目的所有对话与内容**，并结合我随后发的最新代码/终端输出纠正过时信息。项目是用于 AI/LLM 实习简历的科研论文分析 **Advanced-LLM-RAG / Single-Agent（Agentic RAG）**，**不包含 Fine-tuning/LoRA/QLoRA**；MacBook Air + PyCharm 负责主要开发、检索和评估，Windows RTX 5060 本地运行 `Qwen/Qwen3.5-2B`，两机通过 Git/GitHub 同步代码但没有实时跨机器模型 API。Custom PDF Parser V1、Fixed/Recursive/Semantic、FAISS、Dense/BM25/RRF、Cross-Encoder、Basic/Hybrid RAG 和本轮 12 组 Retrieval Baseline 已完成（Fixed 340 / Recursive 340 / Semantic 385 Chunks，最新结果见第 7 节）；不要重做。**目前紧接 Query Rewriting**：先确认 Windows `llm.py` 是否按此前建议删掉 `generate_answer()` 中重复的 `from_pretrained`，然后按一次一个操作的节奏，指导我手写 `src/query_rewriter.py` 的设计与代码，并解释原理。不要越过 Query Optimization 直接实现 Agent。

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
| **10-14 最新** | 以修订后的 Gold 重新跑 Fixed/Recursive/Semantic × 4 Retriever **12 组完整 Evaluation**；暂定 Fixed+Hybrid+Reranker 为工程基线；开始讨论 `llm.py` 的 `lru_cache` 和 Query Rewriting。 | **下一开发阶段是 Query Optimization**。 |

**已经过时、不得复活的陈述**：

- “下一步实现 Dense/BM25/RRF/Reranker” → **已经实现**。
- “只有 330 个 Chunks” → **当前 Fixed/Recursive 340、Semantic 385**。
- “语料含 ResNet.pdf” → **不含；是 VGG.pdf**。
- “Gold Evidence 还未修复或 Pool 尚未创建” → **本轮已补充审查**。
- “Metadata-Aware 分块尚未重建向量索引/完成复评” → **三套索引已检查，最新版 12 组 Evaluation 已完成**。
- “RAG 项目要做 LoRA/QLoRA” → **明确取消**。
- “Mac 可以直接调用另一台电脑的 Qwen” → **尚未搭建远程 API**。
- “q6 股价题也计入五题检索平均数” → **错误，当前被跳过**。
- “`@lru_cache` 已经经 Windows 双次推理运行验证” → **尚无最新日志佐证**。

---

> **维护约定**：本文件的职责是减少跨对话状态丢失。每次实验结果发生变化时，优先更新第 0、7、9、11 节；不要只在旧文档末尾无限追加导致多个互相冲突的“当前状态”。保留必要历史供复盘，但让读者始终能够在第一页看到唯一有效的下一步。
