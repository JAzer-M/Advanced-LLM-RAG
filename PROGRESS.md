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

---

## 8. 最新阶段性进度与交接（2026-10-10 追加）

> **阅读顺序：新对话先读第 8—15 节。第 1—7 节为 2026-10-09 的历史快照，原文保留；其中“尚未实现检索”“索引仅在内存中”“下一步 Dense Retriever”等状态已被下文更新。当前已完成 Dense Retrieval、FAISS 持久化和 Windows 单独 LLM 推理；尚未完成 Retriever → Prompt → LLM 的 Basic RAG 集成。**

### 8.1 本次整理范围与证据来源

- 本文件以 Mac 项目实际存在的 `/Users/j/Desktop/Advanced-LLM-RAG/PROGRESS.md` 为底稿，保留原文并追加；沿用 `PROGRESS.md`，不另建含义重复的 `process.md`。
- 2026-10-10 读取了关联聊天“RAG项目续续”（conversationId：`6ac8ae06-88a8-83e9-b0f9-e5102d87d8be`）。读取接口只返回最后 5 个回合且没有更早分页游标，部分历史代码块显示为内容引用占位符。因此本记录结合可读取聊天、本次用户明确给出的补充信息，以及实际可读的 Mac 项目文件整理；不冒充逐字完整聊天导出。
- Mac 的检索、索引持久化和 Git 状态在本次本地检查中核实。Windows 的硬件、依赖版本、模型加载及 CUDA 推理情况来自用户补充和历史聊天日志；本次没有远程连接 Windows 或重新运行 Windows 模型。
- 下文代码用于恢复实现逻辑和交接，不是 Windows `llm.py` 的逐字拷贝。当前可访问的 Mac 项目根目录没有 `llm.py`，尚不能据此认定 Windows 的 LLM 代码已经同步回 Mac 或提交到 GitHub。

### 8.2 当前状态总览

| 模块 / 阶段 | 最新状态 | 依据与边界 |
| --- | --- | --- |
| PDF 逐页加载、固定字符分块 | 已完成 | 延续原项目；32 页、330 chunks |
| MiniLM Embedding | 已完成 | 384 维，归一化向量；Mac 使用 CPU |
| FAISS Dense Retriever | 已实现 | 已读取 `src/retriever.py` 和 `main.py`；当前 Top-K 为 5；本次没有重跑完整检索评估 |
| FAISS + chunks 持久化 | 已完成并核实产物 | 成功读取 `faiss.index` 和 `chunks.json`：330 个向量、384 维、330 条元数据 |
| Git / GitHub 阶段进度 | 已有本地提交及远程跟踪记录 | 详见第 9.3 节；未重新联网核验远端 |
| Windows CUDA 环境 | 已测试成功（历史记录） | RTX 5060 8GB，Python 3.11.9，PyTorch 2.13.0+cu130 |
| Qwen 下载与加载 | 已成功（历史记录） | `Qwen/Qwen3.5-2B`，HF 本地缓存，BF16 / `cuda:0` |
| 单独 LLM 文本生成 | 已成功 | 聊天中用户贴出 VGG 问题的 `Generated answer` |
| 回答质量与完整性 | 尚需改进 | VGG 梯度消失解释不准确，输出中途截断 |
| Prompt Construction | 下一步，尚未完成 | 尚未将 FAISS Top-K 片段组织为 Qwen 的输入上下文 |
| Basic RAG 端到端链路 | **尚未完成** | Retriever 与 LLM 分别可用，不等于两者已经接通 |
| BM25 / Hybrid / RRF / reranker / evaluation | 后续待实现 | 不写成现有成果 |
| LoRA | 可选后续实验 | 当前无需训练或微调才能接入 RAG |

## 9. Mac 阶段：Dense Retrieval、持久化与 Git 进度

### 9.1 Dense Retriever 已实现

当前实际结构在旧记录基础上增加了：

```text
src/
├── pdf_loader.py
├── chunking.py
├── embedding.py
├── vector_store.py      # build_index / save_index / load_index
├── chunk_storage.py     # save_chunks / load_chunks
└── retriever.py         # retrieve
data/processed/
├── faiss.index
└── chunks.json
```

`retrieve(model, index, chunks, query, top_k=5)` 的现有逻辑：

1. 调用与文档相同的 Sentence Transformer 对 `[query]` 编码；设置 `convert_to_numpy=True`、`normalize_embeddings=True`。
2. 将查询向量转换为连续内存的 `numpy.float32`，单个问题的形状为 `(1, 384)`。
3. 执行 `scores, indices = index.search(query_embedding, top_k)`。
4. 遍历 `scores[0]` 与 `indices[0]`，跳过 `idx == -1`，用 `chunks[int(idx)]` 查回原文。
5. 返回结果列表，每条结果包含 `score`、`source`、`page`、`text`；`score` 转为 Python `float`。

实际 `main.py` 已使用以下问题和参数：

```python
query = "Why does VGG use small 3×3 convolutional filters?"
results = retrieve(model=model, index=index, chunks=chunks, query=query, top_k=5)
```

随后按排序逐条输出 Score、Source、Page、Text。该问题与后续 Qwen 单独推理的问题形成可比较的实验起点，但尚无正式检索指标或 RAG 质量结论。

### 9.2 FAISS 与 chunk 元数据保存 / 重载

- 索引位置：`data/processed/faiss.index`。
- chunk 元数据位置：`data/processed/chunks.json`。
- `save_index` / `load_index` 使用 `faiss.write_index` / `faiss.read_index`。
- `save_chunks` 使用 JSON、UTF-8、`ensure_ascii=False`；`load_chunks` 读取列表。
- `main.py` 用 `Path(__file__).resolve().parent` 构造项目内路径，不依赖 IDE 的当前工作目录。
- 当两个文件同时存在时加载已有产物；否则重新执行 PDF → chunks → embeddings → index 并保存两者。
- 加载或构建后检查 `index.ntotal != len(chunks)`，不匹配时抛出异常。

本次直接读取保存的产物，核实结果：

```text
Index type: IndexFlatIP
Total Vectors: 330
Vector Dimensions: 384
Total Chunks: 330
Chunk fields: text, source, page
```

这验证了文件可读及数量相符，不等于重新验证所有检索结果。数量检查也不能发现“数量相同但顺序错位”的情况，索引与 chunks 仍应保持同批次生成、同顺序保存。

### 9.3 Git / GitHub 与两台设备同步

本次 Mac 本地可见提交：

```text
4c6c168  2026-10-09 18:49:20 +08:00  Implement dense retrieval and FAISS persistence
d04be78  2026-10-09 14:24:51 +08:00  Inititalize project Git configuration
```

检查时 Mac 工作区无未提交变更，分支显示 `main...origin/main`，没有显示领先 / 落后计数。这是本地远程跟踪信息；未执行 fetch 或访问 GitHub，不能据此保证远端此刻没有新变更。追加本文后，`PROGRESS.md` 会成为新的文档变更，本次不自动 commit / push。

后续协作方式：Mac 继续用于编码与整理，Windows 用于 CUDA 模型推理；通过 Git / GitHub 同步源代码和进度文档。切换设备前在当前设备确认改动并提交 / 推送，再在另一台设备拉取；每次教学只安排其中一个具体操作。

`.gitignore` 继续忽略 `.venv/`、`data/raw/`、`data/processed/`、模型权重和本地配置。因此：

- 两台设备各自建立虚拟环境，不复制 `.venv`。
- 原始 PDF 和持久化索引不会随普通代码同步自动出现，需要在另一台设备另行准备，或从相同 PDF 重建。
- HF 模型缓存放在各自设备，**无需加入仓库**。
- Windows `llm.py` 的提交与同步状态尚未核实；下一阶段接线前应读取当前 Windows 代码，避免根据 Mac 文件误判进度。

## 10. Windows 阶段：环境、Qwen 下载与加载

### 10.1 已记录的环境

| 项目 | 已记录值 / 状态 |
| --- | --- |
| 系统 | Windows |
| GPU | NVIDIA GeForce RTX 5060，8GB 显存 |
| Python | 3.11.9 |
| 项目虚拟环境 | 项目内 `.venv` |
| PyTorch | `2.13.0+cu130` |
| CUDA 测试 | 已成功（用户提供的阶段结果） |
| Transformers | `5.19.0` |
| torchvision | 本次环境准备中已安装 / 处理；精确版本未提供，不补写 |
| 模型 | `Qwen/Qwen3.5-2B` |
| LLM 设备 | `cuda:0` |
| LLM 浮点类型 | `torch.bfloat16`，即 BF16 |
| Windows 项目位置 | `C:\Users\J\Desktop\Advanced-LLM-RAG` |
| 推理脚本 | 项目根目录的 `llm.py` |

检索链路依赖仍包括 `pymupdf`、`sentence-transformers`、`numpy`、`faiss-cpu` 等；旧 Mac 环境记录还包括 `httpx[socks]`。这不表示已逐一确认 Windows 安装了旧 Mac 的全部包。此次未导出 Windows 完整依赖锁定文件，也未记录 torchvision 等所有依赖的精确版本。

`+cu130` 是当前 PyTorch 构建的 CUDA 标记；不能据此推断机器另外安装的独立 CUDA Toolkit 版本。当前 CUDA 测试成功及实际生成成功是本阶段可用性的依据，不在本次文档更新中升级或重装环境。

### 10.2 模型下载与缓存

`Qwen/Qwen3.5-2B` 已下载到 Hugging Face 本地缓存，后续 `from_pretrained` 可复用缓存，不需要每次从头下载，也不需要把模型文件复制进项目目录或上传 GitHub。

记录中的加载入口：

```python
from transformers import AutoProcessor, AutoModelForMultimodalLM
```

`AutoProcessor` 和 `AutoModelForMultimodalLM` 均已成功加载对应模型资源；模型在 BF16、`cuda:0` 上完成过生成。加载阶段成功和生成阶段成功分开记录，后者由用户实际贴出的答案确认。

Qwen 的 processor 可统一处理模型的输入格式；本项目目前只测试文本。使用多模态模型类不代表已完成图片 / 视频输入功能，也不代表 RAG 已经接通。原始论文检索依旧由 MiniLM + FAISS 执行，不是用 Qwen 的 token embedding 替换已有 384 维检索向量。

## 11. `llm.py` 推理链路与排错记录

### 11.1 当前已跑通的链路

```text
用户问题
  → messages（角色与内容）
  → processor.apply_chat_template（对话格式 + tokenization）
  → inputs（input_ids、attention_mask 等 Tensor）
  → 送至 cuda:0
  → model.generate 自回归生成
  → 切去输入部分，只保留新 Token
  → processor.decode
  → Generated answer
```

下面为依据聊天信息整理的等价流程，便于新对话理解；不声称是已读取的 Windows 文件原文。具体加载参数和现有消息角色应以用户 Windows 当前 `llm.py` 为准，不要求此刻整体替换：

```python
import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM

model_id = "Qwen/Qwen3.5-2B"
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForMultimodalLM.from_pretrained(
    model_id,
    dtype=torch.bfloat16,
).to("cuda:0")
model.eval()

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Why does VGG use small 3×3 convolutional filters?",
            }
        ],
    }
]

inputs = processor.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors="pt",
    return_dict=True,
)
inputs = inputs.to("cuda:0")

with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=128,
        do_sample=False,
    )

input_length = inputs["input_ids"].shape[-1]
full_sequence = outputs[0]
generated_ids = full_sequence[input_length:]
answer = processor.decode(generated_ids, skip_special_tokens=True)
print("Generated answer:")
print(answer)
```

关键参数含义：

- `messages`：Python 列表；每条消息是字典，`role` 表达说话角色，`content` 中的 `type="text"` 和 `text` 表达文本内容。
- `apply_chat_template`：按模型约定添加角色、分隔符和回复起点；`tokenize=True` 才会同时进行 tokenization。仅应用聊天模板不必然得到 Tensor，要结合参数看返回值。
- `return_tensors="pt"`：返回 PyTorch Tensor；`return_dict=True`：返回可通过键访问的模型输入对象。
- `add_generation_prompt=True`：按模板添加待生成回复的起始标记。
- `inputs.to("cuda:0")`：让输入与模型处于相同设备；Token IDs 保持整数，不能为“统一 BF16”而把 IDs 转成浮点数。
- `**inputs`：Python 字典解包，将 `input_ids`、`attention_mask` 等键值展开为模型参数。
- `max_new_tokens=128`：最多新增 128 个 Token，不是 128 个字、128 个单词，也不包括输入长度；遇到结束条件可以提前停止。
- `do_sample=False`：不随机采样；在单束 `num_beams=1` 条件下是贪心选择。保留稳定的生成设置有利于比较后续不同检索方案。
- 当前使用默认的序列 Tensor 返回方式；processor 的 `return_dict=True` 与生成端的 `return_dict_in_generate=True` 是不同选项，不应混淆。

### 11.2 已排查的拼写与切片问题

| 错误 | 正确形式 | 影响 / 解释 |
| --- | --- | --- |
| `return_dic` | `return_dict=True` | 参数名拼写错误；按预期获得可按键访问的输入 |
| `inputs["inputs_ids"]` | `inputs["input_ids"]` | 多写了一个 `s`，导致 `KeyError: 'inputs_ids'` |
| `outputs[0][input_length]` | `outputs[0][input_length:]` | 前者只取一个 Token；后者取从该位置到末尾的整段新 Token |

最终核心写法：

```python
generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
```

错误日志显示程序在提取输出时停止，说明那一次执行已经通过 `model.generate()`；修正键名及切片后，用户贴出了实际生成文字，确认从加载到解码的流程已跑通。

最后一次概念讲解建议将这一行拆为 `input_length`、`full_sequence`、`generated_ids` 三行，并打印输入 / 输出形状帮助理解。**尚无后续反馈确认用户已添加这些打印或执行该验证**，不可把建议写成已完成操作。

### 11.3 优化 kernel 缺失警告

日志出现以下算子 fallback：

| 缺失包 | 涉及的日志算子 |
| --- | --- |
| `causal_conv1d` | `causal_conv1d_fn`、`causal_conv1d_update` |
| `flash-linear-attention` | `chunk_gated_delta_rule`、`fused_recurrent_gated_delta_rule` |

Transformers 已回退到参考 PyTorch 实现。当前生成能运行，警告主要提示性能影响；这些警告与 `KeyError` 的代码拼写问题是两类事情。没有优化 kernel 不等于 CUDA 不可用，也不代表模型加载失败。

当前保留 fallback，先接通 Basic RAG。尚未安装 / 验证这些优化库，尚未测量加速效果；后续若处理速度问题，应先核实 Windows、PyTorch、CUDA 和包版本的兼容性，再决定优化方式。

### 11.4 首次 VGG 回答与质量问题

用户已经看到 `Generated answer:`，模型回答 VGG 采用小型 3×3 卷积核主要为了缓解梯度消失并保持空间分辨率；输出停在对 vanishing gradient 的说明中途。

本次讨论的纠正要点：

- “主要为了缓解梯度消失”的论点不准确，不能把它作为正确参考答案。
- 堆叠 3×3 卷积可以在步长等条件相同的情况下扩大有效感受野；例如两个 3×3 层对应 5×5 的有效感受野。
- 在输入输出通道数等可比条件下，小卷积堆叠可减少相对于单个大卷积的参数量，并加入更多非线性变换。
- 是否保持空间分辨率还取决于 padding、stride 等配置，不能仅由卷积核尺寸推出。
- 输出截断与 `max_new_tokens=128` 达到上限的现象一致；没有记录实际新 Token 数和停止原因，因此把长度上限记为待验证的主要原因，不能断言已证明。

首次推理的验收是“本地模型能生成文字”，不是“答案已经正确完整”。后续应以检索到的论文原文为依据检查回答；RAG 也不能自动保证正确，需要核对上下文、引用和最终陈述。

## 12. 本次概念学习记录

### 12.1 Tokenizer、Vocabulary 与 embedding

```text
Python 字符串
  → Tokenizer 分词 / 编码
  → Vocabulary 对应 Token IDs（整数）
  → 模型 embedding layer 查得稠密向量
  → Transformer 的数值运算
```

Transformer 要进行矩阵运算，不能直接把 Python 字符串当作数值 Tensor。Token 不必对应一个完整单词；Token ID 是词表编号，不是语义向量，其数字大小没有天然语义距离含义。

若一条输入含 L 个 Token，概念上 Token IDs 的形状是 `(1, L)`，进入模型 embedding 后是 `(1, L, hidden_size)`。模型内部的 token embedding 与用于 FAISS 检索的 384 维 chunk embedding 用途不同：前者服务语言模型计算，后者服务文档语义检索。

### 12.2 预训练模型、LLM 与 RAG

- 预训练模型已经具有学习得到的权重；当前下载模型是在复用权重，不是从零训练，也不是下载后自动继续学习。
- 单独 LLM 根据问题和参数中的知识生成答案，可能出现流畅但不准确的专业解释。
- RAG 先检索外部文档，再将相关原文与问题一起放入 Prompt，交给 LLM 回答。
- 当前主要变化将发生在输入 Prompt；已有 generate、切片和 decode 流程可以继续复用。Basic RAG 不要求先进行 LoRA 或反向传播。

### 12.3 FP32 / FP16 / BF16

| 类型 | 位数 | 本阶段需要理解的差异 |
| --- | ---: | --- |
| FP32 | 32 | 数值精度较高，权重存储占用较大 |
| FP16 | 16 | 比 FP32 节省存储，指数范围较窄 |
| BF16 | 16 | 比 FP32 节省存储，指数范围接近 FP32，但有效精度更低 |

本次 Qwen 使用 BF16。精度格式影响显存和数值计算，但不能仅按权重位数推断总显存占用：运行时还包含缓存、激活及其他开销。当前记录是该机器已完成一次生成，没有覆盖任意长输入、任意 batch 的显存验证。

### 12.4 自回归生成与无梯度推理

自回归生成每一步根据 Prompt 与已生成的 Token 预测下一 Token，再继续向后生成。每一步计算词表候选分数，不等于返回所有候选答案，也不等于保存所有中间长度的序列。

训练通常涉及前向计算、loss、反向传播与参数更新；当前推理只用已有权重计算输出，不需要 optimizer 或 `loss.backward()`。

- `model.eval()`：让 Dropout 等模块使用评估行为；它本身不关闭自动求导。
- `torch.inference_mode()`：关闭常规梯度追踪并减少相关开销；不替代 `eval()` 的模块行为切换。
- 当前不更新模型参数，不等于不使用显存，也不等于生成时完全没有状态；例如自回归推理可以维护生成缓存。

### 12.5 `outputs` 到底包含多少条序列

必须区分词表大小、单条序列长度、输入 batch 大小和每个输入返回多少个候选答案。

在当前单条文本输入、默认返回一个答案、默认生成输出为 Tensor 的场景：

```text
inputs["input_ids"].shape = (1, L)
outputs.shape           = (1, L + G)
outputs[0].shape        = (L + G,)
generated_ids.shape     = (G,)
```

`L` 是处理器实际产生的输入长度，包含聊天模板的 Token；`G` 是新生成长度，本次 `G <= 128`。例如输入 5 个 Token、新增 4 个，`outputs.shape` 是 `(1, 9)`。

逐项解释切片：

1. `outputs[0]` 取第一条完整序列，不是第一个 Token。
2. `inputs["input_ids"].shape[-1]` 取输入 Tensor 的最后一个维度，即输入长度 L。
3. `[L:]` 表示从索引 L 开始一直取到末尾，去掉前面的输入 Token。
4. `decode` 将留下的新 Token IDs 转成答案文本，不会再次调用模型生成。

一般情况下，若输入 B 个问题、每个返回 R 个候选，序列 Tensor 的第一维通常是 `B * R`，而非词表大小。多答案需要选择支持的策略：采样可返回多个候选；beam search 也可配置多个返回序列；不能仅在默认单束贪心配置上随意把 `num_return_sequences` 改成 3。

批量返回时长度可能通过 padding 对齐；本项目目前只需理解单条输入。若以后启用 `return_dict_in_generate=True`，应从 `outputs.sequences` 读取序列，不能继续无条件把 `outputs` 本身当二维 Tensor。若换成 encoder-decoder 模型，也不能直接套用“返回包含输入 Prompt”的假设。

### 12.6 生成是否每次不同

当前 `do_sample=False` 且单束生成时，通常逐步选取最高分 Token；在模型、Prompt、参数和环境相同的情况下，结果通常稳定，但不承诺跨设备 / 环境逐字一致。

`do_sample=True` 才启用随机采样，`temperature` 和 `top_p` 可以影响采样分布；更随机不代表更正确。本次没有要求改用随机采样。后续比较 without RAG、Basic RAG、Hybrid 和 reranker 时，应固定问题、模型及生成参数，并记录截断情况。

## 13. 下一步：Prompt Construction 接通 Basic RAG

### 13.1 当前唯一主线目标

把 FAISS 返回的 Top-K 结果列表转成带来源的上下文，将“上下文 + 问题”放入 Qwen messages，复用已跑通的推理代码，完成一次端到端回答：

```text
Question
  → MiniLM query embedding
  → FAISS Top-K chunks
  → Context + source / page
  → Prompt / messages
  → Qwen3.5-2B
  → Answer + 可核对的来源
```

当前断点在 `results` 列表与 Qwen `messages` 之间。下一阶段不需要重写 PDF 加载、重新选择 embedding 模型或先安装优化 kernel。

### 13.2 新对话建议的第一步（一次只做这一项）

先读取用户 Windows 当前 `llm.py` 和调用检索的入口代码，确认在哪里能够拿到 `results`；不要默认 `llm.py` 已在 Mac 或 GitHub 中。结合现有代码，**只完成把 Top-K 检索结果拼成 context 字符串并打印检查**，解释列表、字典、遍历和字符串拼接，等待用户反馈后再改 Qwen messages。

上下文格式可采用以下设计草案，尚未实现：

```text
[1] Source: DCNN.pdf | Page: <实际页码>
<该结果的原文 text>

[2] Source: <实际文件名> | Page: <实际页码>
<该结果的原文 text>
```

来源、页码和原文必须取自检索结果，不手写猜测论文页码。当前 Top-K 可沿用 5，先确认片段与 VGG 问题相关；分数仅用于相似度排序，不把它解释为答案正确概率。

### 13.3 随后逐步推进（不是同时安排给用户的任务）

1. 上下文打印正确后，再将 context 与 question 组织成 Prompt，并送入现有 `messages`。
2. 提示模型根据给定上下文回答、用片段编号引用依据、证据不足时明确说明；把检索到的文字作为资料处理，不作为额外操作指令。
3. 保留 `do_sample=False`，完成一次从检索到生成的运行，核查回答是否覆盖相关原文。
4. 检查新 Token 数、输出是否完整；必要时单独调整输出预算，避免把截断误判为 RAG 无效。
5. 用同一问题对比 without RAG 与 Basic RAG 的正确性、依据和完整性，再记录结果。

完成条件：能够实际运行“提问 → 检索 → 构建 Prompt → 本地 Qwen → 解码答案”，并检查回答与来源一致。在此之前，继续将 Basic RAG 标记为未完成。

## 14. 后续路线与协作约定（最新）

- [x] PDF 加载、分块、MiniLM Embedding、FAISS 索引。
- [x] Dense Retriever 与结果展示代码。
- [x] FAISS 索引和 chunk 元数据持久化 / 重载。
- [x] Windows CUDA 环境准备与测试成功（历史运行记录）。
- [x] Qwen3.5-2B 下载、加载与单独文本生成（历史运行记录）。
- [ ] Windows `llm.py` 的 Git 提交 / 跨设备同步状态核实。
- [ ] Prompt Construction：将 Top-K chunks 整理为带来源的上下文。
- [ ] Basic RAG：接通检索、Prompt、LLM 与解码，验证端到端运行。
- [ ] BM25：加入稀疏检索。
- [ ] Hybrid Retrieval / RRF：融合 Dense 和 BM25 候选排序。
- [ ] Cross-Encoder reranker：对候选片段重排序。
- [ ] Evaluation：建立问题、参考依据及评估标准，对比 baseline、Basic RAG 和改进版本。
- [ ] 按评估结果考虑分块优化、Query Rewriting、HyDE、速度优化和应用展示。
- [ ] 可选 LoRA 实验：基础链路与评估稳定之后再考虑。

协作要求继续有效：

- 中文为主，解释代码的原理、变量形状和执行顺序，帮助用户自己理解实现。
- **一次只安排一步具体操作，等用户运行 / 确认后再继续。** 路线图可保留，但不要一次要求完成整条链路。
- 暂不引入 LangChain 或 Matt Skills，继续手写流程；不因本次整理而改变项目技术路线。
- 明确区分“用户历史运行成功”“本次读取代码确认”“建议但尚未执行”“真正完成端到端验证”。
- 不因 LLM 单独输出了答案，就宣称已完成 Basic RAG、优化 kernel、正式评估或 LoRA。
- Git 同步尊重用户操作节奏，不自动执行 commit / push，不将模型缓存与虚拟环境加入仓库。

## 15. 可直接用于新对话的交接摘要

请继续我的 Advanced-LLM-RAG 项目，并先读本文件第 8—15 节，前 7 节是保留的旧进度。项目用于 AI / LLM 实习准备，中文讲解，手写流程，暂不使用 LangChain / Matt Skills；每次只安排一步操作，解释原理并等我反馈。

Mac 阶段已完成 PDF → 330 chunks → multilingual MiniLM 384 维归一化 embedding → FAISS IndexFlatIP → Top-K Dense Retriever，并已保存 / 重载 `data/processed/faiss.index` 和 `chunks.json`。本次读取产物确认 330 vectors、384d、330 chunks。相关代码已有提交 `4c6c168`，Mac 和 Windows 通过 Git / GitHub 同步，但数据、索引、虚拟环境和模型缓存不随普通提交同步。Mac 路径 `/Users/j/Desktop/Advanced-LLM-RAG`，Windows 路径 `C:\Users\J\Desktop\Advanced-LLM-RAG`。

Windows 为 RTX 5060 8GB、Python 3.11.9、PyTorch 2.13.0+cu130（CUDA 测试成功）、Transformers 5.19.0；torchvision 已在环境准备中处理，精确版本未记录。`Qwen/Qwen3.5-2B` 已下载至 HF 本地缓存，无需进仓库；`AutoProcessor` 与 `AutoModelForMultimodalLM` 已成功加载，BF16 / `cuda:0`。

`llm.py` 已单独跑通 messages → `apply_chat_template(tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True)` → `model.generate(**inputs, do_sample=False, max_new_tokens=128)` → `outputs[0][inputs["input_ids"].shape[-1]:]` → decode。已解决 `return_dic`、`inputs_ids` 拼写及切片缺冒号。缺少 `causal_conv1d` / `flash-linear-attention` 优化 kernel 时 fallback 可运行，暂不优先处理。Windows `llm.py` 是否已经提交或同步回 Mac 尚未核实。

VGG 问题已经生成文字，但把“小型卷积主要缓解梯度消失”作为理由不准确，回答也中途截断；128 新 Token 上限是主要待验证原因。已讨论 Tokenizer / Vocabulary / embedding、预训练模型、FP32 / FP16 / BF16、LLM 与 RAG、自回归、无梯度推理，以及 outputs 第一维是返回序列数而非词表候选数；默认当前只有一条序列。

**当前尚未完成 Basic RAG 的 LLM 集成。下一步是 Prompt Construction：先检查 Windows 当前 `llm.py` 和检索入口，只把 FAISS Top-K 的 text、source、page 拼成 context 并打印检查，再逐步接入 Qwen。** 后续才是 BM25、Hybrid / RRF、reranker、evaluation 和可选 LoRA。不要重复从环境搭建开始，也不要把待实现功能写成已完成。
