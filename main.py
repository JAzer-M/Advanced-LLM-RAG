from pathlib import Path

from src.pdf_loader import load_pdfs
from src.chunking import split_documents
from src.embedding import load_embedding_model, embed_chunks
from src.vector_store import build_index, save_index, load_index
from src.chunk_storage import save_chunks, load_chunks
from src.retriever import retrieve


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
        documents = load_pdfs(raw_dir)

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

    # 5. 用户提问
    query = "Why does VGG use small 3×3 convolutional filters?"

    # 6. Dense Retrieval
    results = retrieve(
        model=model,
        index=index,
        chunks=chunks,
        query=query,
        top_k=5
    )

    # 7. 输出检索结果
    for rank, result in enumerate(results, start=1):

        print(f"\n--- Result {rank} ---")
        print("Score:", result["score"])
        print("Source:", result["source"])
        print("Page:", result["page"])
        print("Text:", result["text"])


if __name__ == "__main__":
    main()