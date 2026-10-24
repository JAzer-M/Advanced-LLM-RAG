from llm import generate_answer

def generate_hypothetical_document(query: str) -> str:
    if not query.strip():
        raise ValueError("Empty query")

    prompt = f"""
    You are generating a short hypothetical passage to help
    retrieve evidence from scientific research papers.

    Question:
    {query}

    Write only 2-3 sentences, around 40-60 words.

    Requirements:
    - Stay tightly focused on the exact topic in the question.
    - Preserve the key terms and relationships in the question.
    - Describe only the general concepts needed to locate
      relevant evidence.
    - Do not name specific methods, transformations, algorithms,
      or experimental details unless they appear in the question.
    - Do not invent examples or speculate about what the authors
      actually did.
    - Avoid generic discussion of model architecture,
      feature learning, or generalization unless directly needed.
    - Prefer a concise, focused passage over a comprehensive answer.
    """


    hypothetical_document = generate_answer(prompt)

    return hypothetical_document
