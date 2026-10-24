# 加载 CPU 上的多语言 MiniLM，并把分块正文编码为归一化的 384 维向量。
# 查询和建库必须使用匹配的模型；标题元数据没有在这里拼入编码文本。

from sentence_transformers import SentenceTransformer

def load_embedding_model():

    model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device = "cpu"
    )

    return model

def embed_chunks(model, chunks):

    # 列表顺序决定向量行顺序；必须与保存的 chunks.json 一致。
    texts = [chunk["text"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        batch_size = 16,
        show_progress_bar = True,
        convert_to_numpy = True,
        normalize_embeddings = True
    )

    return embeddings
