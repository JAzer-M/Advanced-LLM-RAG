# P2.2 第一步：本地搜索工具验收

日期：2026-10-20（Asia/Shanghai）。本轮只实现搜索工具，不推进邻段读取或 Agent 工具循环。

## 实现与调用方式

新增 [src/agent_tools.py](../../../src/agent_tools.py)，保留普通函数、字典、列表和中文说明。

- `load_search_resources()`显式校验并加载`all-papers-8-20261020`，随后加载CPU MiniLM、BGE和内存BM25，供同一进程复用；不改变激活指针。
- `search_local_kb(query, resources, source=None)`执行Dense/BM25 → RRF → BGE。指定来源时先取得完整排名、筛选论文，再将各路与RRF候选截断至120；最多返回10条。
- source必须是当前库内精确论文文件名，None表示全库。返回原文、来源、页码、标题、章节、原库chunk ID、版本、分数和轨迹；不将过滤后的列表重新编号。
- 该工具不分解问题、不自由改写查询、不生成答案，也没有自动重试。

## 测试与真实运行

新增9项回归测试；**全部132项unittest通过**，失败/错误/跳过均0，测试网络请求0。覆盖来源过滤发生在截断之前、原ID/元数据、全库候选/结果预算、真实小型FAISS/BM25拼接、空结果、非法参数与失败传播。见[测试汇总](tests.json)和[原始日志](tests.log)。

只执行一次真实工具搜索：八篇/1,397条，查询直接取自P2.1保存的h10绑定查询，不读取Gold或旧答案驱动搜索。

```text
RAG: how does the correctness criterion reported by RAG differ | how does the correctness criterion reported by RAG differ
```

来源由本次人工指定为`2005.11401v4.pdf`。P2.1建议的source=null未在本轮实现自动来源路由。冻结协议早于模型加载与工具执行，结果没有反复重跑或按Gold调参。

| 实测项目 | 结果 |
| --- | --- |
| 工具搜索 / 查询编码 / BGE predict | 1 / 1 / 1 |
| 生成API / 网络请求 / 最终答案生成 | 0 / 0 / 0 |
| 返回原文 | 10条，全部属于指定RAG论文 |
| 原文身份 | ID/来源/页码/标题/章节/正文与配对库一致 |
| 资源加载 / 搜索 | 1.777秒 / 7.591秒 |
| Agent执行行动 | 0；本轮为手动工具验收 |

时间是本机受控线程下一次工具运行的记录，不是完整RAG延迟、并发或P95。原文存在与来源一致不等于它足以支持h10判据；本轮没有补查后语义检查、最终生成或h10答题验收。

| 排名 | chunk ID | PDF页码 | 来源 |
| --- | --- | --- | --- |
| 1 | 788 | 6 | 2005.11401v4.pdf |
| 2 | 786 | 6 | 2005.11401v4.pdf |
| 3 | 783 | 6 | 2005.11401v4.pdf |
| 4 | 796 | 7 | 2005.11401v4.pdf |
| 5 | 779 | 5 | 2005.11401v4.pdf |
| 6 | 800 | 7 | 2005.11401v4.pdf |
| 7 | 719 | 1 | 2005.11401v4.pdf |
| 8 | 803 | 7 | 2005.11401v4.pdf |
| 9 | 827 | 9 | 2005.11401v4.pdf |
| 10 | 763 | 4 | 2005.11401v4.pdf |

完整原文与各阶段候选ID见[search_result.json](search_result.json)，实际计数见[smoke_summary.json](smoke_summary.json)。[协议](protocol.json)、[运行脚本](run_smoke.py)及`source_snapshot/`保留；已运行目录拒绝自动重跑，恢复上下文直接读日志。

## 文档与资产保留

桌面总览由923行整理为66行的预期路线图，与[项目路线图](../../../docs/PROJECT_WORKFLOW.md)逐字一致；只写完整流程和阶段小步骤，不写当前状态/下一步。旧稿[完整备份](../../../docs/history/DESKTOP_WORKFLOW_BEFORE_SIMPLIFY_2026-10-20.md)。实际进度继续由PROGRESS和各轮日志维护。

核对原有2173项项目文件，既有Python源码全部未修改；允许变更只有README、PROGRESS和代码阅读说明。旧数据/实验/历史2083项文件哈希均一致，知识库配对文件和激活指针保留，未重建索引。48个维护中的Python文件及本次驱动通过纯编译检查。完整核对见[verification.json](verification.json)。

**第一步完成并停止。** 后续按用户指示处理邻段读取；Agent分派执行和反馈循环仍未接入。
