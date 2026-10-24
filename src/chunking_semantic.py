# 默认分块方法：比较相邻句向量，在相似度较低的位置切分，再满足字符长度预算。
# 各 document 独立处理；短句/短块会被过滤，超长单句保留，不保证 PDF 文本无损。

import re
import numpy as np

def split_sentences(text):

    # 标准化空白字符
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    # 保护常见缩写，避免被误认为句子结束
    protected_text = re.sub(
        r"\b(e\.g\.|i\.e\.|etc\.|vs\.)",
        lambda m: m.group(0).replace(".", "<DOT>"),
        text,
    )

    # 按句子结束标点分割
    sentences = re.split(
        r"(?<!\d\.)(?<=[.!?])\s+",
        protected_text
    )

    # 恢复缩写中的句号
    sentences = [
        sentence.replace("<DOT>", ".")
        for sentence in sentences
    ]

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

# 句向量已归一化，相邻向量点积可作为余弦相似度。
def compute_adjacent_similarities(embeddings):

    if len(embeddings) < 2:
        return np.array([])

    similarities = np.sum(
        embeddings[:-1]  * embeddings[1:],
        axis = 1
    )

    return similarities

# percentile 控制低相似度阈值；返回后一个句子的下标，供切块时断开。
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

            # 保留完整句子，不进行字符级硬切分
            chunks.append(sentence)

            continue

        # 尝试加入新句子
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

# 输出 chunk_id 与列表位置一致的元数据字典；入口构建脚本显式传 percentile=10。
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
