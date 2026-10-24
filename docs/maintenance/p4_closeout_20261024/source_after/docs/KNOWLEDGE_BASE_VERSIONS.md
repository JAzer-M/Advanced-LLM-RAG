# 知识库版本：构建、切换与回退

当前已实现：每个版本独立保存索引、分块与清单；构建不会覆盖旧库，也不会默认切换正在使用的库。问答、答案评估、检索评估和 Gold 核对使用同一个版本读取模块。

截至2026-10-24，本机保留以下版本；日期实验中的规模按当时版本理解：

| 版本名 | 来源 | 分块数 / 向量维度 |
| --- | --- | --- |
| `legacy-3papers-20261019` | 原始 Semantic 索引与 JSON 的逐字节快照 | 378 / 384 |
| `semantic-mac-20261019` | Mac 从原三篇 PDF 重新解析、分块、编码并构建 | 378 / 384 |
| `arxiv-pilot-5-20261019` | 五篇先导论文 | 1019 / 384 |
| `all-papers-8-20261020` | 八篇实验基线；Agent/Auto未指定版本时使用 | 1397 / 384 |
| `webui-72bf8b69e9cf45f28135637e5ead075c` | 当前网页九篇库，含Mamba | 1767 / 384 |

全局激活仍为 `semantic-mac-20261019`；RAG未指定版本时读它。Agent/Auto默认八篇，但三模式均可显式传入合法`kb_version`，工具资源必须与问题版本一致。网页另从`data/webui/library.json`读版本，当前为上表九篇库，三模式在提交时固定同一网页版本。[当前状态快照](maintenance/p4_closeout_20261024/current_state.json)

网页指针、上传PDF和新版本不进入Git。本地提交后在另一台机器克隆，不会自动拥有当前九篇库；迁移须另行复制成对索引/chunks/manifest并校验。首次导入标题回退前的网页版本也保留。[PDF入库与去重/失败边界](WEBUI_PDF_IMPORT_2026-10-24.md)。10月19日原三篇版本的验证记录见[历史操作结果](../evaluation/results/kb_versions_20261019/verification.json)。

## 文件如何组织

```text
data/processed/
  faiss_semantic.index          原始库，保留
  chunks_semantic.json          原始分块，保留
  active_kb.json                只记录当前版本名和 manifest 哈希
  versions/
    legacy-3papers-20261019/
      faiss.index
      chunks.json
      manifest.json
    semantic-mac-20261019/
      faiss.index
      chunks.json
      manifest.json
```

索引像查找目录，chunks 像正文。切换只改变 `active_kb.json`，让程序一次选择完整的一套目录和正文。每份 manifest 记录索引/分块 SHA-256、数量、维度和创建时间；真实构建还记录分块参数、Embedding、PDF 哈希等来源信息。快照不伪称重新执行了向量化。

## 查看、校验和回退

在项目根目录的 Mac 终端运行，使用项目的 `.venv`：

```bash
# 查看当前版本和已发布版本
.venv/bin/python -m src.knowledge_base list

# 校验当前版本，也可在 validate 后指定其他版本名
.venv/bin/python -m src.knowledge_base validate

# 回退到保留的旧库
.venv/bin/python -m src.knowledge_base activate legacy-3papers-20261019

# 再切回本次重建的新库
.venv/bin/python -m src.knowledge_base activate semantic-mac-20261019
```

`activate`只改变全局指针，影响未显式指定版本的RAG；不改变默认八篇的Agent/Auto或网页指针。CLI默认auto，若要使用全局激活库需显式选`--mode rag`。启动信息显示实际版本；已开始的问答及整轮答案评估固定其加载版本，避免中途混用。

## 以后构建一个新版本

为每次构建使用新的版本名。重复的名字会报错，不覆盖已有版本。

```bash
# 构建完成后仅发布，当前库继续使用
.venv/bin/python build_semantic_index.py --version semantic-v2

# 校验新库
.venv/bin/python -m src.knowledge_base validate semantic-v2

# 校验通过后切换
.venv/bin/python -m src.knowledge_base activate semantic-v2
```

Mac 构建沿用[单线程与离线运行条件](MAC_AUDIT_2026-10-19.md)。10月19日构建进程设置了OMP/OpenBLAS/MKL/Accelerate线程上限、关闭Tokenizers并行，并将PyTorch intra-op/inter-op设为1；这些不是全局或PyCharm持久配置。默认线程批量崩溃的根因仍未定位。

`--raw-dir` 可指定另一份 PDF 目录，默认为现有 `data/raw/`。如希望构建成功后立即切换，可额外加 `--activate`；校验失败时不会执行切换。`build_recursive_index.py` 仍是历史 Recursive 对照入口，不参与这里的 Semantic 版本选择。

原始库以后若需要再次保存为独立版本，可运行 `python -m src.knowledge_base snapshot 新的版本名`，复制的是根目录原始 Semantic 文件，当前选择不会改变。

## 评估与证据定位

```bash
# 仅核对指定版本中的 Gold 引文，不调用生成 API
.venv/bin/python -m evaluation.check_evidence --kb-version semantic-mac-20261019

# 指定版本的答案评估会调用生成 API；结果须写新目录
.venv/bin/python -m evaluation.run_answer_evaluation --kb-version semantic-mac-20261019 --question-id q2 --output-dir evaluation/results/my_version_run
```

检索评价也支持 `--kb-version`。不指定时使用当前版本；对历史原始文件可显式指定保留名 `legacy`，无须改变当前指针。已有答案回放直接使用保存的上下文，绑定回放输入文件哈希，不依赖当前知识库，也不同时接受 `--kb-version`。

回答 JSON 保存版本名、manifest 和两个文件哈希，以及选中的 chunk ID。同一个数字 ID 只在相应版本内解释；本次尚未实现跨版本稳定的文档/片段标识。

## 失败时会怎样

- 构建先写临时目录，完整校验后才发布版本。普通异常会清理临时目录；进程被强制结束时可能留下隐藏的临时目录，但不会成为可用版本。
- 切换前检查文件哈希、向量/分块数量、维度和 chunk ID 与行号的对应关系；同数量的分块被替换也会被哈希校验拦截。
- 当前版本指针通过同目录临时文件加 `os.replace` 原子替换。切换失败时保留旧指针；回退使用相同的 activate 操作。
- 已有指针或已激活数据损坏时明确报错，避免静默改用另一份库。首次没有指针的旧项目仍可读取原始 Semantic 文件。

现有 Git 忽略规则会忽略 `versions/` 与 `active_kb.json`，本机版本和选择不会自动同步到 Windows。迁移时另行复制所需版本目录并校验，之后在目标机器执行 activate；原始九个迁移数据文件仍按现有 Git 规则保留。
