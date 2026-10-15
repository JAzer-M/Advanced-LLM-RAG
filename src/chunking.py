def split_documents(documents, chunk_size = 500, chunk_overlap = 100):

    if(chunk_size <= 0 or not 0 <=chunk_overlap < chunk_size):
        raise ValueError("Invalid chunk size or overlap")

    chunks = []

    step = chunk_size - chunk_overlap

    for document in documents:

        text = document["text"]

        if not text.strip():
            continue

        for start in range(0, len(text), step):

            end = min(start + chunk_size, len(text))

            chunk_text = text[start:end]

            if not chunk_text.strip():
                continue
            chunk = {
                "text": chunk_text,
                "source": document["source"],
                "page": document["page"],
                "title": document["title"],
                "section": document["section"],
            }

            chunks.append(chunk)

            if end == len(text):
                break

    return chunks
