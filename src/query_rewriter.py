def rewrite_query(query):
    from llm import generate_answer

    prompt = f"""
    You are a retrieval query optimization assistant
    for academic research papers.

    Rewrite the user's question to improve
    Dense and BM25 retrieval.

    Rules:
    1. Preserve the original meaning and intent.
    2. Keep important technical keywords and entity names.
    3. Expand ambiguous terms into precise technical terminology.
    4. Avoid unnecessary formal or academic paraphrasing.
    5. Do not introduce unsupported facts.
    6. Do not answer the question.
    7. Return only one optimized search query.

    Original Question:
    {query}

    Optimized Search Query:
    """

    rewritten_query = generate_answer(prompt).strip()

    return rewritten_query
