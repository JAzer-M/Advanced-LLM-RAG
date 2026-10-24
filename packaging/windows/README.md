# Windows 下载版构建

面向 Windows 10/11 x64。构建必须在 Windows 上进行（PyInstaller 不能跨平台打包），推荐直接用 GitHub Actions：

1. 打开仓库的 **Actions → build-windows → Run workflow**（推送 `v*` 标签时也会自动运行）。
2. 运行结束后，在该次运行页面底部的 **Artifacts** 下载 `PaperLens-windows-x64-preview`（需登录 GitHub）。
3. 解压得到 `PaperLens-<版本>-windows-x64-preview.zip` 及其 `.sha256`，这就是可发布的安装包。

也可以在本机 Windows 的独立 Python 3.11 环境中构建：

```powershell
py -3.11 -m venv C:\paperlens-build-venv
C:\paperlens-build-venv\Scripts\python.exe -m pip install -r requirements-build-windows.txt
C:\paperlens-build-venv\Scripts\python.exe packaging\windows\build.py
```

输出为 `dist\windows\PaperLens\`（含 `PaperLens.exe`）和 `releases\PaperLens-<版本>-windows-x64-preview.zip`。构建脚本会在源码目录之外运行一次冻结自检，并确认 UTF-8 模式已启用，否则不生成 ZIP。

用户解压后双击 `PaperLens\PaperLens.exe`：程序在后台启动本机服务并打开 `http://127.0.0.1:8849`，没有控制台窗口；用网页右上角的「退出」关闭服务。首次使用在网页中下载检索模型（约 1.61 GB）。数据保存在 `%LOCALAPPDATA%\PaperLens\`（`models/`、`api.local.json`、`data/`、`logs/`），替换程序文件夹不影响数据。

程序未做代码签名，首次运行可能出现 SmartScreen 提示，需点“更多信息 → 仍要运行”。
