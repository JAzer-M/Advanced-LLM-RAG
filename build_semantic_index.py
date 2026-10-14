from pathlib import Path

from src.pdf_loader import load_pdfs
from src.chunking_semantic import split_documents_semantic
from src.embedding import load_embedding_model, embed_chunks
from src.vector_store import build_index, save_index
from src.chunk_storage import save_chunks


def main():

    project_dir = Path(__file__).resolve().parent

    raw_dir = project_dir / "data" / "raw"
    processed_dir = project_dir / "data" / "processed"


    # Semantic 独立路径
    index_path = processed_dir / "faiss_semantic.index"
    chunks_path = processed_dir / "chunks_semantic.json"


    # 1. 加载 PDF
    documents = load_pdfs(
        raw_dir,
        two_columns_files={"DCNN.pdf"}
    )


    # 2. 加载 Embedding Model
    model = load_embedding_model()


    # 3. Semantic Chunking
    chunks = split_documents_semantic(
        documents,
        model,
        max_chunk_size=500,
        percentile=10
    )


    print("Total Chunks:", len(chunks))

    required_fields = {"text", "source", "page", "title", "section"}

    for i, chunk in enumerate(chunks):

        missing = required_fields - chunk.keys()

        if missing:
            raise ValueError(
                f"Chunk {i} missing fields: {missing}"
            )

    # 4. Chunk Embedding
    embeddings = embed_chunks(
        model,
        chunks
    )


    print("Embedding Shape:", embeddings.shape)


    # 5. 构建 FAISS Index
    index = build_index(embeddings)


    if index.ntotal != len(chunks):
        raise ValueError(
            "Index and Chunks mismatch!"
        )


    # 6. 保存
    save_index(
        index,
        index_path
    )

    save_chunks(
        chunks,
        chunks_path
    )


    print("Semantic Index Created!")
    print("Total Vectors:", index.ntotal)



if __name__ == "__main__":
    main()