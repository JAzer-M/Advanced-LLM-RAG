# 分块 JSON 的基础读写；它与 FAISS 向量行必须配对，正式版本校验见 knowledge_base.py。

import json
from pathlib import Path

def save_chunks(chunks, file_path):
    file_path = Path(file_path)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # 保存chunks
    with open(file_path, "w", encoding = "utf-8") as f:
        json.dump(
            chunks,
            f,
            ensure_ascii=False,
            indent=2
        )

def load_chunks(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {file_path}"
        )

    with open(file_path, "r", encoding = "utf-8") as f:
        chunks = json.load(f)

    return chunks
