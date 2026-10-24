# P2.1 范围与证据状态修正：2026-10-20

已将操作需求和搜索查询绑定原题片段，事实检查按需求隔离，校验跨项条件/缺口；最终123项离线测试通过。h10定向复核为RAG missing、Self-RAG supported，查询不再把PopQA/TriviaQA转给RAG，训练损失不计判据支持。

本轮7次真实chat、13,504 token、全部stop，零自动重试/工具执行/新检索/最终回答。最后一次原始运行因局部比较校验过严被标failed；修正后对同一提示和真实响应离线回放通过，没有第8次调用。初始和中间失败全部保留。

新抽取式规划接口尚未完整新跑h01/h10/h11，不声称最终三题3/3。下一步先补最新链路回归，再接有预算的工具循环。

- [完整MD日志](../evaluation/results/agent_scope_fix_20261020/report.md)
- [人工核对](../evaluation/results/agent_scope_fix_20261020/manual_review.md)
- [最终123项测试](../evaluation/results/agent_scope_fix_20261020/tests_final.log)
- [同提示接受回放](../evaluation/results/agent_scope_fix_20261020/accepted_h10_replay.json)
- [当前进度](../PROGRESS.md)
