#!/bin/zsh
# Finder双击后在独立终端运行；关闭终端即停止，不设置开机自启。
cd -- "${0:A:h}/.." || exit 1
if curl --silent --fail --max-time 2 http://127.0.0.1:8848/api/meta > /dev/null; then
    open http://127.0.0.1:8848
    exit 0
fi
exec .venv/bin/python -u ui_prototype/app.py
