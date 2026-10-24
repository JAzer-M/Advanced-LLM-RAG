# QASPER评测交接：执行已完成

更新：2026-10-24（Asia/Shanghai）。先读[完整报告](report.md)、[根汇总](summary.json)、[助手抽查](manual_review.md)。修改前的交接文件及其他文档保存在[source_before](source_before/)。

## 当前已完成

- 15篇52题、15份PDF与独立库1612段已存在且哈希通过；全局激活库和网页指针未切换。
- 原GLM第二条遇429；原DeepSeek未绑定论文轮保存18条后中断。两轮和成本全部保留。
- 实际主结果在`paper_bound_deepseek_v41_flash/`。目录名沿用首个模型，但正式轮发生模型轮换：39/10/3题分别使用DeepSeek v4.1 Flash、DeepSeek v4 Flash、GLM 5.3 Flash；每题三模式同模型。新输入仅增加目标论文标题和arXiv编号，原题/Gold/生产代码/评分不变，新协议在运行前冻结。
- 三模式156条结果、156条匹配作答模型的判分、官方评分交叉核对、汇总与报告均已完成。
- RAG/Agent/Auto的Answer F1为14.83/14.81/21.39，近似Evidence F1为28.24/41.22/33.00。失败保留在52题分母。判分correct为25/25/28，不是人工准确率。
- 正式生成+判分819次请求、1,740,096 token。包含旧轮共885次已留档请求、1,859,159已报告token，另有未落盘/未回传用量；完整账单总量未知。当前私有配置选择`cn:deepseek-v4.1-flash`。
- README、PROJECT_METRICS、PROGRESS和实验索引已同步。本轮只做执行与文档，未修生产逻辑，未重跑旧345/42项测试；执行层3项检查通过。

## 接手时怎样使用现有结果

已有全量作答和判分，接手直接分析保存文件。旧版“一次跑完prepare/build/run/score/judge/report”命令对应原始输入目录，不再作为当前执行入口。

仅离线复算（不调用模型）：

```bash
QASPER_OUTPUT_DIR=evaluation/results/qasper_20261024/paper_bound_deepseek_v41_flash .venv/bin/python evaluation/results/qasper_20261024/run_supervised.py score
QASPER_OUTPUT_DIR=evaluation/results/qasper_20261024/paper_bound_deepseek_v41_flash .venv/bin/python evaluation/results/qasper_20261024/run_supervised.py report
.venv/bin/python evaluation/results/qasper_20261024/analyze_results.py
```

PDF、QASPER原数据包与知识库资产只在本机保留，跨机器需配对复制并校验。原`protocol.md`、原`frozen_sample.json`及原`evaluation/qasper_eval.py`均保持原字节；论文绑定新轮的协议和样本位于主结果目录。

## 尚未解决的边界与下一步

1. 拒答启发式存在至少1处明确误标、1处漏标；部分英文问题得到中文答案。Agent仍有需求引文/修正额度/复核失败。当前分数保留，不把本轮题目反复调试后称为新的独立成绩。
2. 若要更强泛化结论，另冻结更多新题、单一模型及可靠拒答/语言处理。模型轮换、本轮曾看过部分问题、近似段落对齐和同模型判分均需披露。
3. 本地提交按交接要求使用作者`JAzer-M <d1599356723@163.com>`；由用户推送，未授权自动推送。
4. 发布Windows `v0.2.0` Release、可选Mac重打0.2.0包、个人主页及简历/面试材料仍待后续。Windows人工验收与Mac预览已发布的状态来自已有记录，本轮没有重新核对GitHub线上状态。
