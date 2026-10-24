# PaperLens 本机下载与分发方案

更新：2026-10-24。用户希望从 GitHub 下载、在本机打开网页、上传自己的论文并自动处理。这个方向可行；源码安装闭环已验收，并已生成经过实测的 macOS Apple Silicon 预览包（ad-hoc 签名，尚未公证或发布）。

## 用户流程

GitHub 下载程序 → 本机启动 → 浏览器打开 `127.0.0.1:8849` → 准备本地检索模型并配置问答服务 → 上传 PDF → 自动解析、基础清理、分段和建库 → 带引用问答。

下载的是程序；端口是程序运行时在本机提供网页的位置。GitHub 负责下载分发，论文库由各用户自己的本机服务保存，不需要把网页服务部署到 GitHub。GitHub Releases 可附发布说明和二进制下载文件，见 [GitHub 官方说明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。

## 当前已经具备

- 本机 HTTP 服务、网页、三模式问答、模型设置及引用联动。
- 新安装从空网页论文库开始，上传首篇 PDF 自动创建配对知识库；无需作者的实验版本。
- PDF 提取、基础清理、语义分块、向量化、重复跳过、成功后原子切换和失败保留。
- Mac 启动器、新虚拟环境安装记录、首次使用说明及实际网页验收。
- Mac 预览下载包：自带 Python 与依赖；数据保存在 `~/Library/Application Support/PaperLens/`；首次启动下载约 1.61 GB 固定版本检索模型，可中断续传；网页可退出服务。[构建说明](../packaging/macos/README.md) · [下载包验收](maintenance/macos_package_20261024/report.md)

PDF 原件和向量库在本机；使用远程问答模型时，问题与检索到的原文会发给用户配置的模型服务。当前没有 OCR、完整表格和公式恢复、网页删除或通用文档格式支持。

## 下载包下一步

Mac 预览包已完成“解压 → 启动 → 模型准备 → 配置 → 上传 → 问答 → 退出 → 重启”验收，包内不含作者的密钥、论文库、实验日志或模型权重。

正式发布前还需：Developer ID 签名与公证（否则用户首次需右键打开）；在另一台无开发环境的 Mac 上验收；创建 GitHub Release 并附 SHA-256。Windows：源码方式已在真实电脑上验收；安装包由 GitHub Actions 的 `build-windows` 工作流在 Windows 构建机上打包并自检（见 [packaging/windows](../packaging/windows/README.md)），2026-10-24 首次构建的安装包已在真实 Windows 电脑上验收通过。

[当前源码安装说明](INSTALL_AND_START.md) · [本轮验收记录](maintenance/installation_ui_acceptance_20261024/report.md)
