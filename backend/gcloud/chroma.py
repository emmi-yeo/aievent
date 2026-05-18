"""
ChromaDB helper with Gemini embeddings.
Documents are embedded manually so no embedding function is stored in the
collection — this avoids ChromaDB 1.x embedding-function conflict errors.
"""
import os
from typing import List

import chromadb


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


def get_collection(engagement_id: str) -> chromadb.Collection:
    """Return the persistent ChromaDB collection for an engagement.
    No embedding function is registered — embeddings are passed explicitly."""
    persist_dir = os.path.join("chroma_db", engagement_id)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(name=f"eng_{engagement_id}")
