# QASPER 评测：交接与后续步骤

写于 2026-10-24 21:40（Asia/Shanghai），供新对话或其他助手接手。评测协议见同目录 `protocol.md`（运行前冻结，不要修改）。

## 当前状态

- 评测脚本：`evaluation/qasper_eval.py`，6 个步骤均可断点续跑，已完成的结果不会重算，失败不自动重试。
- 第一次 `prepare` 因 macOS Python 缺根证书失败（`CERTIFICATE_VERIFY_FAILED`），已改为使用 certifi（提交 `b38f7d0`），尚未重跑成功。
- 尚未抽样、建库或调用任何模型 API。

## 一次跑完（在 Mac 终端，项目根目录）

```bash
cd ~/Desktop/Advanced-LLM-RAG
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
for step in prepare build run score judge report; do
  caffeinate -i .venv/bin/python evaluation/qasper_eval.py $step || { echo "停在 $step"; break; }
done 2>&1 | tee evaluation/results/qasper_20261024/console.log
```

- `prepare`：下载 QASPER v0.3 测试集，按种子 20261024 抽约 50 题，下载对应 arXiv PDF 到 `data/raw/qasper-test50-20261024/`（本机）。
- `build`：建独立知识库 `qasper-test50-20261024`，不切换当前库、不影响网页库。
- `run`：三种模式各跑一遍（约 150 次运行，预计 1～1.5 小时，真实调用模型 API）。
- `score`：官方口径 Answer F1 / Evidence F1（近似段落对齐）/ 检索命中 / 拒答；并用官方 `qasper_evaluator.py` 交叉核对。
- `judge`：同一模型服务做大模型判分（约 150 次请求）。
- `report`：生成 `summary.json`。

中途中断：重新执行同一段命令即可，从断点继续。

## 跑完后要做的分析（给接手的助手）

1. 读 `summary.json`、`scores/official_evaluator.json`（核对官方脚本的 Answer F1 是否与本脚本一致；不一致要查原因，不要改协议）、`console.log`。
2. 抽查 `scores/per_question.json` 中 F1 很低但判分为 correct 的题，确认是"回答偏长导致 F1 低"还是判分偏宽。
3. 抽查 `prediction_kind=declined` 的题，确认拒答识别规则没有明显误判。
4. 写 `report.md`：三种模式的 Answer F1、按答案类型的 F1、Evidence F1、检索命中率、拒答、判分分布、请求数/token/耗时；如实写协议中的结论边界（小样本、同模型判分、PDF 版本差异、近似对齐）。
5. 更新 README「关键结果」加入 QASPER 表格，更新 `docs/PROJECT_METRICS.md` 与 `PROGRESS.md`；README「已知局限」里“没有独立新题评测”一条改为实际情况。
6. 提交（作者 `JAzer-M <d1599356723@163.com>`），由用户推送。

## 其他待办（与评测无关）

- 发布 `v0.2.0` Release（Windows 安装包已通过 GitHub Actions `build-windows` 构建并由用户在 Windows 上验收；Artifact 保留 14 天）。
- 可选：Mac 重新打 0.2.0 包；补 GitHub 个人主页资料。
