def rerank_results(query, candidates, model, top_k = 5):
    # 检查候选文档是否为空
    if not candidates:
        return []

    # 构建query-document pairs
    pairs = [
        (query, candidate["text"])
        for candidate in candidates
    ]

    # 使用cross-encoder计算相关性
    scores = model.predict(pairs)

    # 将scores添加到chunks中
    reranked_results = []

    for candidate, score in zip(candidates, scores):

        result = candidate.copy()

        result["rerank_score"] = float(score)

        reranked_results.append(result)

    # 按分数降序排列
    reranked_results.sort(
        key = lambda x: x["rerank_score"],
        reverse = True
    )

    # 返回最终Top_k
    return reranked_results[:top_k]
