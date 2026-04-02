"""Adapter wrapping SQLiteStore for consolidator-specific operations.

Exposes both StoreProtocol methods (delegated) and the new embedding/archive methods.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.protocols.schemas import (
    Artifact,
    Claim,
    ClaimLevel,
    Contradiction,
    Decision,
    Domain,
    Evidence,
    Experiment,
    Problem,
    ProblemClassification,
    ProblemStatus,
)
from src.protocols.sqlite_store import SQLiteStore
from src.protocols.store import StoreProtocol, ValidatedClaim, RejectedClaim


class ConsolidatorStore(StoreProtocol):
    """Wraps SQLiteStore, adding embedding and archive capabilities."""

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        self._store = sqlite_store

    # --- Delegate StoreProtocol methods ---

    def write_claim(self, claim: Claim) -> UUID:
        return self._store.write_claim(claim)

    def write_evidence(self, evidence: Evidence) -> UUID:
        return self._store.write_evidence(evidence)

    def write_decision(self, decision: Decision) -> UUID:
        return self._store.write_decision(decision)

    def write_experiment(self, experiment: Experiment) -> UUID:
        return self._store.write_experiment(experiment)

    def write_problem(self, problem: Problem) -> UUID:
        return self._store.write_problem(problem)

    def write_artifact(self, artifact: Artifact) -> UUID:
        return self._store.write_artifact(artifact)

    def write_contradiction(self, contradiction: Contradiction) -> UUID:
        return self._store.write_contradiction(contradiction)

    def get_claim(self, claim_id: UUID) -> Claim | None:
        return self._store.get_claim(claim_id)

    def get_decision(self, decision_id: UUID) -> Decision | None:
        return self._store.get_decision(decision_id)

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        return self._store.get_experiment(experiment_id)

    def get_problem(self, problem_id: UUID) -> Problem | None:
        return self._store.get_problem(problem_id)

    def query_claims(
        self,
        *,
        level: ClaimLevel | None = None,
        domain: Domain | None = None,
        topic: str | None = None,
        entity: str | None = None,
        min_confidence: float | None = None,
        valid_at: datetime | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[Claim]:
        return self._store.query_claims(
            level=level, domain=domain, topic=topic, entity=entity,
            min_confidence=min_confidence, valid_at=valid_at, tags=tags, limit=limit,
        )

    def query_evidence(self, *, claim_id: UUID | None = None, limit: int = 100) -> list[Evidence]:
        return self._store.query_evidence(claim_id=claim_id, limit=limit)

    def query_decisions(self, *, topic: str | None = None, limit: int = 100) -> list[Decision]:
        return self._store.query_decisions(topic=topic, limit=limit)

    def query_experiments(
        self, *, kept: bool | None = None, metric_name: str | None = None, limit: int = 100,
    ) -> list[Experiment]:
        return self._store.query_experiments(kept=kept, metric_name=metric_name, limit=limit)

    def query_problems(
        self,
        *,
        status: ProblemStatus | None = None,
        classification: ProblemClassification | None = None,
        min_score: float | None = None,
        limit: int = 100,
    ) -> list[Problem]:
        return self._store.query_problems(
            status=status, classification=classification, min_score=min_score, limit=limit,
        )

    def query_contradictions(
        self, *, unresolved_only: bool = True, limit: int = 100,
    ) -> list[Contradiction]:
        return self._store.query_contradictions(unresolved_only=unresolved_only, limit=limit)

    def search_semantic(self, text: str, top_k: int = 10) -> list[Claim | Evidence]:
        return self._store.search_semantic(text, top_k)

    def search_lexical(self, text: str, top_k: int = 10) -> list[Claim | Evidence]:
        return self._store.search_lexical(text, top_k)

    def validate_recall(self, claim: Claim) -> ValidatedClaim | RejectedClaim:
        return self._store.validate_recall(claim)

    def update_claim(self, claim_id: UUID, **fields) -> Claim:
        return self._store.update_claim(claim_id, **fields)

    def update_problem(self, problem_id: UUID, **fields) -> Problem:
        return self._store.update_problem(problem_id, **fields)

    def close(self) -> None:
        self._store.close()

    # --- Consolidator-specific: Embeddings ---

    def write_embedding(self, claim_id: UUID, embedding: bytes, model: str) -> None:
        self._store.write_embedding(claim_id, embedding, model)

    def get_embedding(self, claim_id: UUID) -> bytes | None:
        return self._store.get_embedding(claim_id)

    def has_embedding(self, claim_id: UUID) -> bool:
        return self._store.has_embedding(claim_id)

    # --- Consolidator-specific: Archive ---

    def archive_claim(self, claim_id: UUID, reason: str) -> None:
        self._store.archive_claim(claim_id, reason)

    def query_archive(self, limit: int = 100) -> list[dict]:
        return self._store.query_archive(limit)
