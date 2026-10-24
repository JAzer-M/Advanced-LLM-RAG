# 递归分块的独立对照入口；当前主问答默认使用 Semantic 版本。
# 此旧入口直接写入固定的 Recursive 索引/JSON 路径，重跑前应保留已有配对资产。

from pathlib import Path

from src.pdf_loader import load_pdfs
from src.chunking_recursive import split_documents_recursive
from src.embedding import load_embedding_model, embed_chunks
from src.vector_store import build_index, save_index
from src.chunk_storage import save_chunks

def main():
    project_dir = Path(__file__).resolve().parent

    raw_dir = project_dir / "data" / "raw"
    processed_dir = project_dir / "data" / "processed"

    # Recursive 独立文件路径
    index_path = processed_dir / "faiss_recursive.index"
    chunks_path = processed_dir / "chunks_recursive.json"

    # 加载论文
    documents = load_pdfs(
        raw_dir,
        two_columns_files={"DCNN.pdf"}
    )

    # Recursive Chunking
    chunks = split_documents_recursive(
        documents,
        chunk_size = 500,
        chunk_overlap = 100
    )

    # Embedding
    model = load_embedding_model()
    embeddings = embed_chunks(model, chunks)

    # 构建FAISS Index
    index = build_index(embeddings)

    if index.ntotal != len(chunks):
        raise ValueError("Index and Chunks mismatch")

    # 保存实验数据
    save_index(index, index_path)
    save_chunks(chunks, chunks_path)

    print("Total chunks:", len(chunks))
    print("Embedding shape:", embeddings.shape)
    print("Total Vectors:", index.ntotal)

if __name__ == "__main__":
    main()
