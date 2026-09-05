"""
Semantic similarity for resume <-> job-description matching.

Uses a small, fast Sentence-Transformers model so it can run on CPU without
a GPU or external API call — good for a self-contained demo. Embeddings are
handled as torch tensors end-to-end (device placement, normalization, and
cosine similarity), with a numpy conversion only at the FAISS boundary.
"""
from functools import lru_cache

import numpy as np
import torch

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def _get_model():
    # Imported lazily so the rest of the app can run / be tested without
    # pulling in the (largish) torch + transformers dependency chain.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2", device=_DEVICE)


def embed(text: str) -> torch.Tensor:
    """Return a normalized embedding as a torch tensor on _DEVICE."""
    model = _get_model()
    with torch.no_grad():
        vector = model.encode(text, convert_to_tensor=True, device=_DEVICE)
    return torch.nn.functional.normalize(vector, dim=-1)


def embed_batch(texts: list[str]) -> torch.Tensor:
    """Return normalized embeddings for a batch of strings. Shape: (N, dim)."""
    model = _get_model()
    with torch.no_grad():
        vectors = model.encode(
            texts, convert_to_tensor=True, device=_DEVICE, batch_size=32,
            show_progress_bar=False,
        )
    return torch.nn.functional.normalize(vectors, dim=-1)


def cosine_similarity(text_a: str, text_b: str) -> float:
    a = embed(text_a)
    b = embed(text_b)
    # embeddings are already normalized, so cosine similarity == dot product
    return torch.dot(a, b).item()


def to_numpy(vector: torch.Tensor) -> np.ndarray:
    """FAISS expects float32 numpy arrays — this is the one conversion point."""
    return vector.detach().cpu().to(torch.float32).numpy()
