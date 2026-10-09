import faiss
import numpy as np
from pathlib import Path

def build_index(embeddings):
    # 转换成FAISS需要的数据格式
    embeddings = np.ascontiguousarray(
        embeddings,
        dtype=np.float32,
    )

    # 获取embeddings的维度
    dimension = embeddings.shape[1]

    #创建FAISS索引
    index = faiss.IndexFlatIP(dimension)

    # 添加embeddings
    index.add(embeddings)

    return index

def save_index(index, file_path):
    # 将路径转换成Path对象
    file_path = Path(file_path)

    # 确保保存的目录存在
    file_path.parent.mkdir(
        parents = True,
        exist_ok = True
    )

    # 保存faiss索引
    faiss.write_index(index, str(file_path))

def load_index(file_path):
    file_path = Path(file_path)

    # 检查文件是否存在
    if not file_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {file_path}"
        )

    # 从硬盘加载index
    index = faiss.read_index(str(file_path))

    return index