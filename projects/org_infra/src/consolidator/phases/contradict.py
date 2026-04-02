"""Phase 2: Contradiction Detection — find contradictory claim pairs via NLI.

Cold start (<50 claims): pairwise NLI on all pairs.
Warm (>=50 claims): cluster embeddings with HDBSCAN, then NLI within clusters only.

Accepts optional nli_fn and cluster_fn for dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

import numpy as np

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import Claim, ClaimLevel, Contradiction

# Type: (text_a, text_b) -> contradiction score [0, 1]
NliFn = Callable[[str, str], float]

# Type: embeddings matrix -> list of cluster labels (int, -1 = noise)
ClusterFn = Callable[[np.ndarray], list[int]]


@dataclass
class AmbiguousPair:
    """A pair of claims with ambiguous NLI score — needs Claude review."""
    claim_a_id: UUID
    claim_b_id: UUID
    score: float
    claim_a_text: str
    claim_b_text: str


def _default_nli_fn() -> NliFn:
    """Load the real NLI model. Only called in production."""
    from transformers import pipeline

    nli = pipeline("text-classification", model="cross-encoder/nli-deberta-v3-small")

    def score(text_a: str, text_b: str) -> float:
        result = nli(f"{text_a} [SEP] {text_b}")
        # Find contradiction label score
        for r in result:
            if r["label"].lower() == "contradiction":
                return r["score"]
        return 0.0

    return score


def _default_cluster_fn() -> ClusterFn:
    """Cluster embeddings with HDBSCAN."""
    import hdbscan

    def cluster(embeddings: np.ndarray) -> list[int]:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=3, metric="cosine")
        labels = clusterer.fit_predict(embeddings)
        return labels.tolist()

    return cluster


def _load_embedding(store: ConsolidatorStore, claim_id: UUID) -> np.ndarray | None:
    raw = store.get_embedding(claim_id)
    if raw is None:
        return None
    return np.frombuffer(raw, dtype=np.float32)


def run_contradict(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
    *,
    nli_fn: NliFn | None = None,
    cluster_fn: ClusterFn | None = None,
) -> list[AmbiguousPair]:
    """Detect contradictions among claims. Returns ambiguous pairs for Claude review.

    Args:
        nli_fn: Injectable NLI function. If None, loads the real model.
        cluster_fn: Injectable clustering function. If None, uses HDBSCAN.
    """
    actions: list[str] = []
    ambiguous: list[AmbiguousPair] = []

    if nli_fn is None:
        nli_fn = _default_nli_fn()

    # Get all claims with embeddings
    all_claims = store.query_claims(limit=10000)
    claims_with_emb: list[tuple[Claim, np.ndarray]] = []
    for claim in all_claims:
        emb = _load_embedding(store, claim.id)
        if emb is not None:
            claims_with_emb.append((claim, emb))

    if len(claims_with_emb) < 2:
        return ambiguous

    # Decide strategy: cold start vs clustered
    if len(claims_with_emb) < 50:
        # Cold start: pairwise
        pairs = _pairwise_pairs(claims_with_emb)
    else:
        # Cluster then pairwise within clusters
        if cluster_fn is None:
            cluster_fn = _default_cluster_fn()
        pairs = _clustered_pairs(claims_with_emb, cluster_fn)

    # Run NLI on each pair
    lo, hi = config.nli_ambiguous_range
    for claim_a, claim_b in pairs:
        score = nli_fn(claim_a.text, claim_b.text)

        if score > config.nli_contradiction_threshold:
            # Definite contradiction
            contradiction = Contradiction(
                claim_a_id=claim_a.id,
                claim_b_id=claim_b.id,
            )
            store.write_contradiction(contradiction)
            audit.record(
                phase="contradict",
                action="contradiction",
                claim_id=str(claim_a.id),
                reason=f"Contradicts {claim_b.id} (score={score:.3f})",
                details={
                    "claim_b_id": str(claim_b.id),
                    "nli_score": score,
                },
            )
        elif lo <= score <= hi:
            # Ambiguous — queue for Claude review
            ambiguous.append(AmbiguousPair(
                claim_a_id=claim_a.id,
                claim_b_id=claim_b.id,
                score=score,
                claim_a_text=claim_a.text,
                claim_b_text=claim_b.text,
            ))
            audit.record(
                phase="contradict",
                action="ambiguous",
                claim_id=str(claim_a.id),
                reason=f"Ambiguous contradiction with {claim_b.id} (score={score:.3f})",
                details={
                    "claim_b_id": str(claim_b.id),
                    "nli_score": score,
                },
            )

    return ambiguous


def _pairwise_pairs(
    claims_with_emb: list[tuple[Claim, np.ndarray]],
) -> list[tuple[Claim, Claim]]:
    """Generate all unique pairs (cold start)."""
    pairs = []
    for i in range(len(claims_with_emb)):
        for j in range(i + 1, len(claims_with_emb)):
            pairs.append((claims_with_emb[i][0], claims_with_emb[j][0]))
    return pairs


def _clustered_pairs(
    claims_with_emb: list[tuple[Claim, np.ndarray]],
    cluster_fn: ClusterFn,
) -> list[tuple[Claim, Claim]]:
    """Cluster embeddings, then generate pairs within each cluster."""
    embeddings = np.array([emb for _, emb in claims_with_emb])
    labels = cluster_fn(embeddings)

    # Group by cluster
    clusters: dict[int, list[Claim]] = {}
    for (claim, _), label in zip(claims_with_emb, labels):
        if label == -1:
            continue  # noise
        clusters.setdefault(label, []).append(claim)

    # Pairwise within each cluster
    pairs = []
    for cluster_claims in clusters.values():
        for i in range(len(cluster_claims)):
            for j in range(i + 1, len(cluster_claims)):
                pairs.append((cluster_claims[i], cluster_claims[j]))

    return pairs
