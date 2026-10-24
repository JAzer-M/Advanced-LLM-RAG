import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.pdf_loader import load_pdfs
from src.chunking_semantic import split_documents_semantic
from src.embedding import load_embedding_model, embed_chunks
from src.vector_store import build_index, save_index
from src.chunk_storage import save_chunks
from src.knowledge_base import activate_version, create_version, version_name

def main():

    project_dir = Path(__file__).resolve().parent

    processed_dir = project_dir / "data" / "processed"
    parser = argparse.ArgumentParser(description="构建独立的 Semantic 知识库版本，不覆盖旧库。")
    parser.add_argument('--version', type=version_name,
                        default=datetime.now(timezone.utc).strftime('semantic-%Y%m%dT%H%M%SZ'))
    parser.add_argument('--raw-dir', type=Path, default=project_dir / 'data' / 'raw')
    parser.add_argument('--two-column-files', nargs='*', default=['DCNN.pdf'],
                        help='显式按双栏阅读的 PDF 文件名；不自动猜测版式')
    parser.add_argument('--paper-manifest', type=Path,
                        help='可选 arXiv 清单：校验文件集合、补全标题并记录来源')
    parser.add_argument('--activate', action='store_true', help='校验成功后切换当前版本')
    args = parser.parse_args()
    if (processed_dir / 'versions' / args.version).exists():
        parser.error(f'版本 {args.version} 已存在，请使用新的版本名。')
    raw_dir = args.raw_dir.resolve()
    paper_manifest = None
    if args.paper_manifest:
        paper_manifest = json.loads(args.paper_manifest.read_text(encoding='utf-8'))
        papers = {f"{p['arxiv_id']}.pdf": p for p in paper_manifest['papers']}
        if set(papers) != {p.name for p in raw_dir.glob('*.pdf')}:
            parser.error('论文清单与目录中的 PDF 集合不一致。')

    # 1. 加载 PDF
    documents = load_pdfs(
        raw_dir,
        two_columns_files=set(args.two_column_files)
    )
    if paper_manifest:
        for document in documents:
            document['title'] = papers[document['source']]['title']

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

    # 6. 先生成独立版本，完成配对校验后才能切换当前库。
    processed_dir.mkdir(parents=True, exist_ok=True)
    metadata = {'kind': 'semantic_build', 'embedding_model':
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'normalized_embeddings': True, 'max_chunk_size': 500, 'percentile': 10,
                'two_columns_files': sorted(set(args.two_column_files)), 'documents': len(documents),
                'source_pdfs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(raw_dir.glob('*.pdf'))}}
    if paper_manifest:
        metadata['paper_manifest_sha256'] = hashlib.sha256(args.paper_manifest.read_bytes()).hexdigest()
        metadata['source_papers'] = paper_manifest['papers']
    with TemporaryDirectory(prefix='.semantic-build-', dir=processed_dir) as directory:
        index_path = Path(directory) / 'faiss.index'
        chunks_path = Path(directory) / 'chunks.json'
        save_index(index, index_path)
        save_chunks(chunks, chunks_path)
        create_version(processed_dir, args.version, index_path, chunks_path, metadata)
    if args.activate:
        activate_version(processed_dir, args.version)

    print("Semantic version created:", args.version)
    if args.activate:
        print("Active version:", args.version)
    else:
        print("Current selection unchanged. Activate with: python -m src.knowledge_base activate", args.version)
    print("Total Vectors:", index.ntotal)

if __name__ == "__main__":
    main()
