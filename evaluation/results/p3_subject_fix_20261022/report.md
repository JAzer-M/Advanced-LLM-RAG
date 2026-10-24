# P3书目名称误拒绝修复与开发回归

开始：2026-10-22；完成：2026-10-23（Asia/Shanghai）。审计目录沿用开始日期。用户要求先修复当下问题，并说明“开发回归”的含义。

已修复将original/paper来源修饰词误当成论文名称的问题。生产仅修改`src/arxiv_evidence.py`；新增7项行为回归，定向26项、全套298项离线通过，失败、错误、跳过及真实网络尝试均0。本轮新增模型请求、token及公网GET均0；真实模型全流程没有重跑，原冻结成绩与失败保留。

## 1. 问题与根因

此前[六题对照](../p3_validation_20261022/report.md)中，以下两条路径在搜索之前拒绝了正确标题，错误均为`External paper title must name the bound requirement subject.`。模型已给出完整标题`FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness`。

| 历史路径 | 完整绑定主体 | 原结果 | 本次书目查找名 | 原标题离线匹配 |
| --- | --- | --- | --- | --- |
| n04 / Auto-on | original FlashAttention | degraded | flashattention | 通过 |
| n06 / Agent-on | original FlashAttention paper | failed | flashattention | 通过 |

原代码将整个subject交给`agent.names_subject()`，要求标题包含来源修饰词，因此正确标题也不通过。预先列出的三个假设分别为来源修饰词误作名称、大小写/空白等排版问题、模型给错书目标题。对保存的原始组合做探测后：原词组与仅规范大小写/空白均失败；去除来源修饰词后正确标题通过，其他论文仍失败。证据支持第一个假设；这两个阻塞不是HTTP不可用或论文不存在。

证据：[历史原始诊断](../p3_validation_20261022/failure_diagnosis.json)、[修复前假设探测](hypothesis_probes_before.json)。本次探测没有调用模型或公网。

## 2. 改动及原因

在[src/arxiv_evidence.py](../../../src/arxiv_evidence.py)新增普通函数`paper_subject()`，仅供书目身份核对：规范现有大小写/空白，移除边缘的the/original和末尾paper。名称内部词、连字符与版本数字保留；只剩来源描述的空名称仍拒绝。不泛化为任意同义词、全局删词或模糊相似度匹配。

`run_arxiv_followup()`在两处使用同一查找名：先核对模型提出的完整标题，再核对实际返回并选择的题录标题。两处都保留原完整名称匹配，并要求满足原名称边界规则；返回错误论文时不能绕过第二道检查。新增`subject_identity`审计字段，记录完整绑定主体和书目查找名。

完整subject、need与原问题不改；后续选论文、检索原文、证据判断及回答继续使用完整需求。`agent.py`中的全局主体匹配、查询提示、工具协议、PDF版本/哈希/重新解析、证据上限及模型预算均未改动。这样只解除已知的书目误拒绝，需求约束和原文核验继续执行。[生产差异](production.diff)保留精确改动。

此规则只覆盖已明确出现的英文边缘来源描述，不声称能够识别任意自然语言论文别名，也不保证标题含某方法名就一定是原论文；实际选择与原文检查仍必须执行。

## 3. 修复流程和验收

1. 先保存文件哈希与源码基线，提取旧失败，写行为回归并在原代码上运行，确认测试能暴露已知问题。
2. 按上述假设做最小探测，确定失败位于本地书目匹配，不扩大到改模型、提示或联网协议。
3. 只改外部书目匹配，跑同一组回归及错误来源边界；检查原始两组FlashAttention主体/标题。
4. 定向检查通过后，运行一次全套离线测试；保留修复前失败、修复后日志和文件核验，再更新当前进度及导航。

| 验证 | 实际结果 | 记录 |
| --- | --- | --- |
| 原代码上的新增7项测试方法 | 6个失败子场景、0错误，复现误拒绝 | [摘要](red_summary.json)、[完整日志](tests_red.log) |
| 修复后arXiv集成定向测试 | 26项通过，失败/错误0 | [摘要](focused_green_summary.json)、[日志](tests_focused_green.log) |
| 修复后全部离线测试 | 298项通过，失败/错误/跳过/网络尝试0 | [摘要](offline_test_summary.json)、[日志](tests_all_green.log) |
| 保存的两组FlashAttention主体/标题 | 正确标题均通过，RoFormer和FlashAttention-2仍拒绝 | [逐项结果](saved_failure_pairs_after.json) |
| 原有文件及历史实验 | 按修复前4037份文件哈希逐项检查 | [文件核验](verification.json) |

新增7项测试方法含多个子场景：Agent与Auto可完成受控联网分支并保留完整需求；the/original/paper的边缘组合；不同论文名称拒绝；题录实际返回错论文时在读PDF前拒绝；RAG与Self-RAG、Mamba与Mamba-2等名称边界；名称内部original/paper不删除；没有方法名时拒绝。测试文件为[tests/test_arxiv_integration.py](../../../tests/test_arxiv_integration.py)。

main回归替换模型响应、HTTP响应及CPU模型资源，执行实际main、题录解析、PDF解析/哈希/重解析、证据登记、引文与回答复核代码。测试中模拟的模型/HTTP调用不是真实API或公网请求。FlashAttention历史组合另做确定性匹配检查，不把Mamba测试夹具或匹配检查称为原两题真实回答成功。

全套运行采用项目Python及既有离线/线程限制；测试摘要记录实际数量，不以历史291项记录代替本次运行：

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python -m unittest discover -s tests -v
```

原291项加本次7项为298项。失败记录独立保留，不覆盖[此前76次模型请求的评测记录](../p3_validation_20261022/summary.json)。

## 4. “开发回归”是什么意思

“回归”指改完代码后检查：原来暴露的问题是否修好，以及相关原有行为有没有被改坏。“开发回归”就是把已经看过、分析过或用于修复的题目，作为开发阶段的检查用例反复验证。

例如，n04/n06已让我们发现original/paper标题误拒绝；针对它们修复后再检查，是开发回归。它能证明这类已知阻塞被处理，不能再把它们当作从未见过的新题，声称系统对陌生问题的准确率提高。若以后用真实模型重跑这两题，也应另建开发回归目录，并记录新增调用和剩余失败。

因此，修复前Agent-off的4/6、Agent-on的5/6与Auto的1/2保持原样。不能从离线匹配通过推导修复后6/6或2/2，不能把不同版本选出的成功结果拼成总分。真实新题质量需要单独冻结新题、评分和代码，再独立验证。

## 5. 当前结论与边界

当前已完成用户要求的已知程序问题修复及最小充分验收。原因是失败发生在确定性的本地字符串匹配，用保存的精确输入可重复复现，且受控main路径及错误来源边界已经覆盖；本轮无需为相同阻塞重复付费调用模型。

本次真实模型请求/token/公网GET均为0，没有新的模型质量或成本成绩；当前修复版本的真实端到端回答尚未复验，也不能据298项程序测试声称P3总体稳定性或泛化收益已通过。没有重建知识库、改动私有配置、覆盖旧评测或进入P4。生产/测试和当前交接文档的前后快照、旧实验与知识库保留情况见[verification.json](verification.json)。

当前交接入口：[PROGRESS](../../../PROGRESS.md)、[量化口径](../../../docs/PROJECT_METRICS.md)、[实验索引](../README.md)。
