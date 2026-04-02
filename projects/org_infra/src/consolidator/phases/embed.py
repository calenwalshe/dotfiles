"""Phase 1: Embed — generate embeddings for claims that lack them.

Uses sentence-transformers all-MiniLM-L6-v2 by default.
Accepts an optional embed_fn for dependency injection (testing).
"""

from __future__ import annotations

from typing import Callable
from uuid import UUID

import numpy as np

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.store_adapter import ConsolidatorStore

# Type: text -> numpy array of shape (384,)
EmbedFn = Callable[[list[str]], np.ndarray]

MODEL_NAME = "all-MiniLM-L6-v2"


def _default_embed_fn() -> EmbedFn:
    """Load the real sentence-transformers model. Only called in production."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)

    def encode(texts: list[str]) -> np.ndarray:
        return model.encode(texts, show_progress_bar=False)

    return encode


def run_embed(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
    *,
    embed_fn: EmbedFn | None = None,
) -> list[str]:
    """Embed all claims that don't already have embeddings. Idempotent.

    Args:
        embed_fn: Injectable embedding function. If None, loads the real model.
    """
    actions: list[str] = []

    if embed_fn is None:
        embed_fn = _default_embed_fn()

    # Get all claims
    all_claims = store.query_claims(limit=10000)

    # Filter to those without embeddings
    to_embed = [c for c in all_claims if not store.has_embedding(c.id)]

    if not to_embed:
        return actions

    # Batch encode
    texts = [c.text for c in to_embed]
    embeddings = embed_fn(texts)

    # Store each embedding
    for i, claim in enumerate(to_embed):
        embedding_vec = embeddings[i]
        embedding_bytes = np.array(embedding_vec, dtype=np.float32).tobytes()
        store.write_embedding(claim.id, embedding_bytes, MODEL_NAME)
        action = f"embedded:{claim.id}"
        actions.append(action)
        audit.record(
            phase="embed",
            action="embed",
            claim_id=str(claim.id),
            reason="Generated embedding",
            details={"model": MODEL_NAME, "dim": len(embedding_vec)},
        )

    return actions
