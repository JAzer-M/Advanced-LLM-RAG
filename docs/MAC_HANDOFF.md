# Mac 接续开发说明

**本页定位：10月18日迁移记录。** 截至2026-10-24，Mac本机已运行PaperLens、三模式和PDF入库，配置/模型/库及测试以[当前PROGRESS](../PROGRESS.md)为准。下文保留当时迁移命令、旧模型示例和权限核对结果；本轮未重新克隆或将它标为当前完整安装验收。

日期：2026-10-18。目标仓库：`JAzer-M/Advanced-LLM-RAG`，本次已核实为私有仓库，默认分支 `main`。本文件说明同步范围和迁移步骤；没有声称已在 Mac 实际运行。

## 同步范围

- 当前源码、依赖清单、PROGRESS、实验报告、原始结果和历史实验归档。
- 三篇原始 PDF，以及 Fixed / Recursive / Semantic 三组成对 chunks JSON + FAISS 索引，共九个数据文件。生产问答使用 Semantic 的 378 条、384 维数据；旧两组用于历史对照，Fixed 构建源码已清理。
- [数据校验清单](../data/migration_manifest.json)记录九个文件的大小和 SHA-256；`.gitattributes` 禁止 Git 自动改写这些数据文件的换行，保持跨平台字节一致。
- `.gitignore` 只对这九个已有数据文件放行，其他新增数据默认仍忽略。此安排用于当前私有仓库的个人跨机迁移；将来公开项目时须重新处理论文全文及衍生文本的分发许可。

不上传 `api.local.json`、环境变量、`.venv`、IDE 设置、模型权重与 Hugging Face 缓存。文档中指向 Windows 仓库外的清理快照、临时实验驱动和辅助摸底文件也不会由 Git 同步；现有原始结果可阅读，原临时驱动不能直接在 Mac 按该绝对路径重跑。正常问答与保留的评估入口不依赖它们。

## 1. 获取代码，保留 Mac 原有目录

旧 Mac 工作树可能有未提交修改或被忽略的旧索引。建议先克隆到新目录，核验后再决定是否替换原目录，不直接执行 reset/clean。

```bash
cd ~/Desktop
git clone https://github.com/JAzer-M/Advanced-LLM-RAG.git Advanced-LLM-RAG-mac
cd Advanced-LLM-RAG-mac
git log -1 --oneline
git status --short
```

私有仓库需要你自己的 GitHub 登录；不要把 GitHub Token 写入 clone URL。若该目标目录已经存在，另选新目录名。要复用原项目时，先检查修改并保存，再按实际分支情况执行 `git pull --ff-only`；不要强行覆盖本地文件。

## 2. Python 环境

原 Mac 项目历史 Python 为 3.11.9，可复用可用的 Python 3.11 解释器，但虚拟环境需在 Mac 本机创建：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

在 PyCharm 中选择这个新目录下 `.venv/bin/python`。依赖尚未完整锁版本，以上是迁移步骤，不是 Mac 安装已验证记录；若安装失败，保留首个具体错误再处理，不安装 Windows 的 CUDA wheel。

## 3. 检查数据快照

在项目根目录执行以下标准库检查，不加载 LLM、不调用 API：

```bash
python - <<'PY'
import hashlib
import json
from pathlib import Path

manifest = json.loads(Path('data/migration_manifest.json').read_text())
for item in manifest['files']:
    path = Path(item['path'])
    assert path.is_file(), f'Missing: {path}'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
print('Data snapshot verified:', len(manifest['files']), 'files')
PY
```

预期九个文件通过。然后用已安装的 FAISS 检查生产索引：

```bash
python - <<'PY'
import json
import faiss

chunks = json.load(open('data/processed/chunks_semantic.json', encoding='utf-8'))
index = faiss.read_index('data/processed/faiss_semantic.index')
assert index.ntotal == len(chunks) == 378
assert index.d == 384
print(type(index).__name__, index.ntotal, index.d)
PY
```

首次迁移优先核验已有快照。当前 Semantic 构建器已改为生成独立版本，默认不切换；版本、校验与回退步骤见 [知识库版本操作](KNOWLEDGE_BASE_VERSIONS.md)。版本目录与当前指针默认被 Git 忽略，迁移时另行核对。

## 4. API 与检索模型

若新目录尚无本地配置：

```bash
test -f api.local.json || cp api.example.json api.local.json
```

在本地填写可用的 `base_url` 与 Key。`127.0.0.1:7863` 在 Mac 上指 Mac，不会自动连到 Windows 的代理；需要在 Mac 启动对应代理，或使用可访问的服务地址。现有模型路由 `cn:deepseek-v4.1-flash` 属代理配置，不保证能直接用于其他供应商地址。Key 不进入 Git。

Embedding 和 BGE 重排仍在 CPU 运行，无需 Qwen 权重或 NVIDIA GPU。Mac 首次运行若无缓存，需要下载这两个模型：

- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `BAAI/bge-reranker-base`

缓存尚未准备时不要开启 `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`。Windows 上的缓存不会随 Git 自动出现。

## 5. 验证与下一步

```bash
python main.py
```

先用 Transformer 位置编码题验证检索、引用来源和 API 回答。随后如需复核 Gold 映射：

```bash
python -m evaluation.check_evidence
```

确认迁移成功后从 [PROGRESS](../PROGRESS.md) 的 P0 批量导入阶段继续。模型调用评估会产生实际 API 请求，不因换电脑就重复全部历史实验；Mac 与 Windows 的耗时不能直接作为算法改进对照。
