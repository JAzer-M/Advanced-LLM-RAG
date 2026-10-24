# 两条已知路径开发回归：真实输出与引用，语义待人工核对


## n04 / auto_on / degraded

补查未完成，以下仅依据初检证据回答，仍保留原有缺口：
当前证据不足。提供的上下文未包含 FlashAttention 原论文关于 IO 缩减所涉及的两个 GPU 内存层级及减少传输的实现技术的内容；[1] 仅说明 Self-RAG 使用 FlashAttention 提升长上下文训练效率，并以 1–2 块 Quadro RTX 6000 GPU 进行推理，并未涉及该问题的技术细节。

引用[1] 2310.11511v1.pdf p.19 id=1128

We use Deepspeed stage 3 (Rajbhandari et al., 2020) to conduct multi-GPU distributed training, with training precision Bfloat16 enabled. FlashAttention (Dao et al., 2022) is used to make the long-context training more efficient. We run inference of our trained models using 1-2 Quadro RTX 6000 GPUs with 24GB memory.

## n06 / agent_on / failed

HTTPError: HTTP Error 429: Unknown Error
