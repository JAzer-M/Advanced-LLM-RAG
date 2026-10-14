def precision_at_k(retrieved_ids, relevant_ids, k):
    if k <= 0:
        raise ValueError("k must be greater than 0")

    relevant_set = set(relevant_ids)

    retrieved_set = set(retrieved_ids[:k])

    hits = retrieved_set.intersection(relevant_set)

    precision = len(hits) / k

    return precision

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

if __name__ == "__main__":

    relevant_ids = [197, 215]

    retrieved_ids = [215, 30, 50, 197, 100]

    for k in [1, 3, 5]:

        precision = precision_at_k(
            retrieved_ids,
            relevant_ids,
            k
        )

        recall = recall_at_k(
            retrieved_ids,
            relevant_ids,
            k
        )

        print(f"Precision@{k}: {precision: .4f}")
        print(f"Recall@{k}: {recall: .4f}")
        print()

    # 测试 AP@5
    ap = average_precision_at_k(
        retrieved_ids=[215, 30, 50, 197, 100],
        relevant_ids=[197, 215],
        k=5
    )

    print("AP@5:", ap)

    # 测试 MAP@5
    test_cases = [
        ([215, 30, 50, 197, 100], [197, 215]),
        ([5, 37, 9, 2, 4], [37])
    ]

    map_score = mean_average_precision_at_k(
        test_cases,
        k=5
    )

    print("MAP@5:", map_score)
    print()

    # 测试 RR@5
    rr = reciprocal_rank_at_k(
        retrieved_ids=[30, 50, 215, 197, 100],
        relevant_ids=[197, 215],
        k=5
    )

    print(f"RR@5: {rr:.4f}")

    # 测试 MRR@5
    mrr_test_cases = [
        ([30, 50, 215, 197, 100], [197, 215]),
        ([5, 37, 9, 2, 4], [37])
    ]

    mrr = mean_reciprocal_rank_at_k(
        mrr_test_cases,
        k=5
    )

    print(f"MRR@5: {mrr:.4f}")