import argparse
import json
import re
import unicodedata
from pathlib import Path

from sentence_transformers import CrossEncoder

from evaluation.metrics import (
    average_precision_at_k,
    mean_average_precision_at_k,
    mean_reciprocal_rank_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)

from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.embedding import load_embedding_model
from src.hybrid_retriever import reciprocal_rank_fusion
from src.knowledge_base import load_knowledge_base
from src.query_rewriter import rewrite_query
from src.query_decomposer import decompose_query
from src.reranker import rerank_results
from src.retriever import retrieve


# ============================================================
# 1. Experiment configuration
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_PATH = PROJECT_DIR / "evaluation" / "questions.json"

FINAL_K = 5
CANDIDATE_K = 20
RRF_K = 60
RRF_TOP_K = 20

ENABLE_REWRITING = True
ENABLE_DECOMPOSITION = True

RERANKER_NAME = "BAAI/bge-reranker-base"
RERANKER_DEVICE = "cpu"


# ============================================================
# 2. Gold evidence and result ID utilities
# ============================================================

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).lower().strip()


def get_gold_chunk_ids(question, chunks):
    """Map each (source, page, exact quote) to matching chunk IDs."""

    gold_ids = set()
    unmatched_quotes = []

    for evidence in question["gold_evidence"]:

        matches = []

        for index, chunk in enumerate(chunks):

            if (
                chunk["source"] == evidence["source"]
                and chunk["page"] == evidence["page"]
                and normalize_text(evidence["quote"])
                in normalize_text(chunk["text"])
            ):
                matches.append(chunk.get("chunk_id", index))

        if matches:
            gold_ids.update(matches)

        else:
            unmatched_quotes.append(evidence["quote"])

    return gold_ids, unmatched_quotes


def get_result_ids(results, candidates=None):
    """Preserve ranking; recover IDs if the reranker dropped chunk_id."""

    ids = []

    for result in results:

        if "chunk_id" in result:
            ids.append(result["chunk_id"])
            continue

        matches = [
            candidate["chunk_id"]
            for candidate in (candidates or [])
            if candidate["source"] == result["source"]
            and candidate["page"] == result["page"]
            and candidate["text"] == result["text"]
        ]

        if len(matches) != 1:
            raise ValueError("Cannot uniquely identify reranked chunk")

        ids.append(matches[0])

    return ids


def deduplicate_results(results):
    """
    Remove duplicate chunks while preserving their first occurrence.

    Prefer chunk_id when available because it uniquely identifies
    a chunk in the current semantic chunking pipeline.
    """

    unique_results = []
    seen = set()

    for result in results:

        if "chunk_id" in result:
            key = ("chunk_id", result["chunk_id"])

        else:
            key = (
                result["source"],
                result["page"],
                result["text"],
            )

        if key not in seen:
            seen.add(key)
            unique_results.append(result)

    return unique_results


# ============================================================
# 3. Retrieval helpers
# ============================================================

def retrieve_two_ways(
        query,
        embedding_model,
        index,
        chunks,
        bm25
):
    dense = retrieve(
        model=embedding_model,
        index=index,
        chunks=chunks,
        query=query,
        top_k=CANDIDATE_K,
    )

    sparse = retrieve_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=CANDIDATE_K,
    )

    return dense, sparse


def fuse_and_rerank(
        query,
        dense,
        sparse,
        reranker_model,
        extra_results=None
):
    """
    RRF first; rerank against the user's ORIGINAL question.
    """

    fused = reciprocal_rank_fusion(
        dense_results=dense,
        bm25_results=sparse,
        k=RRF_K,
        top_k=RRF_TOP_K,
        extra_results=extra_results,
    )

    reranked = rerank_results(
        query=query,
        candidates=fused,
        model=reranker_model,
        top_k=FINAL_K,
    )

    return fused, reranked


def decomposition_retrieve_and_rerank(
        query,
        decomposition,
        original_fused,
        embedding_model,
        index,
        chunks,
        bm25,
        reranker_model
):
    """
    Query Decomposition experiment.

    Strategy:

    Original Query
        -> Dense + BM25 -> RRF
        -> candidate pool

    Each Sub-Query
        -> Dense + BM25 -> RRF
        -> candidate pool

    Then:

    candidate pool
        -> deduplication
        -> BGE reranker using ORIGINAL query
        -> Top-K
    """

    # 如果不需要 decomposition，
    # 直接使用原始 Hybrid + Reranker 的结果。
    if not decomposition["needs_decomposition"]:

        return (
            original_fused,
            None,
            None,
            None,
        )

    candidate_pool = list(original_fused)

    sub_query_details = []

    print("\n=== Query Decomposition Retrieval ===")

    for i, sub_query in enumerate(
        decomposition["sub_queries"],
        start=1
    ):

        print(f"\nSub-Query {i}: {sub_query}")

        sub_dense, sub_bm25 = retrieve_two_ways(
            sub_query,
            embedding_model,
            index,
            chunks,
            bm25,
        )

        sub_fused = reciprocal_rank_fusion(
            dense_results=sub_dense,
            bm25_results=sub_bm25,
            k=RRF_K,
            top_k=RRF_TOP_K,
        )

        candidate_pool.extend(sub_fused)

        sub_query_details.append({
            "query": sub_query,
            "dense": sub_dense,
            "bm25": sub_bm25,
            "rrf": sub_fused,
        })

        print(
            "Sub-Query RRF Top-5 IDs:",
            get_result_ids(sub_fused[:FINAL_K])
        )

    print(
        "\nDecomposition Candidate Pool Before Deduplication:",
        len(candidate_pool)
    )

    unique_candidates = deduplicate_results(candidate_pool)

    print(
        "Decomposition Candidate Pool After Deduplication:",
        len(unique_candidates)
    )

    reranked = rerank_results(
        query=query,
        candidates=unique_candidates,
        model=reranker_model,
        top_k=FINAL_K,
    )

    return (
        unique_candidates,
        reranked,
        decomposition,
        sub_query_details,
    )


# ============================================================
# 4. Metrics and reporting
# ============================================================

def evaluate_retrieval(retrieved_ids, gold_ids):

    return {
        "precision": precision_at_k(
            retrieved_ids,
            gold_ids,
            FINAL_K
        ),

        "recall": recall_at_k(
            retrieved_ids,
            gold_ids,
            FINAL_K
        ),

        "ap": average_precision_at_k(
            retrieved_ids,
            gold_ids,
            FINAL_K
        ),

        "rr": reciprocal_rank_at_k(
            retrieved_ids,
            gold_ids,
            FINAL_K
        ),
    }


def print_overall_metrics(name, cases):

    if not cases:

        print(f"\n=== Overall {name} Evaluation ===")
        print("No valid test cases")
        return

    mean_precision = sum(
        precision_at_k(
            retrieved,
            gold,
            FINAL_K
        )
        for retrieved, gold in cases
    ) / len(cases)

    mean_recall = sum(
        recall_at_k(
            retrieved,
            gold,
            FINAL_K
        )
        for retrieved, gold in cases
    ) / len(cases)

    print(f"\n=== Overall {name} Evaluation ===")

    print(
        "Evaluated Questions:",
        len(cases)
    )

    print(
        f"Mean Precision@{FINAL_K}: "
        f"{mean_precision:.4f}"
    )

    print(
        f"Mean Recall@{FINAL_K}: "
        f"{mean_recall:.4f}"
    )

    print(
        f"MAP@{FINAL_K}: "
        f"{mean_average_precision_at_k(cases, FINAL_K):.4f}"
    )

    print(
        f"MRR@{FINAL_K}: "
        f"{mean_reciprocal_rank_at_k(cases, FINAL_K):.4f}"
    )


def record_results(
        methods,
        gold_ids,
        test_cases
):

    for name, retrieved_ids in methods.items():

        scores = evaluate_retrieval(
            retrieved_ids,
            gold_ids
        )

        test_cases[name].append(
            (
                retrieved_ids,
                gold_ids
            )
        )

        print(f"\n=== {name} ===")

        print(
            "Retrieved IDs:",
            retrieved_ids
        )

        print(
            f"Precision@{FINAL_K}: "
            f"{scores['precision']:.4f}"
        )

        print(
            f"Recall@{FINAL_K}: "
            f"{scores['recall']:.4f}"
        )

        print(
            f"AP@{FINAL_K}: "
            f"{scores['ap']:.4f}"
        )

        print(
            f"RR@{FINAL_K}: "
            f"{scores['rr']:.4f}"
        )


# ============================================================
# 5. Main evaluation
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='按当前或指定知识库版本评价检索。')
    parser.add_argument('--kb-version')
    parser.add_argument('--questions', type=Path, default=QUESTIONS_PATH,
                        help='题目 JSON；默认保留已有六题')
    args = parser.parse_args()

    with args.questions.open(
        "r",
        encoding="utf-8"
    ) as file:

        questions = json.load(file)

    print('Questions:', args.questions)

    print(
        "Total Questions:",
        len(questions)
    )

    print(
        "Query Rewriting Enabled:",
        ENABLE_REWRITING
    )

    print(
        "Query Decomposition Enabled:",
        ENABLE_DECOMPOSITION
    )

    print(
        f"RRF candidates: Top-{RRF_TOP_K}; "
        f"final results: Top-{FINAL_K}"
    )

    # --------------------------------------------------------
    # Load models and index
    # --------------------------------------------------------

    index, chunks, knowledge_base = load_knowledge_base(PROJECT_DIR / 'data/processed', args.kb_version)
    print('Knowledge Base:', knowledge_base['version'])
    embedding_model = load_embedding_model()

    bm25 = build_bm25_index(
        chunks
    )

    reranker_model = CrossEncoder(
        RERANKER_NAME,
        device=RERANKER_DEVICE
    )

    # --------------------------------------------------------
    # Evaluation containers
    # --------------------------------------------------------

    test_cases = {

        "Dense": [],

        "BM25": [],

        "Hybrid": [],

        "Hybrid + Reranker": [],

    }

    if ENABLE_REWRITING:

        test_cases[
            "Rewritten Hybrid + Reranker"
        ] = []

        test_cases[
            "Multi-Query + Reranker"
        ] = []

    if ENABLE_DECOMPOSITION:

        test_cases[
            "Decomposition + Hybrid + Reranker"
        ] = []

    # --------------------------------------------------------
    # Evaluate every question
    # --------------------------------------------------------

    for question in questions:

        query = question["question"]

        print(
            "\n" + "=" * 60
        )

        print(
            "Question ID:",
            question["id"]
        )

        print(
            "Question:",
            query
        )

        # ----------------------------------------------------
        # Out-of-scope question
        # ----------------------------------------------------

        if not question.get(
            "gold_evidence"
        ):

            print(
                "Out-of-scope / no gold evidence: skipped"
            )

            continue

        # ----------------------------------------------------
        # Gold evidence
        # ----------------------------------------------------

        gold_ids, unmatched = get_gold_chunk_ids(
            question,
            chunks
        )

        if unmatched or not gold_ids:

            print(
                "WARNING: Incomplete ground truth; "
                "question skipped"
            )

            for quote in unmatched:

                print(
                    "Unmatched quote:",
                    quote
                )

            continue

        print(
            "Gold IDs:",
            sorted(gold_ids)
        )

        # ====================================================
        # A. Original Query Baseline
        # ====================================================

        original_dense, original_bm25 = retrieve_two_ways(
            query,
            embedding_model,
            index,
            chunks,
            bm25
        )

        original_fused, original_reranked = fuse_and_rerank(
            query,
            original_dense,
            original_bm25,
            reranker_model
        )

        methods = {

            "Dense":
                get_result_ids(
                    original_dense[:FINAL_K]
                ),

            "BM25":
                get_result_ids(
                    original_bm25[:FINAL_K]
                ),

            "Hybrid":
                get_result_ids(
                    original_fused[:FINAL_K]
                ),

            "Hybrid + Reranker":
                get_result_ids(
                    original_reranked,
                    candidates=original_fused
                ),

        }

        # ====================================================
        # B. Query Decomposition
        # ====================================================

        if ENABLE_DECOMPOSITION:

            decomposition = decompose_query(
                query
            )

            print(
                "\nDecomposition:",
                decomposition
            )

            if decomposition[
                "needs_decomposition"
            ]:

                print(
                    "Sub-Queries:"
                )

                for sub_query in decomposition[
                    "sub_queries"
                ]:

                    print(
                        "-",
                        sub_query
                    )

            (
                decomposition_candidates,
                decomposition_reranked,
                decomposition_info,
                sub_query_details,
            ) = decomposition_retrieve_and_rerank(
                query=query,
                decomposition=decomposition,
                original_fused=original_fused,
                embedding_model=embedding_model,
                index=index,
                chunks=chunks,
                bm25=bm25,
                reranker_model=reranker_model,
            )

            if decomposition[
                "needs_decomposition"
            ]:

                methods[
                    "Decomposition + Hybrid + Reranker"
                ] = get_result_ids(
                    decomposition_reranked,
                    candidates=decomposition_candidates,
                )

            else:

                print(
                    "Decomposition not needed; "
                    "using original Hybrid + Reranker "
                    "as fallback."
                )

                methods[
                    "Decomposition + Hybrid + Reranker"
                ] = get_result_ids(
                    original_reranked,
                    candidates=original_fused,
                )

        # ====================================================
        # C. Query Rewriting
        # ====================================================

        if ENABLE_REWRITING:

            rewritten_query = (
                rewrite_query(query).strip()
                or query
            )

            print(
                "\nOriginal Query:",
                query
            )

            print(
                "Rewritten Query:",
                rewritten_query
            )

            if rewritten_query == query:

                # The two queries are identical:
                # avoid needless retrieval/reranking.

                rewritten_fused = original_fused
                rewritten_reranked = original_reranked

                multi_fused = original_fused
                multi_reranked = original_reranked

            else:

                rewritten_dense, rewritten_bm25 = (
                    retrieve_two_ways(
                        rewritten_query,
                        embedding_model,
                        index,
                        chunks,
                        bm25
                    )
                )

                # ------------------------------------------------
                # Rewritten-only Hybrid
                # ------------------------------------------------

                rewritten_fused, rewritten_reranked = (
                    fuse_and_rerank(
                        query,
                        rewritten_dense,
                        rewritten_bm25,
                        reranker_model
                    )
                )

                # ------------------------------------------------
                # Multi-Query:
                #
                # Original Dense/BM25
                # +
                # Rewritten Dense/BM25
                # ------------------------------------------------

                multi_fused, multi_reranked = (
                    fuse_and_rerank(
                        query,
                        original_dense,
                        original_bm25,
                        reranker_model,
                        extra_results=[
                            rewritten_dense,
                            rewritten_bm25
                        ],
                    )
                )

            methods[
                "Rewritten Hybrid + Reranker"
            ] = get_result_ids(
                rewritten_reranked,
                candidates=rewritten_fused
            )

            methods[
                "Multi-Query + Reranker"
            ] = get_result_ids(
                multi_reranked,
                candidates=multi_fused
            )

        # ====================================================
        # Record results
        # ====================================================

        record_results(
            methods,
            gold_ids,
            test_cases
        )

    # ========================================================
    # Final comparison
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "FINAL EVALUATION COMPARISON"
    )

    print(
        "=" * 60
    )

    for name, cases in test_cases.items():

        print_overall_metrics(
            name,
            cases
        )


if __name__ == "__main__":
    main()
