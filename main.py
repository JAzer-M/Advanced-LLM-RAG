from pathlib import Path

from src.pdf_loader import load_pdfs
from src.chunking import split_documents
from src.embedding import load_embedding_model, embed_chunks
from src.vector_store import build_index, save_index, load_index
from src.chunk_storage import save_chunks, load_chunks
from src.retriever import retrieve
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.hybrid_retriever import reciprocal_rank_fusion
from llm import generate_answer
from sentence_transformers import CrossEncoder
from src.reranker import rerank_results


def main():

    # 1. 设置文件路径
    project_dir = Path(__file__).resolve().parent

    raw_dir = project_dir / "data" / "raw"
    processed_dir = project_dir / "data" / "processed"

    index_path = processed_dir / "faiss.index"
    chunks_path = processed_dir / "chunks.json"

    # 2. 加载 Embedding Model
    model = load_embedding_model()

    # 3. 判断是否已经存在索引和 Chunks
    if index_path.exists() and chunks_path.exists():

        print("Loading existing FAISS Index...")

        index = load_index(index_path)
        chunks = load_chunks(chunks_path)

    else:

        print("Building new FAISS Index...")

        # 加载 PDF
        documents = load_pdfs(
            raw_dir,
            two_columns_files={"DCNN.pdf"}
        )

        print("Total pages:", len(documents))

        # 文本分块
        chunks = split_documents(
            documents,
            chunk_size=500,
            chunk_overlap=100
        )

        print("Total chunks:", len(chunks))

        # 生成 Embeddings
        embeddings = embed_chunks(model, chunks)

        print("Embedding Matrix Shape:", embeddings.shape)

        # 构建 FAISS Index
        index = build_index(embeddings)

        # 保存数据
        save_index(index, index_path)
        save_chunks(chunks, chunks_path)

        print("Index and Chunks saved successfully!")

    # 4. 检查索引与 Chunks 是否匹配
    if index.ntotal != len(chunks):
        raise ValueError("Index and Chunks count mismatch!")

    print("Total Vectors:", index.ntotal)
    print("Vector Dimensions:", index.d)
    print("Total Chunks:", len(chunks))
    for chunk in chunks[:20]:
        print(chunk["page"], chunk["section"])
    # 5. 用户提问
    query = input("Please enter your question:")

    # 6. Hybrid Retrieval

    # 构建bm25 index
    bm25 = build_bm25_index(chunks)

    # Dense retrieval
    dense_results = retrieve(
        model = model,
        index = index,
        chunks = chunks,
        query = query,
        top_k = 20
    )

    #BM25 retrieval
    bm25_results = retrieve_bm25(
        bm25 = bm25,
        chunks = chunks,
        query = query,
        top_k = 20
    )

    # RRF Fusion
    rrf_results = reciprocal_rank_fusion(
        dense_results = dense_results,
        bm25_results = bm25_results,
        k = 60,
        top_k = 20
    )

    # 加载cross-encoder
    reranker_model = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L6-v2",
    )

    # Cross-Encoder Reranking
    results = rerank_results(
        query = query,
        candidates = rrf_results,
        model = reranker_model,
        top_k = 5
    )

    print("\n === Metadata Check ===")
    print(results[0])

    # 对比 RRF 与 Cross-Encoder 的排序结果

    print("\n=== RRF Top-5 (Before Reranking) ===")

    for i, result in enumerate(rrf_results[:5], start=1):
        print(f"Rank: {i}")
        print(f"Source: {result['source']}")
        print(f"Page: {result['page']}")
        print(f"Text: {result['text'][:200]}")
        print()

    print("\n=== Cross-Encoder Top-5 (After Reranking) ===")

    for i, result in enumerate(results, start=1):
        print(f"Rank: {i}")
        print(f"Source: {result['source']}")
        print(f"Page: {result['page']}")
        print(f"Rerank Score: {result['rerank_score']:.4f}")
        print(f"Text: {result['text'][:200]}")
        print()

    # 7. 构建RAG context
    context_parts = []

    for i, result in enumerate(results, start = 1):
        chunk_text = (
            f"[{i}]"
            f"Source: {result['source']} | "
            f"Page: {result['page']} | "
            f"Section: {result['section']}\n"
            f"{result['text']}"
        )

        context_parts.append(chunk_text)

    context = "\n\n".join(context_parts)

    print("\n=== Retrieved Context ===")
    print(context)

    # 8. prompt construction
    prompt = f"""
    you are an AI research assistant.
    
    Answer the user's question based on the provided context.
    
    Rules:
    1. Use the provided context as your source of evidence.
    2. Do not invent information.
    3. Cite relevant evidence using [1], [2], etc.
    4. If the context does not contain enough information,
       clearly state that the evidence is insufficient.
    
    Context:
    {context}
    
    Question:
    {query}
    
    Answer:
    """

    print("\n=== RAG Prompt ===")
    print(prompt)

    # 9. LLM Generation
    answer = generate_answer(prompt)
    print("\n=== Generated Answer ===")
    print(answer)

if __name__ == "__main__":
    main()