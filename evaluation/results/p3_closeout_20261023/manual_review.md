# 两条真实开发回归：人工核对

2026-10-23（Asia/Shanghai）。只审阅本轮真实输出，不改生产代码、不新增模型judge或公开GET。标准在运行前写入[review_protocol.md](review_protocol.md)，问题与生产源码见[冻结协议](frozen_protocol.json)。

## n04 / Auto-on

程序结果为`degraded`，不计完整交付。原问题要求HBM、片上SRAM及tiling减少两者间读写的关系；本轮三项均没有交付，任务未通过。

Auto初稿发现原文不足后升级Agent，Agent本地判断为missing并正常停止。联网路由给出正确完整FlashAttention标题；本次实际绑定主体为`original FlashAttention paper`，书目查找名为`flashattention`，校验已通过，随后真实搜索GET返回HTTP429。没有执行选论文、PDF读取、外部证据检查或Agent最终回答复核。

降级答案明确“当前证据不足”，未编造所问机制。附加引用称Self-RAG使用FlashAttention提高长上下文训练效率，并用1–2块Quadro RTX 6000 GPU推理，对应本地`2310.11511v1.pdf`第19页、chunk1128，登记原文为：

> FlashAttention (Dao et al., 2022) is used to make the long-context training more efficient. We run inference of our trained models using 1-2 Quadro RTX 6000 GPUs with 24GB memory.

该引用只支持这段附加说明，不能支持原问题的三个必答点。安全说明缺口仍不等于回答任务完成。[真实降级答案](live/n04/auto_on/fallback.md)、[运行结果](live/n04/auto_on/result.json)、[429记录](live/n04/auto_on/network/search/result.json)。

## n06 / Agent-on

程序结果为`failed`，没有答案，任务未通过。模型完成本地需求规划、缺源判断和联网路由，本次主体是`FlashAttention`，没有来源修饰词；它也进入真实搜索GET并收到HTTP429。因此本次没有再次触发旧书目误拒绝，但不能单靠这条运行声称重新覆盖了原`original FlashAttention paper`词组；旧精确组合仍由[离线修复回归](../p3_subject_fix_20261022/saved_failure_pairs_after.json)覆盖。

没有读到原论文，也没有进入最终拒答或回答复核阶段。不能把运行日志中的missing状态，或评审者已知“原文未给出kWh”，算成系统已经正确拒答。[运行结果](live/n06/agent_on/result.json)、[429记录](live/n06/agent_on/network/search/result.json)。

## 本地参考与来源核验范围

只读此前保存的FlashAttention `2205.14135v2`完整34页PDF，本次无Gold预取GET，也未将该参考加入生产输入。文件SHA-256为`ca7f9fda10b90fc05dd291a3accc85e9c1a4a860b99b31928dab03ed3fcb14e4`，与此前冻结值一致。第1页包含HBM/SRAM/tiling机制支持；全文kWh、kilowatt、energy关键词出现次数均0，与此前人工核对的“该保存原论文未建立所问实测总kWh”边界一致。关键词缺失本身不是对现实世界或其他版本的普遍证明。[原参考PDF](../p3_validation_20261022/gold_sources/2205.14135v2/2205.14135v2.pdf)。

本轮两个初检上下文均与旧对应失败路径逐字节一致，本地登记原文保留且与八篇库一致。外部PDF数为0，所以PDF版本/哈希/连续窗口核验标为不适用，不记通过；没有答案的n06引用结构也标为不适用。n04仅初检降级引用结构通过，不代表完成Agent回答复核。[机器复算](metrics_raw.json)、[逐项人工结论](summary.json)。

## 成绩与成本

两条计划路径完整任务通过0/2，程序为1条degraded、1条failed。这只是已知开发用例的本轮结果，不是独立新题准确率；原4/6、5/6、1/2不改。

实际模型POST共9次、12278 token（输入11422、输出856），均finish_reason=stop，模型HTTP失败/调用失败/usage缺失均0。公开搜索GET共2次，均HTTP429；PDF GET、自动重试和Gold预取均0。本轮没有费用单价核验，不推算金额。
