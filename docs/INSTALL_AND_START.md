# PaperLens 安装与首次启动

更新：2026-10-24。当前提供源码安装流程，运行在用户自己的电脑上，网页地址为 `http://127.0.0.1:8849`。

已实测：macOS Apple Silicon、Python 3.11.9、全新虚拟环境、在线安装依赖、从空网页论文库导入 PDF 并问答。本轮复用了本机 Hugging Face 模型缓存和已配置的模型网关；源码安装这一轮没有覆盖权重冷下载、Windows 或可执行安装包。[验收记录](maintenance/installation_ui_acceptance_20261024/report.md)（Mac 预览包另行验收了权重冷下载，见[下载包验收](maintenance/macos_package_20261024/report.md)。）

## 1. 安装依赖

先准备 Python 3.11，将源码放到自己有写入权限的目录，再在项目根目录执行。不要复制其他机器的 `.venv`。

```bash
python3.11 --version
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-macos-py311.lock.txt
.venv/bin/python -m pip check
```

`requirements-macos-py311.lock.txt` 固定本轮 Mac 验收使用的包版本；`requirements.txt` 保留原来的未固定依赖列表。这个版本快照不是跨平台兼容承诺。

## 2. 准备本地检索模型

首次使用需要准备多语言 MiniLM 和 BGE 重排模型。下面的命令会下载缺少的文件，已有缓存则复用；需要能访问 Hugging Face。它不调用问答 API。

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 \
.venv/bin/python -B - <<'PY'
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
from src.embedding import load_embedding_model
from sentence_transformers import CrossEncoder
load_embedding_model()
CrossEncoder('BAAI/bge-reranker-base', device='cpu')
print('本地检索模型准备完成')
PY
```

网页的入库与问答进程使用离线模式加载这些本地模型，避免每次处理论文时重新下载。模型准备失败时先解决下载问题；已有知识库和上传原件不会因准备失败被替换。本轮验证了独立虚拟环境能离线加载已有缓存，没有重新下载全部权重。

## 3. 启动与配置模型服务

Mac 在项目根目录执行，或双击这个启动文件：

```bash
./webui/start.command
```

网页自动打开后保持启动终端运行。重复启动会打开已有服务；在启动终端按 `Ctrl+C` 会停止本次服务。也可以直接运行 `.venv/bin/python -B -u webui/server.py`，再手动打开本机网页。若下载工具没有保留可执行权限，可以使用 `zsh webui/start.command`。

在顶栏“模型”中填写自己的兼容 Chat Completions 服务地址、API Key 和模型 ID。地址应包括服务要求的 `/v1` 前缀；本地网关必须先运行。可以获取 `/models` 列表，也可直接填写模型名。保存设置不生成回答。

密钥留在本机 `api.local.json`，不回填网页、不写入 Git。相同地址留空保留已存密钥；换地址需要填写对应密钥。

需要额外调用参数时，可在首次配置前复制 `api.example.json` 为 `api.local.json` 并编辑；已有配置直接编辑原文件。示例中的 `thinking` 等扩展字段需要模型服务支持。本轮真实问答使用已有网关及 `cn:glm-5.3`，保留 `thinking=disabled`、`temperature=0`、`max_tokens=4096`；没有替所有服务和模型验证兼容性。

## 4. 上传自己的第一篇 PDF

新安装没有本机八篇实验版本时，网页显示空论文库和“添加论文”入口；不需要迁移作者的知识库，也不会自动把仓库里的 PDF 加进网页论文库。已有工作区继续使用自己的网页指针或现存八篇基线。

1. 打开“论文库”，选择 PDF；每批 1～5 篇、总计不超过 20 MB、每篇不超过 200 页。
2. 根据实际版式选择“双栏”，点击“添加并入库”。
3. 等待正文提取、基础清理、语义分段和本地向量编码完成，再开始提问。

入库不调用生成 API。首篇论文创建独立知识库，后续上传追加到新版本；内容重复跳过。全批成功、索引和分块校验通过后才切换网页指针，失败保留原库。当前清理不包含 OCR，也不保证完整恢复表格、公式或任意复杂排版。

论文原件、任务和网页指针在 `data/webui/`；配对索引、分块、manifest 在 `data/processed/versions/`。问答记录在 `logs/webui/`。备份时一并保留这些目录；它们不会随普通 Git 克隆复制。

## 5. 最小验收

以自己上传的论文为依据，选 RAG 并问一个明确、可在原文核对的问题。此次问答会调用用户配置的模型服务。PDF 解析和向量化在本机进行；问题和检索出的原文段落会发给该模型服务。

确认以下行为：

- Enter 发送，Shift+Enter 换行，中文输入法选词的 Enter 不发送。
- 问答过程中刷新接续同一任务，不重复提交。
- 回答里的编号可展开对应原文，并显示来源和页码。
- 重复上传不重复入库；无正文 PDF 显示失败，原知识库仍可用。
- 重启服务后导入库仍保留；旧问答任务显示不能接续，不自动重新运行。原运行文件保留。

本轮实际以新导入 VGG 验收：1 篇 / 160 段；步长与填充问题回答正确，引用第 2 页，20.32 秒、2 次请求、3,098 token。它是安装闭环与已知题检查，不是独立质量评测。

## 6. 常见启动边界

- 页面打不开：查看启动终端是否仍运行；若 8849 已被其他程序占用，先处理占用再启动。
- 页面可打开但无法入库：查看导入状态和对应 `data/webui/imports/<id>/console.log`；先确认本地模型准备完成，PDF 有可提取正文。
- 页面可打开但问答失败：核对模型网关、地址、模型和调用参数；在 `logs/webui/` 查看本次记录。没有自动重试。
- 需要在其他电脑继续：按本文重新安装环境；知识库须成套复制后校验，私有配置单独设置。

面向普通用户的 GitHub 下载包方案见 [本机分发方案](LOCAL_DISTRIBUTION.md)；Mac 预览包的构建方法见 [packaging/macos](../packaging/macos/README.md)，验收见 [下载包验收](maintenance/macos_package_20261024/report.md)。
