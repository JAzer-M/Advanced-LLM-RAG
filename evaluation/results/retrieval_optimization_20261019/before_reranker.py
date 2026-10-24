def rerank_results(
    query,
    candidates,
    model,
    top_k=5,
    include_source=True,
):
    # 检查候选文档是否为空
    if not candidates:
        return []

    # 构建query-document pairs
    pairs = [
        (
            query,
            f"Source: {candidate['source']}\n"
            + (f"Title: {candidate['title']}\n" if candidate.get('title')
               and candidate['title'].strip().casefold() not in candidate['source'].casefold() else '')
            + candidate['text']
            if include_source
            else candidate["text"],
        )
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
