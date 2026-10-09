# Advanced-LLM-RAG 项目进度

更新日期：2026-10-09

## 1. 项目定位与协作约定

开发一个用于 AI / LLM 相关实习简历的综合型 Advanced RAG 系统。从手写 Basic RAG 流程开始，逐步加入高级检索、检索优化、评估实验和应用展示。

- 当前暂不使用 Matt Skills 或 LangChain。
- 教学时一次只做一个操作，完成并确认后再继续。
- 解释 Python 代码的原理、数据结构和执行过程，帮助理解实现。
- LoRA 微调属于后续可选实验，不是当前重点。

## 2. 开发环境

| 项目 | 当前情况 |
| --- | --- |
| 主要开发设备 | MacBook Air |
| IDE | PyCharm |
| Python | 3.11.9，项目内 `.venv` 虚拟环境，已本地核实 |
| 深度学习框架 | PyTorch |
| 当前 Embedding 运行设备 | CPU，代码指定 `device="cpu"` |
| 后续 GPU 设备 | RTX 5060 笔记本，计划用于 GPU 推理和训练 |
| 项目同步 | 通过 GitHub 同步 |
| Mac 项目路径 | `/Users/j/Desktop/Advanced-LLM-RAG` |

已在项目虚拟环境中核实安装：

```text
pymupdf
sentence-transformers
torch
transformers
numpy
faiss-cpu
httpx[socks]
```

其中 `httpx[socks]` 所需的 `httpx` 和 `socksio` 均已安装。

## 3. 当前项目结构

```text
Advanced-LLM-RAG/
├── .venv/
├── data/
│   ├── raw/
│   │   ├── Attention is all you need.pdf
│   │   ├── DCNN.pdf
│   │   └── ResNet.pdf
│   └── processed/
├── src/
│   ├── pdf_loader.py
│   ├── chunking.py
│   ├── embedding.py
│   └── vector_store.py
├── main.py
├── .gitignore
└── PROGRESS.md
```

上述代码文件和数据目录已本地检查。`data/processed/` 当前为空，尚未保存索引或元数据。

`.gitignore` 已忽略虚拟环境、Python 缓存、PyCharm 配置、原始及处理后数据、模型权重、日志和环境变量文件。通过 GitHub 同步代码时，三个原始 PDF 不会随常规提交自动上传，需要在另一台设备另行准备。

## 4. 已完成：PDF → Chunks → Embeddings → FAISS Index

### 4.1 PDF 加载

`src/pdf_loader.py` 使用 PyMuPDF，按文件名排序加载 `data/raw/` 下的 PDF，逐页提取文本。

| 文件 | 页数 |
| --- | ---: |
| Attention is all you need.pdf | 11 |
| DCNN.pdf | 7 |
| ResNet.pdf | 14 |
| 合计 | 32 |

每页对应一个字典，包含：

- `text`：该页提取出的文本。
- `source`：PDF 文件名。
- `page`：从 1 开始的页码。

### 4.2 固定字符分块

`src/chunking.py` 按页进行固定字符长度分块，保留 `text`、`source`、`page`。

```python
chunk_size = 500
chunk_overlap = 100
```

参数单位是 Python 字符串中的字符，不是 token。滑动步长为 `500 - 100 = 400`；分块不跨页，空白文本会跳过，页尾块可以短于 500 个字符。

本次使用现有 PDF 和现有分块代码重新核实：32 页，共 **330 chunks**。

### 4.3 Embedding

`src/embedding.py` 使用 Sentence Transformers：

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

当前参数：

```python
device = "cpu"
batch_size = 16
convert_to_numpy = True
normalize_embeddings = True
```

每个 chunk 生成一个归一化的 384 维向量。此前成功运行得到的 Embedding 矩阵形状为 `(330, 384)`。

### 4.4 FAISS 索引

`src/vector_store.py` 的 `build_index(embeddings)` 已实现：

1. 将 Embedding 矩阵转换为连续内存布局的 `numpy.float32` 数组。
2. 从 `embeddings.shape[1]` 读取向量维度。
3. 创建 `faiss.IndexFlatIP(dimension)`。
4. 调用 `index.add(embeddings)`，返回索引。

`IndexFlatIP` 按内积搜索；当文档向量和查询向量都经过 L2 归一化时，内积等价于余弦相似度。分数越高，向量越相似，分数不是概率。

用户已确认索引构建运行成功，关键结果为：

```text
Total pages: 32
Total chunks: 330
Embedding Matrix Shape: (330, 384)
Total Vectors: 330
Vector Dimensions: 384
```

注意：现有 `main.py` 的实际输出标签是复数 `Vector Dimensions:`，此前交接文字中的 `Vector Dimension:` 为单数；两者指向同一个 `index.d` 属性。

本次检查核实了代码、环境、PDF 页数及分块数量；未重新执行模型编码和完整索引构建。上述 Embedding 和 FAISS 成功结果来自此前用户确认，相关参数与当前代码一致。

目前索引仅存在于运行时内存中，程序退出后不会自动保存。当前尚未实现检索，也尚未接入 LLM 生成答案。

## 5. 下一步：实现 Dense Retriever

目标流程：

```text
用户提问
  → 使用与文档相同的 Embedding 模型
  → 生成归一化的 query embedding
  → FAISS search，取 top-k
  → 根据返回的向量索引定位原始 chunk
  → 输出 score、source、page、text
```

待实现要点：

- 查询编码使用相同模型，并设置 `normalize_embeddings=True`。
- 查询向量应为二维数组，形状为 `(1, 384)`，并满足 FAISS 的连续 `float32` 格式要求。
- 使用 `index.search(query_embedding, k)` 获取分数和向量索引。
- 向量添加顺序与 `chunks` 列表顺序一致，因此有效索引 `i` 对应 `chunks[i]`。
- 保持索引与 chunk 列表一一对应；处理搜索结果时跳过无效索引（例如 `-1`）。
- 每条检索结果展示相似度分数、来源文件、页码和原文片段。

首次测试可使用：

```text
Why are residual connections important in ResNet?
```

先尝试 `top-k = 5`，检查检索结果是否包含与残差连接相关的 ResNet 内容。此问题与参数是下一步测试建议，尚未执行或验证检索效果。

## 6. 后续路线（均待实现）

- [ ] Dense Retriever：实现问题编码、向量搜索及结果展示。
- [ ] 持久化：保存并加载 FAISS 索引和 chunk 元数据，保持顺序对应。
- [ ] LLM 接入：将检索片段组织为上下文，生成有来源依据的回答。
- [ ] Advanced Retrieval：加入 BM25，与 Dense 检索结合，通过 RRF 融合排序。
- [ ] Cross-Encoder rerank：对候选片段重排序。
- [ ] RAG Optimization：尝试 Query Rewriting、HyDE 和分块策略优化。
- [ ] Evaluation：准备评估问题与参考依据，比较检索和回答效果，记录实验结果。
- [ ] 应用展示与部署：提供可演示界面，完善使用说明。
- [ ] 可选实验：LoRA 微调，在基础系统和评估流程稳定后再考虑。

## 7. 新对话续接提示

请先阅读本文件，并检查现有代码。当前已完成 PDF 加载、固定字符分块、MiniLM Embedding 和 FAISS 内存索引构建；下一步是 Dense Retriever。保持一次只做一个操作并解释 Python 原理的教学节奏，暂不使用 Matt Skills 或 LangChain，不把计划功能当作已完成，不自动执行 Git commit 或 push。
