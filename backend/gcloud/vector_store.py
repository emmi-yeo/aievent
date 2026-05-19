"""
Lightweight JSON + numpy vector store — replaces ChromaDB.
Embeddings are stored as JSON files on disk (one file per engagement).
Similarity search uses numpy cosine similarity — no compilation needed.
"""
import json
import os
from typing import List, Optional, Dict, Any

import numpy as np

STORE_DIR = os.environ.get("VECTOR_STORE_PATH", "vector_store")


def _path(engagement_id: str) -> str:
    os.makedirs(STORE_DIR, exist_ok=True)
    return os.path.join(STORE_DIR, f"{engagement_id}.json")


def _load(engagement_id: str) -> Dict:
    p = _path(engagement_id)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"ids": [], "documents": [], "embeddings": [], "metadatas": []}


def _save(engagement_id: str, data: Dict):
    with open(_path(engagement_id), "w") as f:
        json.dump(data, f)


def add_documents(
    engagement_id: str,
    ids: List[str],
    documents: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
):
    """Store documents with their embeddings."""
    data = _load(engagement_id)
    existing_ids = set(data["ids"])
    for i, doc_id in enumerate(ids):
        if doc_id not in existing_ids:
            data["ids"].append(doc_id)
            data["documents"].append(documents[i])
            data["embeddings"].append(embeddings[i])
            data["metadatas"].append(metadatas[i])
    _save(engagement_id, data)


def count(engagement_id: str) -> int:
    return len(_load(engagement_id)["ids"])


def query(
    engagement_id: str,
    query_embedding: List[float],
    n_results: int = 6,
    where_category: Optional[str] = None,
) -> List[str]:
    """Return top-n document chunks by cosine similarity, optionally filtered by category."""
    data = _load(engagement_id)
    if not data["embeddings"]:
        return []

    # Filter by category if requested
    indices = [
        i for i, m in enumerate(data["metadatas"])
        if where_category is None or m.get("category") == where_category
    ]
    if not indices:
        return []

    matrix = np.array([data["embeddings"][i] for i in indices], dtype=np.float32)
    qvec   = np.array(query_embedding, dtype=np.float32)

    # Cosine similarity
    norms  = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms  = np.where(norms == 0, 1e-9, norms)
    sims   = (matrix / norms) @ (qvec / (np.linalg.norm(qvec) + 1e-9))

    top_k  = min(n_results, len(indices))
    top_i  = np.argsort(sims)[::-1][:top_k]
    return [data["documents"][indices[j]] for j in top_i]
