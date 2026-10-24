def rewrite_query(query):
    from llm import generate_answer

    prompt = f"""
    You are a retrieval query optimization assistant
    for an academic research paper RAG system.

    Your task is to rewrite the user's question into
    a retrieval-optimized query for Dense and BM25 retrieval.

    The goal is NOT to make the question sound more formal.
    The goal is to improve the chance of matching relevant
    technical terminology in academic papers.

    Rules:
    1. Preserve the original information need and intent.
    2. Preserve all important entities, model names, paper names,
       abbreviations, and technical concepts from the original question.
    3. Keep the original important keywords whenever possible.
    4. When a technical concept may be expressed using different
       standard terminology in academic papers, add a concise
       synonym or closely related terminology that preserves the
       original meaning.
    5. Prefer terminology that is likely to appear in scientific
       papers, but do not invent specific facts, values, methods,
       or conclusions.
    6. Do not remove important technical terms from the original query.
    7. Do not broaden or narrow the information need.
    8. Do not answer the question.
    9. Do not add explanations.
    10. Return only ONE retrieval-optimized query.
    11. Keep the rewritten query concise.

    Example:

    Original Question:
    How do VGG and DCNN differ in their use of convolutional filter sizes?

    Optimized Search Query:
    VGG and DCNN convolutional filter sizes receptive field sizes

    Incorrect:
    VGG and DCNN architecture differences

    Incorrect:
    Why does VGG use small convolutional filters while DCNN uses large filters?

    Original Question:
    {query}

    Optimized Search Query:
    """
    rewritten_query = generate_answer(prompt).strip()

    return rewritten_query
