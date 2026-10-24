# Agent 诊断、本地工具与保存记录入口

本页从清理前 README 独立整理，保留 P2.1～P2.4 的输入输出、预算和历史命令。日常新问题从 [main 运行入口](../README.md)进入；最新 Auto、P2.5 结果及限制见 [PROGRESS](../PROGRESS.md)。以下阶段结果按当时版本理解，旧 h10 成功不能替代最新版升级失败记录。

所有命令在项目根目录执行。恢复上下文先读已有日志；使用新目录执行会产生真实 API 请求，旧目录受源码／输入哈希校验，不能用当前源码强行续写。

## P2第一步诊断入口

本节保留P2.1当时的诊断入口；当前`agent.py`已支持普通函数/字典实现的诊断、工具单步/循环与最终回答复核，当前状态和分版本对照见[PROGRESS](../PROGRESS.md)。此前代码注释整理已覆盖46个Python文件，新增的搜索工具与测试也保留中文说明，阅读顺序与文件职责见[代码阅读说明](../docs/CODE_READING_GUIDE.md)。

P2.1收尾时已完整运行下述三题规划/证据检查，目录内保存当时的真实输出；只记录建议，不执行工具。以下为当时的历史运行命令，查看已有日志即可恢复上下文：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python agent.py \
  --replay-dir evaluation/results/holdout_v1_20261020 \
  --question-id h01 h10 h11 \
  --output-dir evaluation/results/agent_p21_closeout_20261020/run
```

上面是已完成目录；当时相同源码/输入/公开选项续接新增调用0。**此前加注释改变了原文件哈希，当前源码不能向该旧目录续接**，历史源码快照/协议/结果保留。新目录会发生新API请求，每批硬上限6次、失败不自动重试。规划模型只收原问题并抽取片段；事实检查只收绑定需求/查询、原文和目录，Gold/旧答案/完整比较题不传入。P2.1人工核对3/3见[报告](../evaluation/results/agent_p21_closeout_20261020/report.md)；该P2.1历史运行未执行工具；当前工具循环见后文P2.3。

## P2.2 本地搜索与邻段读取工具

`load_search_resources()`加载一次八篇配对库和CPU模型；`search_local_kb(query, resources, source=None)`执行Dense/BM25 → RRF → BGE，候选120、返回最多10条。`source`须为库内精确文件名，传None则搜索全库；它只检索，不调用分解或生成API。

```python
from src.agent_tools import load_search_resources, search_local_kb

resources = load_search_resources()  # 同一进程复用；沿用PROGRESS中的离线/受控线程条件。
result = search_local_kb("What evaluation criterion does RAG use?", resources,
                         source="2005.11401v4.pdf")
```

当时已执行的原文结果见[search_result.json](../evaluation/results/agent_local_search_20261020/search_result.json)，无需重跑恢复上下文。该工具单独验收时来源由人工指定；后续Agent/Auto集成见当前PROGRESS，该单次工具结果不代表集成验收。

`read_neighbors(chunk_id, resources, source, window=1)`用于读命中片段附近的上下文：先限定同篇论文，再按入库顺序返回中心段及前后各一段；`window`可设0～2，最多返回5段，论文首尾自动截断。`source`必须与中心段的精确文件名一致。它不加载模型、不检索、不重排、不生成答案。

```python
from src.agent_tools import read_neighbors

hit = result['results'][0]  # 使用上面的搜索结果和同一份 resources，避免混用知识库版本。
nearby = read_neighbors(hit['chunk_id'], resources, source=hit['source'])
for item in nearby['results']:
    print(item['offset'], item['chunk_id'], item['page'], item['text'])
```

`offset=-1/0/1`分别表示前段、中心段、后段。分块检索可能命中主题相关段，但定义、条件或实验判据在紧邻处，读取邻段用于补齐这些上下文。这里的“邻段”指已保存分块的顺序，无法恢复解析或分块时遗漏的原文。只读取时，资源字典提供经`load_knowledge_base()`校验的`chunks`和`knowledge_base`即可，不需要调用`load_search_resources()`加载模型。真实人工样例和完整返回见[邻段报告](../evaluation/results/agent_neighbors_20261020/report.md)。

## P2.3 单次执行与有预算循环

默认运行`agent.py`仍只做规划和诊断；显式增加`--execute-once`后，每题最多执行一个工具，再做一次证据检查。搜索沿用模型给出的query/source，邻段固定前后各一段；answer/stop不调用工具或最终生成器。反馈提出的新行动只记录，不继续执行。

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python agent.py \
  --replay-dir evaluation/results/holdout_v1_20261020 \
  --question-id h10 --execute-once \
  --output-dir evaluation/results/agent_once_new_run
```

这条命令会产生新的API请求，需要本机反代运行；查看已有结果无需执行。单次模式最多两题、全批次最多6次请求。证据核对版本、manifest及原文，按版本/ID去重，保留旧证据在前；最多32段、24000字符，超限时报错，不静默删段。工具失败或请求失败均不自动重试；中断后可复用已完成的同输入调用和工具结果，未完成的尝试不会自动再执行。

代码重点为`execute_action()`、`merge_evidence()`和`run_diagnostics()`中的`execute_once`分支。逐步说明见[代码阅读指南](../docs/CODE_READING_GUIDE.md)，这轮真实结果及所有失败见[验收报告](../evaluation/results/agent_feedback_20261020/report.md)。真实搜索基于P2.1已验收行动的回放，最新反馈被校验拒绝；不把它描述为全新自主链路通过或h10答题成功。

以上是此前单步模式的实现及验收。新循环模式用以下命令，仍沿用受控CPU线程；命令会产生新API请求，阅读已保存记录无需重跑：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python agent.py \
  --replay-dir evaluation/results/holdout_v1_20261020 \
  --question-id h10 --max-actions 3 \
  --output-dir evaluation/results/agent_loop_new_run
```

循环一次只接受一题，最多3个工具行动、6次模型请求、32段/24000字符；前后各读两段。answer表示可以进入回答，stop表示边界停止；不加`--finalize`时只保存循环结果。反馈没有新增片段时停止；相同type/query/source/chunk_id的行动不会因reason变化而重复执行。

工具查询保留原题已有、且不含方法名的公共场景前缀，分别记录模型query和实际effective_query。重复行动或读取范围重叠超过一半时，若有同篇、匹配公共任务章节的未读区域，本地规则可选该区域，并记录action_overrides/action_origin。没有合适候选时保留原提议；若行动本身重复，最多再给模型一次改选机会，仍重复就停止。改选与非法状态修正共用一次预算，修正响应仍经过原校验，网络失败不自动重试。

P2.3当时的成功开发轨迹在[novelty_followup/run/h10.json](../evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json)：搜索新增9段，读结果表附近新增4段，避免重叠后改读任务说明新增3段，最终26段、10198字符；两项需求语义核对通过。单次成功轨迹是6个模型回合，开发不同方案累计9次实际新请求，缓存复用没有重复计为新请求。完整失败、成本及局限见[本轮报告](../evaluation/results/agent_loop_20261020/report.md)。

## P2.4 最终回答与复核

只查看已保存的[最终答案](../evaluation/results/agent_answer_20261021/network_followup/h10/answer.md)和[出处核对](../evaluation/results/agent_answer_20261021/manual_review.md)不产生请求。要亲自新跑回答阶段，可在项目根目录执行以下命令；它会调用已配置的反代，最多4次，不重跑规划、搜索或邻段读取：

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python agent.py \
  --answer-from evaluation/results/agent_loop_20261020/novelty_followup/run/h10.json \
  --output-dir evaluation/results/agent_answer_new_run
```

要运行“工具循环→回答复核”，在前一节循环命令上增加`--finalize`，并使用新输出目录。程序分别写入`loop/`与`answer/`；决策最多6请求、回答最多4请求，总计最多10请求，不额外启动检索修复循环。`--finalize`只与`--max-actions`配合，原诊断与单步模式保持。

回答阶段重新核对保存输入、知识库版本和原文，不把Gold、旧答案或执行理由作为证据。`answer.md`是可交付文本；`inputs.json`中的`passages`给出[n]对应的source/page/chunk_id及完整原文；逐题JSON另保留初稿、修订稿、复核与引用检查，`actual_chat_calls.json`记录原始请求和响应。引用编号是当前26段证据的顺序号，与chunk_id不同。

全缺失时返回`insufficient_evidence`；有证据时必须通过引用结构检查和模型逐项复核，才能返回`review_passed`。两次复核仍失败则`review_failed`，保留被拒草稿，交付明确的未通过说明；网络失败或截断直接留档，不自动重试。模型复核与本地引文存在性检查仍不是正确性的保证，具体实现与边界见[代码阅读指南](../docs/CODE_READING_GUIDE.md)。
