# P3.2真实答案与原文核对

2026-10-22。同助手出题、实现和审阅；以下是工程验收与已知题开发回归，不是盲评。Gold只保存在冻结协议中，运行驱动仅把query传给main；模型不接收Gold或评分条件。

| 运行 | 核对与结论 |
| --- | --- |
| 初次s01 | 答案Adam，附β1=.9、β2=.98、ϵ=10⁻⁹；[8]映射到八篇库chunk66，Attention论文第7页Optimizer原文支持。原模型复核通过，人工核对核心及参数通过；arXiv调用0。 |
| 初次s02 | 仅返回Differential Mamba、Mamba-in-Mamba、Bi-Mamba+；模型拒选，未读取PDF，最终明确证据不足。拒答诚实，但未完成预先期望的联网回答。不能按程序completed算语义验收通过。 |
| s02第一次开发复验 | query为`ti:Mamba abstract`，结果含不支持的旧式ID，严格固定版本校验失败；main failed、没有答案。HTTP200并不等于工具解析成功。 |
| s02最终开发复验 | 模型给出完整书目标题，Python标题查询返回原论文，模型选`2312.00752v2`。第1页摘要明确是5×、比较对象为Transformers，核心引用[12]正确。补充句的[15]为第2页相近规模生成吞吐量，[14]为第15页推理基准，均有对应原文。 |

最终核心原句：`Mamba enjoys fast inference (5× higher throughput than Transformers)`，空白按PDF换行规范化；数字和比较对象直接来自保存PDF第1页摘要。PDF为36页/1168615字节，SHA-256为`adf70ed1803c85b1899dec3e21f3af0b124411439e8654b840ea65f7b9f52b2e`。另外用PyMuPDF读取实际物理第1、2、15页核对，所有6个外部窗口逐一验证为保存原文的连续切片。

最终引用登记：

| 引用 | 来源/页码 | 临时chunk ID | 文档内字符区间 |
| --- | --- | ---: | --- |
| [12] | `2312.00752v2.pdf`，第1页 | 1398 | 1040:2240 |
| [14] | 同版本，第15页 | 1456 | 1040:2240 |
| [15] | 同版本，第2页 | 1404 | 3120:4320 |

三个来源链接均由程序从实际被引用的登记表生成，指向该固定版本PDF。全部11段本地证据保持原顺序/原文，追加6段外部证据，共17段/10687字符；外部ID不写入1397段本地索引。

答案有两点表达瑕疵：中文“比……高5倍”应按原文5×比率理解，清楚的说法是“吞吐量是其5倍”；额外第2/15页句子重复了核心结论。模型scope理由声称相关引文均在摘要也不精确，第2页属于引言；人工核对以实际页码和原文为准。这些记录保留，不把模型pass当作完整语义证明，也不手工改写真实模型输出。

[初次s01答案](live/s01/answer/answer.md) · [初次s02拒答](live/s02/answer/answer.md) · [失败开发记录](network_followup/s02/network/result.json) · [最终真实答案](development_followup/s02/network/answer.md) · [最终原文登记](development_followup/s02/network/external_registry.json) · [独立原文核对JSON](manual_verification.json)
