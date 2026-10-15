# Advanced-LLM-RAG

科研论文问答项目，使用手写的 PDF 解析、分块、Dense/BM25 检索、RRF、重排和本地 Qwen。

当前保留原有函数、文件结构和调用方式。代码整理主要删除调试残留、无用导入和多余空行，不改写算法或引入通用框架。

## 环境与数据

项目原环境为 Python 3.11.9。依赖清单见 `requirements.txt`；它不是完整锁定文件，Windows 还需匹配本机的 PyTorch/CUDA 环境。

原 PDF 放在 `data/raw/`，索引和 Chunk JSON 放在 `data/processed/`。模型缓存、数据和 `.venv` 不随 Git 同步。

当前三篇论文为 Transformer、DCNN、VGG；Fixed/Recursive/Semantic 分别有 340/340/385 个 Chunk。FAISS 与对应 JSON 必须配对，不同分块方案的 ID 不能互换。

## 原来的运行方式

在项目根目录运行：

```bash
python main.py
python build_recursive_index.py
python build_semantic_index.py
python -m evaluation.run_evaluation
python -m evaluation.check_evidence
```

`main.py` 默认使用 Semantic + BGE，交互输入问题。`USE_MULTI_QUERY` 控制是否改写；完整生成和改写需要本地 Qwen 缓存，历史运行在 Windows GPU。

`evaluation/run_evaluation.py` 中的 `ENABLE_REWRITING` 控制四组或六组评估。`check_evidence.py` 保留原来的 Fixed JSON 路径，检查其他分块时修改其中的 `chunks_path`。

构建脚本会保存对应索引和 Chunk JSON；这是原有行为，重建实验前应另存现有基线。

## 文件说明

- `src/pdf_loader.py`：正式 Parser V1；`pdf_loader_v2.py`：尚未接入主线的文本块实验。
- `src/chunking*.py`：三种分块；`embedding.py`、`vector_store.py`、`chunk_storage.py`：向量和文件处理。
- `src/*retriever.py`、`reranker.py`：检索、融合与重排。
- `src/query_rewriter.py`、`llm.py`：查询改写和本地 Qwen。
- `evaluation/`：问题、证据检查、指标及历史候选池。

当前进度见 [PROGRESS.md](PROGRESS.md)，历史实验与失败案例见 [docs/experiments.md](docs/experiments.md)。
