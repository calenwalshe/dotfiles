"""Phase 3: Corroborate — find independently corroborated L1 claims via embedding similarity.

Two claims corroborate each other if:
1. Cosine similarity > threshold (0.85)
2. They come from independent sources (different source_type OR different source_ref)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import numpy as np

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import Claim, ClaimLevel


@dataclass
class CorroborationResult:
    claim_id: UUID
    corroboration_count: int
    corroborating_claim_ids: list[UUID] = field(default_factory=list)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _are_independent(a: Claim, b: Claim) -> bool:
    """Two claims are independent if they differ in source_type or source_ref."""
    return a.source_type != b.source_type or a.source_ref != b.source_ref


def _load_embedding(store: ConsolidatorStore, claim_id: UUID) -> np.ndarray | None:
    raw = store.get_embedding(claim_id)
    if raw is None:
        return None
    return np.frombuffer(raw, dtype=np.float32)


def run_corroborate(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
) -> list[CorroborationResult]:
    """Find L1 claims with >= 2 independent corroborations.

    Returns list of CorroborationResult for claims eligible for L1->L2 promotion.
    """
    l1_claims = store.query_claims(level=ClaimLevel.L1, limit=10000)

    # Load embeddings for all L1 claims
    claims_with_embeddings: list[tuple[Claim, np.ndarray]] = []
    for claim in l1_claims:
        emb = _load_embedding(store, claim.id)
        if emb is not None:
            claims_with_embeddings.append((claim, emb))

    # For each claim, find independent corroborators
    corroboration_map: dict[UUID, list[UUID]] = {}

    for i, (claim_a, emb_a) in enumerate(claims_with_embeddings):
        for j, (claim_b, emb_b) in enumerate(claims_with_embeddings):
            if i >= j:
                continue

            sim = _cosine_similarity(emb_a, emb_b)
            if sim > config.cosine_corroboration_threshold:
                # Check source independence
                if _are_independent(claim_a, claim_b):
                    corroboration_map.setdefault(claim_a.id, []).append(claim_b.id)
                    corroboration_map.setdefault(claim_b.id, []).append(claim_a.id)

    # Filter to claims with >= 2 independent corroborations
    results: list[CorroborationResult] = []
    for claim_id, corroborators in corroboration_map.items():
        if len(corroborators) >= 2:
            result = CorroborationResult(
                claim_id=claim_id,
                corroboration_count=len(corroborators),
                corroborating_claim_ids=corroborators,
            )
            results.append(result)
            audit.record(
                phase="corroborate",
                action="corroborated",
                claim_id=str(claim_id),
                reason=f"Found {len(corroborators)} independent corroborations",
                details={"corroborating_ids": [str(c) for c in corroborators]},
            )

    return results
