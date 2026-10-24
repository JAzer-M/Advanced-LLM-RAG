# macOS 下载版构建

本构建仅面向 Apple Silicon；需要在 Mac 的独立 Python 3.11 环境执行。运行源码仍可使用原来的 `.venv` 和 `webui/start.command`。

```bash
python3.11 -m venv /tmp/paperlens-build-venv
/tmp/paperlens-build-venv/bin/python -m pip install -r requirements-build-macos.txt
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
/tmp/paperlens-build-venv/bin/python packaging/macos/build.py
```

输出为 `dist/PaperLens.app`、`releases/PaperLens-0.1.0-macos-arm64-preview.zip` 和 SHA-256 校验文件。构建会替换上述生成目录中的同名产物；源码、用户库和配置不在收集清单中。第三方许可汇总放在应用的资源目录中。

应用自带 Python 与依赖；用户不需要安装 Python。首次启动打开本机网页 `http://127.0.0.1:8849`，点击准备检索模型，下载固定版本的 MiniLM 与 BGE 文件（约 1.61 GB），下载后在本机加载校验。中断后可重试，已完成文件复用。模型准备不调用生成 API。

用户数据默认保存在 `~/Library/Application Support/PaperLens/`：`models/` 为检索模型，`api.local.json` 为私有服务配置，`data/` 为上传及配对知识库，`logs/` 为运行记录。更新应用前备份整个数据目录；替换 `.app` 不会迁移作者的资料。`PAPERLENS_DATA_DIR` 仅用于隔离验收或明确选择其他目录。

网页“退出”按钮在任务完成后关闭本机服务。重复启动同一数据目录时打开已有服务；8849 被其他服务或另一个数据目录占用时，打开本机错误页并给出日志位置。

当前脚本生成 ad-hoc 签名的预览包。Developer ID 签名、公证、在另一台 Mac 验收及 GitHub Release 为正式发布步骤，不能由本地构建成功代替。请勿把本机配置、权重缓存或用户论文添加到发布清单。

参考：[PyInstaller 运行方式](https://pyinstaller.org/en/stable/operating-mode.html)、[冻结程序路径约定](https://pyinstaller.org/en/stable/runtime-information.html)、[Apple Developer ID](https://developer.apple.com/developer-id/)。
