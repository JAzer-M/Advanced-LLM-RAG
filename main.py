from pathlib import Path

from sentence_transformers import CrossEncoder

from llm import generate_answer
from src.embedding import load_embedding_model
from src.vector_store import load_index
from src.chunk_storage import load_chunks
from src.retriever import retrieve
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.hybrid_retriever import reciprocal_rank_fusion
from src.reranker import rerank_results
from src.query_rewriter import rewrite_query

# 检索配置，默认关闭 Multi-Query。
USE_MULTI_QUERY = False
RETRIEVAL_TOP_K = 20
RRF_TOP_K = 20
RERANK_TOP_K = 5
RRF_K = 60

def main():
    # 1. 加载 Semantic FAISS Index 和 Chunks
    project_dir = Path(__file__).resolve().parent
    processed_dir = project_dir / "data" / "processed"
    index_path = processed_dir / "faiss_semantic.index"
    chunks_path = processed_dir / "chunks_semantic.json"

    # 缺少索引时先运行 build_semantic_index.py。
    if not index_path.is_file() or not chunks_path.is_file():
        raise FileNotFoundError(
            "Semantic Index 或 Chunks 文件不存在。"
            "请先运行 build_semantic_index.py。"
        )

    print("Loading existing Semantic FAISS Index...")
    embedding_model = load_embedding_model()
    index = load_index(index_path)
    chunks = load_chunks(chunks_path)

    if index.ntotal != len(chunks):
        raise ValueError("Index and Chunks count mismatch!")

    print("Total Vectors:", index.ntotal)
    print("Vector Dimensions:", index.d)
    print("Total Chunks:", len(chunks))

    # 2. 用户问题：原始问题始终用于 Reranking 和最终生成
    query = input("Please enter your question: ").strip()
    if not query:
        print("Question cannot be empty.")
        return

    print("Original Query:", query)

    # 3. 原始问题的两路检索
    bm25 = build_bm25_index(chunks)

    dense_results = retrieve(
        model=embedding_model,
        index=index,
        chunks=chunks,
        query=query,
        top_k=RETRIEVAL_TOP_K,
    )

    bm25_results = retrieve_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=RETRIEVAL_TOP_K,
    )

    # 4. 可选 Multi-Query：保留原始问题，再增加改写问题的两路检索
    extra_results = []

    if USE_MULTI_QUERY:
        rewritten_query = rewrite_query(query).strip()
        print("Rewritten Query:", rewritten_query)

        if rewritten_query and rewritten_query != query:
            rewritten_dense_results = retrieve(
                model=embedding_model,
                index=index,
                chunks=chunks,
                query=rewritten_query,
                top_k=RETRIEVAL_TOP_K,
            )

            rewritten_bm25_results = retrieve_bm25(
                bm25=bm25,
                chunks=chunks,
                query=rewritten_query,
                top_k=RETRIEVAL_TOP_K,
            )

            extra_results = [rewritten_dense_results, rewritten_bm25_results]
        else:
            print("Rewritten Query is empty or unchanged; using original only.")

    print("Multi-Query Active:", bool(extra_results))

    # 5. RRF 融合：可以处理两路或四路结果
    rrf_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        k=RRF_K,
        top_k=RRF_TOP_K,
        extra_results=extra_results,
    )

    # 6. BGE Reranking
    reranker_model = CrossEncoder("BAAI/bge-reranker-base", device="cpu")
    results = rerank_results(
        query=query,
        candidates=rrf_results,
        model=reranker_model,
        top_k=RERANK_TOP_K,
    )

    print("\n=== Retrieved Top-5 ===")
    for i, result in enumerate(results, start=1):
        print(f"\nRank: {i}")
        print(f"Source: {result['source']}")
        print(f"Page: {result['page']}")
        print(f"Section: {result['section']}")
        print(f"Text: {result['text']}")

    # 7. 使用最终检索结果构建 Context
    context_parts = []
    for i, result in enumerate(results, start=1):
        context_parts.append(
            f"[{i}] Source: {result['source']} | "
            f"Page: {result['page']} | "
            f"Section: {result['section']}\n"
            f"{result['text']}"
        )

    context = "\n\n".join(context_parts)

    # 8. 构建带引用规则的 Prompt
    prompt = f"""
You are an AI research assistant.

Answer the user's question based on the provided context.

Rules:
1. Answer the user's question using only the provided context.
2. Do not invent information or introduce unsupported claims.
3. Place citations immediately after the claims they support.
4. Cite only the context chunks that directly support each claim.
5. Do not list all citation numbers at the end of the answer.
6. Prioritize evidence that directly answers the question.
7. Avoid unrelated technical details.
8. If the evidence is insufficient, clearly state the limitation.

Context:
{context}

Question:
{query}

Answer:
"""

    # 9. 本地 Qwen 生成
    answer = generate_answer(prompt)
    print("\n=== Generated Answer ===")
    print(answer)

if __name__ == "__main__":
    main()
