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


def rank_evidence(query, candidates, sub_query_results, model, sub_query_top_k=3):
    """Rank globally and locate subquestion evidence using the same candidates."""
    global_ranking = rerank_results(query, candidates, model, top_k=len(candidates),
                                  include_source=True)
    canonical = {(c['source'], c['page'], c['text']): c for c in candidates}
    sub_query_evidence = []
    for item in sub_query_results:
        local = {}
        for candidate in item['results']:
            chunk = canonical[(candidate['source'], candidate['page'], candidate['text'])]
            local.setdefault(chunk['chunk_id'], chunk)
        ranked = rerank_results(item['query'], list(local.values()), model,
                                top_k=sub_query_top_k, include_source=True)
        sub_query_evidence.append({'query': item['query'],
                                   'top_ids': [c['chunk_id'] for c in ranked]})
    return global_ranking, sub_query_evidence


def select_evidence(global_ranking, sub_query_evidence, top_k, retrieval_first_ids=()):
    """Protect original retrieval and subquestion first hits within the budget."""
    if top_k <= 0:
        raise ValueError('top_k must be greater than 0')
    protected = list(dict.fromkeys([*retrieval_first_ids,
        *(item['top_ids'][0] for item in sub_query_evidence if item['top_ids'])]))
    focused = {cid for item in sub_query_evidence for cid in item['top_ids']}
    selected = set(protected[:top_k])
    for ranking in ([c for c in global_ranking if c['chunk_id'] in focused], global_ranking):
        for chunk in ranking:
            if len(selected) >= top_k:
                break
            selected.add(chunk['chunk_id'])
    return [c for c in global_ranking if c['chunk_id'] in selected]
