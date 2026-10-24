# 纯指标函数：输入检索 ID、Gold ID 和 K，不加载模型或读取标准答案。
# 逐题 AP/RR 汇总后才叫 MAP/MRR；无 Gold 时 Recall/AP/RR/nP 的未定义结果为 None。

# P@K 的分母固定为 K；少量 Gold 的题目即使命中齐全，原始 P 也可能很低。
def precision_at_k(retrieved_ids, relevant_ids, k):
    if k <= 0:
        raise ValueError("k must be greater than 0")

    relevant_set = set(relevant_ids)

    retrieved_set = set(retrieved_ids[:k])

    hits = retrieved_set.intersection(relevant_set)

    precision = len(hits) / k

    return precision


def normalized_precision_at_k(retrieved_ids, relevant_ids, k):
    """Fraction of the Gold chunks attainable within this question's budget."""
    return overall_normalized_precision_at_k([(retrieved_ids, relevant_ids)], k)


# 各题命中去重后求和，再除以各题 min(K,G) 之和；无可计分 Gold 时返回 None。
def overall_normalized_precision_at_k(test_cases, k):
    """Sum hits / sum min(K, Gold count); skip questions without Gold."""
    if k <= 0:
        raise ValueError("k must be greater than 0")

    hits = 0
    attainable = 0
    for retrieved_ids, relevant_ids in test_cases:
        relevant_set = set(relevant_ids)
        hits += len(set(retrieved_ids[:k]).intersection(relevant_set))
        attainable += min(k, len(relevant_set))

    return hits / attainable if attainable else None


# Recall 分母为该题 Gold 总数，和预算归一化指标在 G>K 时不相同。
def recall_at_k(retrieved_ids, relevant_ids, k):

    if k <= 0:
        raise ValueError("k must be greater than 0")

    relevant_set = set(relevant_ids)

    if not relevant_set:
        return None

    retrieved_set = set(retrieved_ids[:k])

    hits = retrieved_set.intersection(relevant_set)

    recall = len(hits) / len(relevant_set)

    return recall

# 每次首次命中 Gold 时累计当前排名的 Precision，最后除以该题 Gold 数。
def average_precision_at_k(retrieved_ids, relevant_ids, k):

    if k <= 0:
        raise ValueError("k must be greater than 0")

    relevant_set = set(relevant_ids)

    if not relevant_set:
        return None

    hits = 0
    precision_sum = 0.0
    seen = set()

    for rank, chunk_id in enumerate(retrieved_ids[:k], start=1):

        # 防止同一个chunk被重复计算
        if chunk_id in seen:
            continue

        seen.add(chunk_id)

        if chunk_id in relevant_set:

            hits += 1
            precision_at_rank = hits / rank

            precision_sum += precision_at_rank

    ap = precision_sum / len(relevant_set)

    return ap

def mean_average_precision_at_k(test_cases, k):
    ap_scores = []

    for retrieved_ids, relevant_ids in test_cases:

        ap = average_precision_at_k(
            retrieved_ids,
            relevant_ids,
            k
        )

        if ap is not None:
            ap_scores.append(ap)

    if not ap_scores:
        return None

    return sum(ap_scores) / len(ap_scores)

# 只看第一条相关片段的排名；没有命中返回 0，无 Gold 返回 None。
def reciprocal_rank_at_k(retrieved_ids, relevant_ids, k):
    if k <= 0:
        raise ValueError("k must be greater than 0")

    relevant_set = set(relevant_ids)

    if not relevant_set:
        return None

    for rank, chunk_id in enumerate(retrieved_ids[:k], start=1):

        if chunk_id in relevant_set:
            return 1 / rank

    return 0

def mean_reciprocal_rank_at_k(test_cases, k):

    rr_scores = []

    for retrieved_ids, relevant_ids in test_cases:

        rr = reciprocal_rank_at_k(
            retrieved_ids,
            relevant_ids,
            k
        )

        if  rr is not None:
            rr_scores.append(rr)

    if not rr_scores:
        return None

    return sum(rr_scores) / len(rr_scores)
