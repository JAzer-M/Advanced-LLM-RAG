# ui_prototype（只保留后端辅助函数）

2026-10-24：旧版 8848 原型的页面文件（index.html、style.css、app.js）和 start.command 已删除，网页统一使用 `webui/`（PaperLens，端口 8849）。

保留 `app.py`，因为 `webui/server.py` 仍从这里导入四个函数：`public_result`（把运行结果转换成页面可以展示的公开字段）、`example_result`、`metadata` 和 `EXAMPLES`（已保存的回答）。`app.py` 自带的 8848 服务入口已没有页面可用，不要再单独启动。

以后如果要彻底移除这个目录，先把上述函数移到 `webui/` 里，再删除本目录。删除前的完整版本保存在 git 提交 `00d7f6e`。
