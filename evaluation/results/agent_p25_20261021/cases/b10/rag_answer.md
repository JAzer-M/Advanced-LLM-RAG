Self-RAG 通过提示 GPT-4 生成 reflection tokens，并将这些知识蒸馏到一个内部 critic 模型 C 中来获得监督信号，从而无需在训练期间托管 critic 模型（[2]、[5]）。具体而言，它为每组 reflection token 从原始训练数据中随机采样实例，并针对不同 token 组使用不同的指令提示，以其示例中的 Retrieve 为例（[5]）。

CRAG 在接入大规模网络搜索之前，使用 ChatGPT 将输入改写为由关键词组成的查询，以模拟搜索引擎的日常使用方式（[8]）。
