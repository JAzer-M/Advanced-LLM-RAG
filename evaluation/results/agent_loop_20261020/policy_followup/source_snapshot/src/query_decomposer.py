# 固定 RAG 的检索前分解：API 判断是否需要 2～4 个独立子问题，再校验结构和数量。
# 它只生成补充检索问题；agent.py 另外抽取需求并判断已有证据能否支持事实。

import json

MAX_SUB_QUERIES = 4


def rejected_decomposition(reason, proposed_count=None):
    return {'needs_decomposition': False, 'sub_queries': [],
            'status': 'rejected', 'reason': reason, 'proposed_count': proposed_count}


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
   generate between 2 and {MAX_SUB_QUERIES} sub-questions.

4. The sub-questions must be a decomposition of the original question.
   Do NOT include the original question itself as a sub-question.

5. Each sub-question should answer only one distinct information need
   required to answer the original question.
   For comparisons with multiple entities AND multiple requested aspects,
   split by entity and by aspect when the total fits within {MAX_SUB_QUERIES}.
   For example, comparing Method A and Method B on representation and scoring
   requires four searches: A representation, A scoring, B representation,
   and B scoring. Do not combine representation and scoring in one search.
   For vector-retrieval questions, keep concrete retrieval vocabulary:
   representation searches should explicitly ask about query/document vectors
   or embeddings; scoring searches should ask how similarity between them is
   computed. Do not assume or name a particular scoring function in the query.

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
        return rejected_decomposition('invalid_json')

    if not isinstance(result, dict):
        return rejected_decomposition('not_an_object')

    needs = result.get("needs_decomposition")
    sub_queries = result.get("sub_queries")

    if not isinstance(needs, bool):
        return rejected_decomposition('needs_decomposition_not_boolean')

    if not isinstance(sub_queries, list):
        return rejected_decomposition('sub_queries_not_list')

    if needs:
        for question in sub_queries:
            if not isinstance(question, str) or not question.strip():
                return rejected_decomposition('invalid_sub_query', len(sub_queries))
        normalized = list(dict.fromkeys(question.strip() for question in sub_queries))
        if not 2 <= len(normalized) <= MAX_SUB_QUERIES:
            return rejected_decomposition('sub_query_count_out_of_range', len(sub_queries))
        return {'needs_decomposition': True, 'sub_queries': normalized,
                'status': 'accepted', 'proposed_count': len(sub_queries)}

    else:
        if sub_queries:
            return rejected_decomposition('not_needed_with_sub_queries', len(sub_queries))

    return {'needs_decomposition': False, 'sub_queries': [], 'status': 'not_needed'}
