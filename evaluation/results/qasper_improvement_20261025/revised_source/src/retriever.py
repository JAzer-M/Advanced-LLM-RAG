# Dense 检索：问题编码后搜索 FAISS，向量行号用于读取同一配对版本的 chunk。
# 建库与查询都归一化时，内积可作为余弦相似度；返回内容始终来自知识库原文。

import numpy as np

def retrieve(model, index, chunks, query, top_k = 5, sources=None):

    query_embedding = model.encode(
        [query],
        convert_to_numpy = True,
        normalize_embeddings = True
    )

    query_embedding = np.ascontiguousarray(
        query_embedding,
        dtype = np.float32
    )

    # 在FAISS中搜索最相似的向量
    # 限定来源时先取全库排名再过滤；不能把过滤后的列表当作原FAISS行号表。
    scores, indices = index.search(query_embedding, len(chunks) if sources else top_k)

    # 整理结果
    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx == -1:
            continue

        chunk = chunks[int(idx)]
        if sources and chunk['source'] not in sources:
            continue

        results.append({
            "chunk_id": int(idx),
            "score": float(score),
            "source": chunk["source"],
            "page": chunk["page"],
            "title": chunk["title"],
            "section": chunk["section"],
            "text": chunk["text"]
        })
        if len(results) >= top_k:
            break

    return results
