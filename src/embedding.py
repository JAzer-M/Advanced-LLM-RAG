from sentence_transformers import SentenceTransformer

def load_embedding_model():

    model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device = "cpu"
    )

    return model

def embed_chunks(model, chunks):

    texts = [chunk["text"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        batch_size = 16,
        show_progress_bar = True,
        convert_to_numpy = True,
        normalize_embeddings = True
    )

    return embeddings