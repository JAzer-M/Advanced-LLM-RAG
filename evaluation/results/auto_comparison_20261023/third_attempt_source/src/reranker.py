# BGE 负责相关性重排；rank_evidence 同时保存原题全局排名和子题局部 Top-K。
# select_evidence 在同一最终预算内保护锚点与局部证据，输出仍按原题全局排名排序。

# 为每个问题/原文对打相关性分数；分数用于排序，不是事实正确概率。
def rerank_results(
    query,
    candidates,
    model,
    top_k=5,
    include_source=True,
    score_cache=None,
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

    # 缓存由请求方创建，只复用完全相同的输入；文档ID不是分数缓存键。
    if score_cache is None:
        scores = model.predict(pairs)
    else:
        missing = list(dict.fromkeys(pair for pair in pairs if (id(model), *pair) not in score_cache))
        if missing:
            score_cache.update(((id(model), *pair), float(score))
                               for pair, score in zip(missing, model.predict(missing)))
        scores = [score_cache[(id(model), *pair)] for pair in pairs]

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


# 全局按原题重排，子题各自找局部 Top-K；同原文候选映射回统一 chunk_id。
def rank_evidence(query, candidates, sub_query_results, model, sub_query_top_k=3, score_cache=None):
    """Rank globally and locate subquestion evidence using the same candidates."""
    options = {} if score_cache is None else {'score_cache': score_cache}
    global_ranking = rerank_results(query, candidates, model, top_k=len(candidates),
                                  include_source=True, **options)
    canonical = {(c['source'], c['page'], c['text']): c for c in candidates}
    sub_query_evidence = []
    for item in sub_query_results:
        local = {}
        for candidate in item['results']:
            chunk = canonical[(candidate['source'], candidate['page'], candidate['text'])]
            local.setdefault(chunk['chunk_id'], chunk)
        ranked = rerank_results(item['query'], list(local.values()), model,
                                top_k=sub_query_top_k, include_source=True, **options)
        sub_query_evidence.append({'query': item['query'],
                                   'top_ids': [c['chunk_id'] for c in ranked]})
    return global_ranking, sub_query_evidence


# 优先保护锚点/明确保留 ID/各子题首条，再补局部证据与全局高分，始终受 top_k 限制。
def select_evidence(global_ranking, sub_query_evidence, top_k, retrieval_first_ids=(),
                    protected_ids=()):
    """Protect original retrieval and retained local evidence within the budget."""
    if top_k <= 0:
        raise ValueError('top_k must be greater than 0')
    protected = list(dict.fromkeys([*retrieval_first_ids, *protected_ids,
        *(item['top_ids'][0] for item in sub_query_evidence if item['top_ids'])]))
    focused = {cid for item in sub_query_evidence for cid in item['top_ids']}
    selected = set(protected[:top_k])
    for ranking in ([c for c in global_ranking if c['chunk_id'] in focused], global_ranking):
        for chunk in ranking:
            if len(selected) >= top_k:
                break
            selected.add(chunk['chunk_id'])
    return [c for c in global_ranking if c['chunk_id'] in selected]
