"""Store protocol — the abstract interface every component talks to.

Implementations (SQLite, Postgres, flat-file) are adapters behind this interface.
Components import StoreProtocol, never a concrete backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
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


class RecallResult(ABC):
    """Base for recall query results with validation metadata."""


class ValidatedClaim(Claim):
    """A Claim that passed the retrieval-as-proposal gate."""

    validation_passed: bool = True
    validation_note: str = ""


class RejectedClaim(Claim):
    """A Claim that failed the retrieval-as-proposal gate."""

    validation_passed: bool = False
    rejection_reason: str = ""


class StoreProtocol(ABC):
    """Abstract store interface. Every component programs against this."""

    # --- Write ---

    @abstractmethod
    def write_claim(self, claim: Claim) -> UUID: ...

    @abstractmethod
    def write_evidence(self, evidence: Evidence) -> UUID: ...

    @abstractmethod
    def write_decision(self, decision: Decision) -> UUID: ...

    @abstractmethod
    def write_experiment(self, experiment: Experiment) -> UUID: ...

    @abstractmethod
    def write_problem(self, problem: Problem) -> UUID: ...

    @abstractmethod
    def write_artifact(self, artifact: Artifact) -> UUID: ...

    @abstractmethod
    def write_contradiction(self, contradiction: Contradiction) -> UUID: ...

    # --- Read by ID ---

    @abstractmethod
    def get_claim(self, claim_id: UUID) -> Claim | None: ...

    @abstractmethod
    def get_decision(self, decision_id: UUID) -> Decision | None: ...

    @abstractmethod
    def get_experiment(self, experiment_id: UUID) -> Experiment | None: ...

    @abstractmethod
    def get_problem(self, problem_id: UUID) -> Problem | None: ...

    # --- Query ---

    @abstractmethod
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
    ) -> list[Claim]: ...

    @abstractmethod
    def query_evidence(
        self,
        *,
        claim_id: UUID | None = None,
        limit: int = 100,
    ) -> list[Evidence]: ...

    @abstractmethod
    def query_decisions(
        self,
        *,
        topic: str | None = None,
        limit: int = 100,
    ) -> list[Decision]: ...

    @abstractmethod
    def query_experiments(
        self,
        *,
        kept: bool | None = None,
        metric_name: str | None = None,
        limit: int = 100,
    ) -> list[Experiment]: ...

    @abstractmethod
    def query_problems(
        self,
        *,
        status: ProblemStatus | None = None,
        classification: ProblemClassification | None = None,
        min_score: float | None = None,
        limit: int = 100,
    ) -> list[Problem]: ...

    @abstractmethod
    def query_contradictions(
        self,
        *,
        unresolved_only: bool = True,
        limit: int = 100,
    ) -> list[Contradiction]: ...

    # --- Search ---

    @abstractmethod
    def search_semantic(
        self,
        text: str,
        top_k: int = 10,
    ) -> list[Claim | Evidence]: ...

    @abstractmethod
    def search_lexical(
        self,
        text: str,
        top_k: int = 10,
    ) -> list[Claim | Evidence]: ...

    # --- Retrieval-as-Proposal Gate ---

    @abstractmethod
    def validate_recall(self, claim: Claim) -> ValidatedClaim | RejectedClaim:
        """Check a recalled Claim before committing it to agent working memory.

        Checks:
        1. Source still exists (file path, URL, commit SHA)
        2. Freshness (not past domain decay threshold)
        3. No contradicting L2/L3 claims
        4. Confidence above threshold for this decision type

        Returns ValidatedClaim if all checks pass, RejectedClaim with reason if not.
        """
        ...

    # --- Update ---

    @abstractmethod
    def update_claim(self, claim_id: UUID, **fields) -> Claim: ...

    @abstractmethod
    def update_problem(self, problem_id: UUID, **fields) -> Problem: ...

    # --- Lifecycle ---

    @abstractmethod
    def close(self) -> None: ...
