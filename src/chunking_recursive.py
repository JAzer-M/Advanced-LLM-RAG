def recursive_split_text(text, chunk_size, separators):
    # 文本已经足够短
    if len(text) <= chunk_size:
        return [text]

    # 取出当前优先级最高的分隔符
    separator = separators[0]

    # 退化为字符切分
    if separator == "":
        return [
            text[i: i + chunk_size]
            for i in range(0, len(text), chunk_size)
        ]

    # 按当前分隔符切分
    parts = text.split(separator)

    # 没有切开， 尝试下一个分隔符
    if len(parts) == 1:
        return recursive_split_text(
            text,
            chunk_size,
            separators[1:]
        )

    # 递归处理每个片段
    results = []

    for i, part in enumerate(parts):

        if i < len(parts) - 1:
            part += separator

        if part:
            results.extend(
                recursive_split_text(
                    part,
                    chunk_size,
                    separators[1:]
                )
            )

    return results

def merge_chunks(parts, chunk_size, chunk_overlap):

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")

    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Invalid chunk_overlap")

    chunks = []
    current = []
    current_len = 0

    for part in parts:

        if not part:
            continue

        if len(part) > chunk_size:
            raise ValueError("Part exceeds chunk size")

        # 当前片段放进去会不会超过限制？
        if current_len + len(part) > chunk_size:

            # 保存当前Chunk
            if current:
                chunks.append("".join(current).strip())

            # 移除开头的片段， 保留末尾重叠
            while current and (
                current_len > chunk_overlap
                or current_len + len(part) > chunk_size
            ):
                removed = current.pop(0)
                current_len -= len(removed)

        # 添加新片段
        current.append(part)
        current_len += len(part)

    # 保存最后一个 chunk
    if current:
        chunks.append("".join(current).strip())

    return chunks

def split_documents_recursive(
        documents,
        chunk_size = 500,
        chunk_overlap = 100
):

    seperator = ["\n\n", "\n", ".", " ", ""]

    chunks = []

    for document in documents:
        text = document["text"]

        # 递归切分
        parts = recursive_split_text(
            text,
            chunk_size,
            seperator
        )

        # 合并并处理overlap
        merged = merge_chunks(
            parts,
            chunk_size,
            chunk_overlap
        )

        # 保留metadata
        for chunk_text in merged:

            if not chunk_text:
                continue

            chunks.append({
                "chunk_id": len(chunks),
                "text": chunk_text,
                "source": document["source"],
                "page": document["page"],
                "title": document["title"],
                "section": document["section"]
            })

    return chunks


if __name__ == "__main__":

    from pathlib import Path
    from src.pdf_loader import load_pdfs

    # 1. 定位项目目录
    project_dir = Path(__file__).resolve().parent.parent
    raw_dir = project_dir / "data" / "raw"

    # 2. 加载 PDF
    documents = load_pdfs(raw_dir)

    # 3. Recursive Chunking
    chunks = split_documents_recursive(
        documents,
        chunk_size=500,
        chunk_overlap=100
    )

    # 4. 统计 Chunk 长度
    lengths = [len(chunk["text"]) for chunk in chunks]

    print("Total Pages:", len(documents))
    print("Total Chunks:", len(chunks))

    if lengths:
        print("Average Length:", sum(lengths) / len(lengths))
        print("Min Length:", min(lengths))
        print("Max Length:", max(lengths))

    # 5. 检查异常
    print("Empty Chunks:", sum(length == 0 for length in lengths))
    print("Oversized Chunks:", sum(length > 500 for length in lengths))

    # 6. 查看前三个 Chunk
    for chunk in chunks:

        if chunk["section"] is not None:
            print("\n=== Chunk ===")
            print("ID:", chunk["chunk_id"])
            print("Source:", chunk["source"])
            print("Page:", chunk["page"])
            print("Section:", chunk["section"])
            print("Text:", repr(chunk["text"][:200]))

            break