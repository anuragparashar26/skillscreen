"""ChromaDB and embeddings helpers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import chromadb
from chromadb.utils import embedding_functions


class ChromaManager:
    """Manage a Chroma client and simple collection operations.

    This class uses ChromaDB's default embedding function (all-MiniLM-L6-v2)
    which runs locally and is free to use.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        # Default client will use in-memory storage
        self.client = chromadb.Client()
        # Use ChromaDB's default embedding function (sentence-transformers all-MiniLM-L6-v2)
        self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    def get_or_create_collection(self, name: str = "resumes"):
        try:
            return self.client.get_or_create_collection(
                name=name,
                embedding_function=self._embedding_fn
            )
        except Exception:
            return self.client.create_collection(
                name=name,
                embedding_function=self._embedding_fn
            )

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        """Embed texts using ChromaDB's default embedding function (free, local)."""
        return self._embedding_fn(list(texts))

    def add_documents(self, collection_name: str, ids: List[str], documents: List[str], metadatas: List[Dict[str, Any]], embeddings: Optional[List[List[float]]] = None):
        coll = self.get_or_create_collection(collection_name)
        if embeddings is None:
            embeddings = self.embed_texts(documents)
        coll.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def query_similarity(self, collection_name: str, query_embedding: List[float], n_results: int = 10):
        coll = self.get_or_create_collection(collection_name)
        resp = coll.query(query_embeddings=[query_embedding], n_results=n_results, include=["metadatas", "distances", "documents", "ids"])
        # resp is a dict with keys: ids, distances, metadatas, documents
        results = []
        ids = resp.get("ids", [[]])[0]
        distances = resp.get("distances", [[]])[0]
        metadatas = resp.get("metadatas", [[]])[0]
        documents = resp.get("documents", [[]])[0]
        for i, _id in enumerate(ids):
            # convert distance to similarity approximation (if metric is cosine, distances are 1-cos)
            dist = distances[i]
            try:
                similarity = 1.0 - dist
            except Exception:
                similarity = float(dist)
            results.append({
                "id": _id,
                "distance": dist,
                "similarity": similarity,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "document": documents[i] if i < len(documents) else "",
            })
        return results


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    a_arr = np.array(a, dtype=float)
    b_arr = np.array(b, dtype=float)
    if np.linalg.norm(a_arr) == 0 or np.linalg.norm(b_arr) == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
