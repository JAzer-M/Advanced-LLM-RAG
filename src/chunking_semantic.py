import re
import numpy as np

from src.embedding import load_embedding_model

def split_sentences(text):

    # 标准化空白字符
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    # 按句子结束标点分割
    sentences = re.split(r"(?<!\d\.)(?<=[.!?])\s+", text)

    # 清理空白句子
    sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
        and len(sentence.strip()) > 10
    ]

    return sentences

def embed_sentences(sentences, model):

    embeddings = model.encode(
        sentences,
        convert_to_numpy = True,
        normalize_embeddings = True,
    )

    return embeddings

def compute_adjacent_similarities(embeddings):

    if len(embeddings) < 2:
        return np.array([])

    similarities = np.sum(
        embeddings[:-1]  * embeddings[1:],
        axis = 1
    )

    return similarities

def detect_semantic_boundaries(similarities, percentile):

    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")

    if len(similarities) < 2:
        return np.array([])

    # 动态计算阈值
    threshold = np.percentile(similarities, percentile)

    # 找到低于阈值的位置
    boundary_indices = np.where(
        similarities < threshold
    )[0] + 1

    return boundary_indices.tolist()

def group_sentences_by_boundaries(
        sentences,
        boundaries,
        max_chunk_size = 500
):
    if max_chunk_size <= 0:
        raise ValueError("Max chunk size must be positive")

    chunks = []
    current = ""

    boundaries = set(boundaries)

    for i, sentence in enumerate(sentences):

        sentence = sentence.strip()

        if not sentence:
            continue

        # 遇到语义边界， 保存当前chunk
        if i in boundaries and current:
            chunks.append(current)
            current = ""

        # 单个句子已经超过长度限制
        if len(sentence) > max_chunk_size:

            if current:
                chunks.append(current)
                current = ""

            # 最后回退到字符切分
            for j in range(0, len(sentence), max_chunk_size):
                chunks.append(
                    sentence[j : j + max_chunk_size]
                )

            continue

        # 尝试假如新句子
        candidate = (
            f"{current} {sentence}"
            if current
            else sentence
        )

        # 判断是否超出最大长度
        if len(candidate) > max_chunk_size:

            if current:
                chunks.append(current)

            current = sentence

        else:
            current = candidate

    # 保存最后一个chunk
    if current:
        chunks.append(current)

    return chunks

def split_documents_semantic(
        documents,
        model,
        max_chunk_size = 500,
        percentile = 20
):

    chunks = []

    for document in documents:

        # 获取当前PDF页面的原始文本
        page_text = document["text"]

        # 按换行符拆分为多行
        lines = page_text.splitlines()

        # 如果最后一行是当前页码， 删除它
        if lines and lines[-1].strip() == str(document["page"]):
            lines.pop()

        # 重新合并文本
        page_text = "\n".join(lines)

        # Sentence Splitting
        sentences = split_sentences(page_text)

        if not sentences:
            continue

        # 计算语义边界
        if len(sentences) >= 2:
            embeddings = embed_sentences(sentences, model)

            similarities = compute_adjacent_similarities(
                embeddings
            )

            boundaries = detect_semantic_boundaries(
                similarities,
                percentile = percentile
            )

        else:
            boundaries = []

        # 按语义边界和长度限制生成Chunks
        semantic_chunks = group_sentences_by_boundaries(
            sentences,
            boundaries,
            max_chunk_size = max_chunk_size
        )

        # 保存文本和元数据
        for chunk_text in semantic_chunks:

            if not chunk_text:
                continue

            if len(chunk_text.strip())  < 50:
                continue

            chunks.append({
                "chunk_id": len(chunks),
                "text": chunk_text,
                "source": document["source"],
                "page": document["page"],
                "title": document["title"],
                "section": document["section"],
            })

    return chunks


if __name__ == "__main__":

    from pathlib import Path
    from src.pdf_loader import load_pdfs
    from src.embedding import load_embedding_model

    project_dir = Path(__file__).resolve().parent.parent
    raw_dir = project_dir / "data" / "raw"

    # 加载三篇论文
    documents = load_pdfs(raw_dir)

    # 加载 Embedding Model
    model = load_embedding_model()

    # 执行 Semantic Chunking
    chunks = split_documents_semantic(
        documents,
        model,
        max_chunk_size=500,
        percentile=20
    )

    lengths = [len(chunk["text"]) for chunk in chunks]

    print("\n=== Semantic Chunking Statistics ===")
    print("Total Pages:", len(documents))
    print("Total Chunks:", len(chunks))

    if lengths:
        print("Average Length:", sum(lengths) / len(lengths))
        print("Min Length:", min(lengths))
        print("Max Length:", max(lengths))
        print("Empty Chunks:", sum(x == 0 for x in lengths))
        print("Oversized Chunks:", sum(x > 500 for x in lengths))

    for chunk in chunks[:3]:
        print("\n=== Chunk ===")
        print("ID:", chunk["chunk_id"])
        print("Source:", chunk["source"])
        print("Page:", chunk["page"])
        print("Text:", repr(chunk["text"][:300]))

    # 统计过短的 Chunk
    short_50 = [c for c in chunks if len(c["text"]) < 50]
    short_100 = [c for c in chunks if len(c["text"]) < 100]

    print("\n=== Short Chunk Analysis ===")
    print("Chunks shorter than 50:", len(short_50))
    print("Chunks shorter than 100:", len(short_100))

    # 查看最短的 5 个 Chunk
    sorted_chunks = sorted(
        chunks,
        key=lambda c: len(c["text"])
    )

    for chunk in sorted_chunks[:5]:
        print("\nChunk ID:", chunk["chunk_id"])
        print("Source:", chunk["source"])
        print("Page:", chunk["page"])
        print("Length:", len(chunk["text"]))
        print("Text:", repr(chunk["text"]))

