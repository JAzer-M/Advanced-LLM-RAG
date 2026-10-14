
import json
import re
import unicodedata
from pathlib import Path

from sentence_transformers import CrossEncoder

from src.embedding import load_embedding_model
from src.vector_store import load_index
from src.chunk_storage import load_chunks
from src.retriever import retrieve
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.hybrid_retriever import reciprocal_rank_fusion
from src.reranker import rerank_results

from evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    average_precision_at_k,
    reciprocal_rank_at_k,
    mean_average_precision_at_k,
    mean_reciprocal_rank_at_k
)


# 1. 设置路径
PROJECT_DIR = Path(__file__).resolve().parent.parent

questions_path = PROJECT_DIR / "evaluation" / "questions.json"
index_path = PROJECT_DIR / "data" / "processed" / "faiss_semantic.index"
chunks_path = PROJECT_DIR / "data" / "processed" / "chunks_semantic.json"


# 2. 文本标准化
def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


# 3. Gold Evidence 映射到 Chunk ID
def get_gold_chunk_ids(question, chunks):

    gold_ids = set()
    unmatched = []

    for evidence in question["gold_evidence"]:

        matched = []

        for i, chunk in enumerate(chunks):

            same_source = chunk["source"] == evidence["source"]
            same_page = chunk["page"] == evidence["page"]

            quote_match = (
                normalize_text(evidence["quote"])
                in normalize_text(chunk["text"])
            )

            if same_source and same_page and quote_match:
                matched.append(chunk.get("chunk_id", i))

        if not matched:
            unmatched.append(evidence["quote"])

        gold_ids.update(matched)

    return gold_ids, unmatched


# 4. 获取检索结果的 Chunk IDs
def get_result_ids(results, candidates=None):

    ids = []

    for result in results:

        if "chunk_id" in result:
            ids.append(result["chunk_id"])
            continue

        # 如果 Reranker 没有保留 ID，
        # 则从原始候选结果中恢复
        matches = [
            c["chunk_id"]
            for c in (candidates or [])
            if c["source"] == result["source"]
            and c["page"] == result["page"]
            and c["text"] == result["text"]
        ]

        if len(matches) != 1:
            raise ValueError(
                "Cannot uniquely identify reranked chunk"
            )

        ids.append(matches[0])

    return ids


# 5. 计算单道问题指标
def evaluate_retrieval(retrieved_ids, gold_ids, k):

    return {
        "precision": precision_at_k(
            retrieved_ids, gold_ids, k
        ),
        "recall": recall_at_k(
            retrieved_ids, gold_ids, k
        ),
        "ap": average_precision_at_k(
            retrieved_ids, gold_ids, k
        ),
        "rr": reciprocal_rank_at_k(
            retrieved_ids, gold_ids, k
        )
    }


# 6. 整体评估
def print_overall_metrics(name, test_cases, k):

    if not test_cases:
        print(f"No valid test cases for {name}")
        return

    mean_precision = sum(
        precision_at_k(retrieved, gold, k)
        for retrieved, gold in test_cases
    ) / len(test_cases)

    mean_recall = sum(
        recall_at_k(retrieved, gold, k)
        for retrieved, gold in test_cases
    ) / len(test_cases)

    map_score = mean_average_precision_at_k(
        test_cases, k
    )

    mrr_score = mean_reciprocal_rank_at_k(
        test_cases, k
    )

    print(f"\n=== Overall {name} Evaluation ===")
    print("Evaluated Questions:", len(test_cases))
    print(f"Mean Precision@{k}: {mean_precision:.4f}")
    print(f"Mean Recall@{k}: {mean_recall:.4f}")
    print(f"MAP@{k}: {map_score:.4f}")
    print(f"MRR@{k}: {mrr_score:.4f}")


# 7. 主程序
def main():

    k = 5
    candidate_k = 20

    # 加载问题
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print("Total Questions:", len(questions))

    # 加载检索资源
    model = load_embedding_model()
    index = load_index(index_path)
    chunks = load_chunks(chunks_path)

    if index.ntotal != len(chunks):
        raise ValueError("Index and Chunks count mismatch!")

    # 构建 BM25 索引
    bm25 = build_bm25_index(chunks)

    # Cross-Encoder 只加载一次
    reranker_model = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L6-v2"
    )

    # 存储四种方法的结果
    test_cases = {
        "Dense": [],
        "BM25": [],
        "Hybrid": [],
        "Hybrid + Reranker": [],
    }

    # 8. 遍历 Evaluation Dataset
    for question in questions:

        query = question["question"]

        print(f"\n{'=' * 50}")
        print("Question ID:", question["id"])
        print("Question:", query)

        # Out-of-Scope 单独处理
        if not question.get("gold_evidence"):
            print("Out-of-Scope: Skipped")
            continue

        # Ground Truth
        gold_ids, unmatched = get_gold_chunk_ids(
            question, chunks
        )

        if unmatched or not gold_ids:
            print("WARNING: Incomplete Ground Truth")
            for quote in unmatched:
                print("Unmatched:", quote)
            continue

        print("Gold IDs:", sorted(gold_ids))

        # 9. Dense Retrieval
        dense_results = retrieve(
            model=model,
            index=index,
            chunks=chunks,
            query=query,
            top_k=candidate_k
        )

        # 10. BM25 Retrieval
        bm25_results = retrieve_bm25(
            bm25=bm25,
            chunks=chunks,
            query=query,
            top_k=candidate_k
        )

        # 11. Hybrid Retrieval: RRF Top-20
        hybrid_results = reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            k=60,
            top_k=candidate_k
        )

        # 12. Cross-Encoder Reranking
        reranked_results = rerank_results(
            query=query,
            candidates=hybrid_results,
            model=reranker_model,
            top_k=k
        )

        # 13. 四种检索方法的 Top-5 IDs
        methods = {
            "Dense": get_result_ids(dense_results[:k]),
            "BM25": get_result_ids(bm25_results[:k]),
            "Hybrid": get_result_ids(hybrid_results[:k]),
            "Hybrid + Reranker": get_result_ids(
                reranked_results,
                candidates=hybrid_results
            )
        }

        # 14. 自动计算指标
        for name, retrieved_ids in methods.items():

            scores = evaluate_retrieval(
                retrieved_ids, gold_ids, k
            )

            test_cases[name].append(
                (retrieved_ids, gold_ids)
            )

            print(f"\n=== {name} Evaluation ===")
            print("Retrieved IDs:", retrieved_ids)

            print(f"Precision@{k}: {scores['precision']:.4f}")
            print(f"Recall@{k}: {scores['recall']:.4f}")
            print(f"AP@{k}: {scores['ap']:.4f}")
            print(f"RR@{k}: {scores['rr']:.4f}")

    # 15. 汇总最终结果
    print("\n" + "=" * 50)
    print("FINAL EVALUATION COMPARISON")
    print("=" * 50)

    for name, cases in test_cases.items():
        print_overall_metrics(
            name=name,
            test_cases=cases,
            k=k
        )

if __name__ == "__main__":
    main()
