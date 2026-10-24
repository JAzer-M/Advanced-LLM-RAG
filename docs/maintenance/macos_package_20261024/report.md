# macOS 下载版（预览包）构建与验收

日期：2026-10-24（Asia/Shanghai）。构建与验收由 Codex 执行；Codex 在写报告前达到额度上限，本报告由 Claude 依据本目录保存的原始记录整理，没有重新运行验收，也没有新增模型调用。

## 结论与范围

在 macOS 26.6.2 / Apple Silicon / Python 3.11.9 下，以本地提交 `5a4cd85` 叠加安装验收与打包改动，用 PyInstaller 生成自带 Python 与依赖的 `dist/PaperLens.app`，并压缩为预览包：

- `releases/PaperLens-0.1.0-macos-arm64-preview.zip`，276,390,289 字节
- SHA-256 `c18ae800b78a1148c3f76b6305228acb8f3fb13a01fc8b6a7e642eb5938409ff`（与同目录 `.sha256` 文件一致，2026-10-24 复核）

验收使用解压后的应用、空数据目录与空 Hugging Face 缓存（[冷启动基线](cold_baseline.json)），完成“首次启动 → 下载检索模型（含中断与续传）→ 配置模型 → 上传 PDF → RAG/Agent/Auto 问答 → 退出 → 重启”。

不在本轮结论内：Developer ID 签名与公证（当前为 ad-hoc 签名，其他 Mac 首次打开会被 Gatekeeper 拦截）、另一台 Mac、Intel Mac、Windows、GitHub Release 发布。问答服务复用本机已有网关配置。

[构建环境](environment.json) · [构建说明](../../../packaging/macos/README.md) · [分发方案](../../LOCAL_DISTRIBUTION.md)

## 代码改动

| 改动 | 说明 |
| --- | --- |
| 用户数据目录 | 新增 `src/runtime_paths.py`；冻结程序默认使用 `~/Library/Application Support/PaperLens/`（`models/`、`api.local.json`、`data/`、`logs/`），`PAPERLENS_DATA_DIR` 可覆盖。源码运行保持原路径。[默认路径自检](frozen_default_path_check.txt) |
| 后台子进程 | 冻结程序以自身可执行文件启动入库/问答 worker，不再依赖项目内 Python 解释器 |
| 首次模型准备 | 新增 `src/model_assets.py` 与 `/api/setup`；固定版本 MiniLM（`e8f8c21`）与 BGE（`2cfc18c`），共 1,614,137,940 字节；显示进度，中断后复用已完成文件，准备完成前禁止上传 |
| 应用入口 | 新增 `paperlens_app.py`：启动本机 8849 服务并打开浏览器；同一数据目录重复启动时打开已有服务 |
| 网页 | 首次模型准备提示、空库提示、“退出”按钮（有任务运行时拒绝退出）。暖白朱橙设计与样式文件未改动 |
| 构建 | `packaging/macos/`（spec、build.py）、`requirements-build-macos.txt`；`build/`、`dist/`、`releases/` 已加入 `.gitignore` |

测试：先写失败用例再修复（[runtime 红](runtime_red.txt)/[绿](runtime_green.txt)、[模型准备 红](model_assets_red.txt)/[绿](model_assets_green.txt)、[setup HTTP 红](setup_http_red.txt)/[绿](model_assets_http_green.txt)）。最终后端 345 项、网页 42 项通过（[后端](backend_tests_green.txt)、[网页](webui_tests.txt)）。一次 runtime 测试因 macOS `/var` → `/private/var` 符号链接比较失败，已保留记录（[失败](runtime_fixture_path_failure.txt)）。

## 构建过程中的失败

| 尝试 | 结果 |
| --- | --- |
| 第 1 次 | PyInstaller 缓存目录 `~/Library/Application Support/pyinstaller` 无写权限而中止；改用专用构建目录。[记录](build_attempt_1.txt) |
| 第 2 次 | 构建成功，但冻结自检失败：缺少 torchvision 本地算子库，导致 transformers 无法导入。[构建](build_attempt_2.txt)、[自检失败](frozen_self_check_1.txt) |
| 第 3 次 | 补入 torchvision 本地库后重建；自检通过，Python、torch 2.14.1、FAISS 1.15.1、PDF、transformers 5.19.0、sentence-transformers 6.1.0 均可加载。[构建](build_attempt_3.txt)、[自检](frozen_self_check_2.txt) |

## 下载版实际操作

| 操作 | 结果 |
| --- | --- |
| 首次启动 | 0 篇 / 0 段、未配置模型；上传被禁用，显示模型准备入口。[元数据](frozen_initial_meta.json)、[截图](first_launch.png) |
| 中断下载 | 下载到约 292 MB 时中断，页面显示“重新准备模型”，保留未完成文件。[状态](download_interrupted.json)、[截图](download_interrupted.png) |
| 重启后重试 | 续传推进；刷新页面仍是同一下载进程，没有另起下载。[续传](download_resumed.json)、[刷新后](download_after_refresh.json) |
| 模型设置与重复启动 | 获取模型列表并保存；配置文件权限 0600；重复启动复用服务，下载进程不变。[记录](config_and_duplicate_launch.json)、[截图](config_saved.png) |
| 模型就绪 | 两个模型下载完成、在冻结程序中加载校验，上传入口启用。[记录](models_ready.json)、[截图](models_ready.png) |
| 首篇入库 | VGG：1 篇 / 160 段 / 384 维，完整标题保留。[记录](first_import_and_rag_start.json)、[截图](pdf_imported.png) |
| 重复上传 | 跳过，库不变。[截图](duplicate_skipped.png) |
| 无正文 PDF | 失败提示“扫描件暂不支持OCR”，当前库不切换。[记录](invalid_imports_and_source_identity.json)、[截图](blank_pdf_failed.png) |
| Agent 运行中刷新 | 接续同一任务，没有重复提交。[记录](qa_after_agent_refresh.json)、[截图](agent_refresh_running.png) |
| 运行中点退出 | 被拒绝，提示等待任务完成。[截图](quit_blocked_while_busy.png) |
| 退出 | 8849 端口关闭。[记录](before_restart.json)、[截图](app_stopped.png) |
| 重启 | 模型、配置、160 段库保留；旧任务 404，没有自动重发。[记录](restart_verification.json)、[截图](restart_preserves_data.png) |

两次 Agent/Auto 运行的 29 个打包源码文件哈希与仓库源码一致。[核对](invalid_imports_and_source_identity.json)

## 真实问答及成本

同一已知题“VGG 的 3×3 卷积层步长和填充分别是多少？”，模型 `cn:glm-5.3`，联网关闭：

| 模式 | 状态 | 耗时 | 请求 | token |
| --- | --- | --- | --- | --- |
| RAG | completed / not_reviewed | 19.16 秒 | 2 | 3,108 |
| Agent | completed / review_passed | 32.91 秒 | 5 | 10,955 |
| Auto | completed（RAG 草稿直答）/ not_reviewed | 18.84 秒 | 2 | 3,105 |

合计 9 次请求、17,168 token，0 失败、0 自动重试；另有 1 次网关 `/models` 请求。三者均回答步长 1 像素、填充 1 像素，引用 VGG 第 2 页。这是安装验收，不是独立质量评测。[汇总](live_run_summary.json)、[运行记录](live_runs/)、截图：[RAG](frozen_rag_citation.png)、[Agent](frozen_agent_answer.png)、[Auto](frozen_auto_answer.png)

## 隐私与数据保护

- 分发包扫描 6,396 个文件：没有私有配置、论文、知识库、实验日志或模型权重，没有与已配置密钥匹配的文件。[扫描结果](artifact_privacy_scan.json)
- 开始前对 5,198 份既有文件留哈希。[基线](baseline_hashes.json)；原九篇网页库、实验记录与私有配置未改动。
- 验收数据与模型缓存放在 `/private/tmp/paperlens-package-acceptance-20261024/`，属临时目录；本目录另存了测试知识库和导入记录。

## 收尾状态与遗留

- Codex 在关闭验收浏览器页面后达到额度上限，未写本报告、未更新文档、未提交。本报告与文档更新为 Claude 补写。
- 预览包构建之后，源码中仅改动了一处网页断线提示文案（不再只提“终端窗口”，兼顾应用包），因此现有 zip 仍是旧文案；下次重建时带上即可，不影响已验证功能。
- 正式发布前仍需：Developer ID 签名与公证、在另一台未装开发环境的 Mac 上验收、决定是否公开验收目录中的测试知识库（含 VGG 论文分段原文）、创建 GitHub Release。Windows 需单独构建与验收。
