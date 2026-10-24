#!/bin/zsh
# 桌面可放本文件的符号链接；:A会解析链接，仍从项目根目录启动。
cd -- "${0:A:h}/.." || exit 1
paperlens_url='http://127.0.0.1:8849'
if curl --noproxy '*' --silent --fail --max-time 2 "$paperlens_url/api/meta" > /dev/null; then
    print -r -- "PaperLens 已在运行，正在打开 $paperlens_url"
    open "$paperlens_url"
    exit 0
fi
if [[ ! -x .venv/bin/python ]]; then
    print -r -- '找不到项目的 Python 环境，请检查 .venv。'
    read 'reply?按回车关闭…'
    exit 1
fi
print -r -- '正在启动 PaperLens，网页将自动打开。使用期间请保持此终端窗口打开。'
.venv/bin/python -B -u webui/server.py &
paperlens_pid=$!
# 终端关闭或按Ctrl+C时清理本次启动的服务，不影响已存在的服务。
trap 'kill "$paperlens_pid" 2>/dev/null' EXIT
trap 'exit 0' INT TERM HUP
for attempt in {1..40}; do
    if curl --noproxy '*' --silent --fail --max-time 1 "$paperlens_url/api/meta" > /dev/null; then
        open "$paperlens_url"
        wait "$paperlens_pid"
        exit $?
    fi
    kill -0 "$paperlens_pid" 2>/dev/null || break
    sleep 0.25
done
print -r -- '服务未能就绪，请查看上方错误信息。'
read 'reply?按回车关闭…'
exit 1
