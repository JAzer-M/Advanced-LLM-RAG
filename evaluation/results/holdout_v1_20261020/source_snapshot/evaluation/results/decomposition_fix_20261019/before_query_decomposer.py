import json

def decompose_query(query):

    prompt = f"""
You are a query decomposition assistant for a scientific paper RAG system.

Your task is to analyze the user's question and determine
whether it requires multiple independent information searches.

Rules:
1. Do not answer the question.
2. If the question has only one information need,
   do not decompose it.
3. If the question requires multiple distinct pieces of evidence,
   generate exactly 2 or 3 sub-questions.

4. The sub-questions must be a decomposition of the original question.
   Do NOT include the original question itself as a sub-question.

5. Each sub-question should answer only one distinct information need
   required to answer the original question.

6. Preserve the exact entities, model names, paper names,
   abbreviations, and technical terms from the original question.

7. If the original question compares multiple specific models,
   methods, or papers, create separate sub-questions for each
   specific entity being compared.

8. Each sub-question must explicitly mention the relevant entity.
   Do not replace a specific entity with a generic term.

9. Preserve the factual intent of the original question.
   Do not introduce words such as "typical", "common", "usually",
   or "in general" unless they appear in the original question.

10. Do not make the sub-question broader or more general than
    the original question.

11. Return only valid JSON, without explanations or markdown.

Example:

Original question:
How do VGG and DCNN differ in their use of convolutional filter sizes?

Correct decomposition:
{{
    "needs_decomposition": true,
    "sub_queries": [
        "According to the VGG paper, what convolutional filter sizes are used?",
        "According to the DCNN paper, what convolutional filter sizes are used?"
    ]
}}

Incorrect decomposition:
{{
    "needs_decomposition": true,
    "sub_queries": [
        "How do VGG and DCNN differ in their use of convolutional filter sizes?",
        "What are the typical convolutional filter sizes used in VGG networks?",
        "What are the typical convolutional filter sizes used in DCNN networks?"
    ]
}}

Output format:
{{
    "needs_decomposition": boolean,
    "sub_queries": ["question 1", "question 2"]
}}

If decomposition is unnecessary, return an empty sub_queries list.

Original Question:
{query}
"""

    from llm import generate_answer

    response = generate_answer(prompt)

    try:
        result = json.loads(response.strip())

    except json.JSONDecodeError:
        result = None

    if not isinstance(result, dict):
        return {"needs_decomposition": False, "sub_queries": []}

    needs = result.get("needs_decomposition")
    sub_queries = result.get("sub_queries")

    if not isinstance(needs, bool):
        return {"needs_decomposition": False, "sub_queries": []}

    if not isinstance(sub_queries, list):
        return {"needs_decomposition": False, "sub_queries": []}

    if needs:
        if not 2 <= len(sub_queries) <= 3:
            return {"needs_decomposition": False, "sub_queries": []}

        for question in sub_queries:
            if not isinstance(question, str) or not question.strip():
                return {"needs_decomposition": False, "sub_queries": []}

    else:
        if sub_queries:
            return {"needs_decomposition": False, "sub_queries": []}

    return result