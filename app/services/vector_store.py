"""
FAISS vector store over candidate resumes, so recruiters can semantically
search past candidates ("find me someone like this for a similar role")
instead of only running the one-shot JD-match in the screening agent.

This mirrors the RAG pattern (chunk/embed -> FAISS index -> top-k
similarity retrieval) from the resume's RAG projects, applied to candidate
search instead of document Q&A.
"""
import os
import pickle
from typing import List, Tuple

import numpy as np

from app.config import settings
from app.services.embeddings import embed

_INDEX_DIR = os.path.dirname(settings.faiss_index_path) or "."
_META_PATH = settings.faiss_index_path + ".meta.pkl"


class CandidateVectorStore:
    """
    Thin wrapper around a FAISS flat index (cosine similarity via
    normalized inner product) plus a parallel metadata list, persisted to
    disk so the index survives restarts.
    """

    def __init__(self):
        self._index = None
        self._metadata: List[dict] = []  # [{"candidate_id": int, "name": str, "job_id": int}, ...]

    def _ensure_loaded(self):
        if self._index is not None:
            return

        import faiss  # lazy import, same reasoning as embeddings.py

        os.makedirs(_INDEX_DIR, exist_ok=True)
        dim = 384  # all-MiniLM-L6-v2 embedding dimension

        if os.path.exists(settings.faiss_index_path) and os.path.exists(_META_PATH):
            self._index = faiss.read_index(settings.faiss_index_path)
            with open(_META_PATH, "rb") as f:
                self._metadata = pickle.load(f)
        else:
            self._index = faiss.IndexFlatIP(dim)  # inner product == cosine, since embeddings are normalized
            self._metadata = []

    def add(self, candidate_id: int, name: str | None, job_id: int, resume_text: str) -> None:
        self._ensure_loaded()
        vector = embed(resume_text).astype("float32").reshape(1, -1)
        self._index.add(vector)
        self._metadata.append({"candidate_id": candidate_id, "name": name, "job_id": job_id})
        self._persist()

    def search(self, query_text: str, top_k: int = 5) -> List[Tuple[dict, float]]:
        self._ensure_loaded()
        if self._index.ntotal == 0:
            return []

        query_vector = embed(query_text).astype("float32").reshape(1, -1)
        scores, indices = self._index.search(query_vector, min(top_k, self._index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self._metadata[idx], float(score)))
        return results

    def _persist(self) -> None:
        import faiss

        faiss.write_index(self._index, settings.faiss_index_path)
        with open(_META_PATH, "wb") as f:
            pickle.dump(self._metadata, f)


# module-level singleton, mirrors the lru_cache pattern used for the embedding model
_store: CandidateVectorStore | None = None


def get_vector_store() -> CandidateVectorStore:
    global _store
    if _store is None:
        _store = CandidateVectorStore()
    return _store
