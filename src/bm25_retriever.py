# 关键词检索分支：正文分词并建 BM25 索引，再返回带原文/来源的排序候选。
# 当前词项是英文和数字；纯中文可能没有有效词项，不能据此判断 Dense 检索也无结果。

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
    tokens = re.findall(r"[a-z0-9]+", text)

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

    # 没有有效稀疏词项时返回空列表，避免零分候选凭名次污染 RRF。
    if not query_tokens:
        return []

    # 计算所有chunks的BM25分数
    scores = bm25.get_scores(query_tokens)

    # 剔除零分候选；真实词项匹配可能产生的负分仍保留。
    top_indices = sorted(
        (i for i, score in enumerate(scores) if score != 0),
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
            "title": chunk["title"],
            "section": chunk["section"],
            "text": chunk["text"]
        })

    return results
