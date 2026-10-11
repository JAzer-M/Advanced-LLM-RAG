from rank_bm25 import BM25Okapi
import re
import unicodedata

# 文本Tokenization
def tokenize(text):
    # Unicode 标准化
    text = unicodedata.normalize("NFKC", text)

    # 转换成小写
    text = text.lower()

    # 统一乘号
    text = text.replace("×", "x")

    # 统一 3 * 3等表达形式
    text = re.sub(r"(\d)\s*x\s*(\d)", r"\1x\2", text)

    # 提取英文和数字词项 去除标点
    tokens = re.findall(r"[a-z0-0]+", text)

    return tokens

# 构建BM25 Index
def build_bm25_index(chunks):

    tokenized_corpus = [
        tokenize(chunk["text"]) for chunk in chunks
    ]

    bm25 = BM25Okapi(tokenized_corpus)

    return bm25

# BM25 retrieval
def retrieve_bm25(bm25, chunks, query, top_k = 5):
    # 对用户询问进行 Tokenization
    query_tokens = tokenize(query)

    # 计算所有chunks的BM25分数
    scores = bm25.get_scores(query_tokens)

    # 按分数从高到低排序
    top_indices = sorted(
        range(len(scores)),
        key = lambda i: scores[i],
        reverse = True
    )[:top_k]

    # 整理检索结果
    results = []

    for idx in top_indices:
        chunk = chunks[idx]

        results.append({
            "chunk_id": int(idx),
            "score": float(scores[idx]),
            "source": chunk["source"],
            "page": chunk["page"],
            "text": chunk["text"]
        })

    return results