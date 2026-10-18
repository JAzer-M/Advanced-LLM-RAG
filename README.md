# Advanced-LLM-RAG

面向科研论文的 RAG 问答项目：PDF 解析 → Semantic 分块 → Dense/BM25 检索 → RRF 融合 → 问题分解补检索 → Cross-Encoder 重排 → 证据整理 → API 回答与引用检查。

当前生成模型为 `cn:deepseek-v4.1-flash`。Embedding 与重排在本机 CPU 运行；问题分解、回答和必要时的一次引用修复共用本机反代 API。

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

需要重建时运行 `python build_semantic_index.py`；它会覆盖 Semantic 索引及 JSON，请先保存要保留的基线。`build_recursive_index.py` 保留为 Recursive 分块的独立构建入口。

## 评估与结果

```powershell
# 六题真实主流程，保存每次 API 调用、答案、证据和引用编号
python -m evaluation.run_answer_evaluation --output-dir evaluation/results/new_run

# 固定证据，只检查生成；输入和输出目录须不同
python -m evaluation.run_answer_evaluation --question-id q1 q5 --replay-dir evaluation/results/deepseek_v41/initial --output-dir evaluation/results/new_replay

# 检索方法对照，以及 Gold 引文与当前分块的匹配检查
python -m evaluation.run_evaluation
python -m evaluation.check_evidence
```

以上回答评估会调用 API。`run_evaluation.py` 是历史 Top-5 检索方法对照，参数与主流程 Top-10 不同，其指标不能替代当前回答评价。Gold/reference_answer 仅供评估，不传给回答模型。

DeepSeek 已完成首次六题运行、固定证据调试及清理后的全流程复核。核心事实明显好于历史本地 2B；对绝对化措辞与配置例外的处理仍有瑕疵，不能宣称全面优于 Kimi。引用检查验证编号结构，语义支撑仍需人工核对。

- [三个新题、rewrite/HyDE 与本地模型同题对照](docs/REWRITE_HYDE_LOCAL_COMPARISON_2026-10-18.md)
- [本次调试日志](docs/DEEPSEEK_V41_DEBUG_LOG_2026-10-18.md)
- [本次清理日志](docs/CLEANUP_LOG_2026-10-18.md)
- [当前交接状态](PROGRESS.md)
- [历史实验概览](docs/experiments.md)与[历史结果归档](docs/history/README.md)

## 代码结构

- `main.py`：当前问答主流程；HyDE 和查询改写保留开关，默认关闭。
- `src/pdf_loader.py`、`chunking_semantic.py`、`chunking_recursive.py`：解析和分块。
- `src/embedding.py`、`vector_store.py`、`chunk_storage.py`：向量与持久化。
- `src/*retriever.py`、`reranker.py`：检索、融合与重排。
- `src/query_decomposer.py`、`query_rewriter.py`、`hyde.py`：问题分解与可选查询增强。
- `src/numeric_evidence.py`、`grounded_evidence.py`：保守数值解析、有限主体归属及原文证据视图。
- `src/api_llm.py`、`llm.py`、`citation_validation.py`：API 调用、共享入口与引用结构检查。
- `evaluation/`：四个必要评估/核对入口、六题材料和当前运行结果；旧诊断与测试脚本已清理。

Single-Agent、LangGraph 与演示界面尚未实现。当前使用规则化证据整理，不能等同于通用语义验证。
