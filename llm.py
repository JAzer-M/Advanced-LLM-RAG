# 兼容原来的 generate_answer 调用名；分解、改写和 HyDE 最终都走同一 API 客户端。

"""问题分解与查询增强共用的 API 生成入口。"""

from src.api_llm import generate_final_answer as generate_answer
