"""
Semantic similarity for resume <-> job-description matching.

Uses a small, fast Sentence-Transformers model so it can run on CPU without
a GPU or external API call — good for a self-contained demo.
"""
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def _get_model():
    # Imported lazily so the rest of the app can run / be tested without
    # pulling in the (largish) torch + transformers dependency chain.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def embed(text: str) -> np.ndarray:
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def cosine_similarity(text_a: str, text_b: str) -> float:
    a = embed(text_a)
    b = embed(text_b)
    # embeddings are already normalized, so cosine similarity == dot product
    return float(np.dot(a, b))
