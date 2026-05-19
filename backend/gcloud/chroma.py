"""
Vector store interface using Gemini embeddings + local JSON storage.
Drop-in replacement for the previous ChromaDB-based implementation.
No compiled dependencies — works on any platform including Render.
"""
import os
from typing import List

from gcloud.vector_store import add_documents, count, query as _query


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts using Gemini text-embedding-004."""
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    embeddings = []
    for text in texts:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        embeddings.append(result["embedding"])
    return embeddings


def embed_query(text: str) -> List[float]:
    """Embed a single query string using Gemini text-embedding-004."""
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


class _Collection:
    """Thin wrapper that mimics the ChromaDB collection interface."""

    def __init__(self, engagement_id: str):
        self._eid = engagement_id

    def count(self) -> int:
        return count(self._eid)

    def add(self, documents: List[str], embeddings: List[List[float]],
            ids: List[str], metadatas: List[dict]):
        add_documents(self._eid, ids, documents, embeddings, metadatas)

    def query(self, query_embeddings: List[List[float]], n_results: int = 6,
              where: dict = None) -> dict:
        category = where.get("category") if where else None
        qvec = query_embeddings[0]
        docs = _query(self._eid, qvec, n_results=n_results,
                      where_category=category)
        return {"documents": [docs]}


def get_collection(engagement_id: str) -> _Collection:
    """Return a collection-like object for the given engagement."""
    return _Collection(engagement_id)
