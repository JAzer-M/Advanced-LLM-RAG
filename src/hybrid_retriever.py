def reciprocal_rank_fusion(
    dense_results,
    bm25_results,
    k=60,
    top_k=5,
    extra_results=None
):
    # 存储每一个chunk的rrf分数
    rrf_scores = {}

    # 存储每隔chunk的原始信息
    chunk_lookup = {}

    # 便利两个retriever的结果
    for results in [dense_results, bm25_results, *(extra_results or [])]:
        for rank, result in enumerate(results, start=1):

            chunk_id = result["chunk_id"]

            # 计算并累加rrf分数
            rrf_scores[chunk_id] =(
                rrf_scores.get(chunk_id, 0.0)
                + 1 / (k + rank)
            )

            # 保存chunk信息
            chunk_lookup[chunk_id] = result

    # 根据rrf分数排序
    sorted_ids = sorted(
        rrf_scores,
        key = lambda idx: rrf_scores[idx],
        reverse = True
    )[:top_k]

    # 构建最终结果
    fused_results = []

    for chunk_id in sorted_ids:

        chunk = chunk_lookup[chunk_id]

        fused_results.append({
            "chunk_id": chunk["chunk_id"],
            "score": rrf_scores[chunk_id],
            "source": chunk["source"],
            "page": chunk["page"],
            "title": chunk["title"],
            "section": chunk["section"],
            "text": chunk["text"]
        })

    return fused_results