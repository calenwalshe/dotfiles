"""The six core protocols + supporting types.

Every component in the system reads and writes these types through the Store API.
No component calls another directly. These schemas ARE the interfaces.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> UUID:
    return uuid4()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ClaimLevel(str, Enum):
    """Knowledge maturation level."""

    L0 = "L0"  # raw — ingested, unprocessed
    L1 = "L1"  # extracted — atomic fact with provenance
    L2 = "L2"  # validated — corroborated, survived contradiction check
    L3 = "L3"  # actionable — promoted to active knowledge


class Domain(str, Enum):
    codebase = "codebase"
    product = "product"
    competitive = "competitive"
    user = "user"
    operational = "operational"


class SourceType(str, Enum):
    file = "file"
    url = "url"
    commit = "commit"
    conversation = "conversation"
    experiment = "experiment"
    api = "api"


class EvidenceStrength(str, Enum):
    supports = "supports"
    contradicts = "contradicts"
    neutral = "neutral"


class ProblemClassification(str, Enum):
    open_ended = "open-ended"
    bounded = "bounded"
    hybrid = "hybrid"
    unclassified = "unclassified"


class ProblemStatus(str, Enum):
    discovered = "discovered"
    approved = "approved"
    in_progress = "in-progress"
    completed = "completed"
    rejected = "rejected"


class ArtifactType(str, Enum):
    spec = "spec"
    contract = "contract"
    handoff_package = "handoff-package"
    report = "report"
    projection = "projection"
    code = "code"


# ---------------------------------------------------------------------------
# Protocol 1: Claim
# ---------------------------------------------------------------------------


class Claim(BaseModel):
    """The atomic unit of knowledge. Everything the system knows is a Claim."""

    id: UUID = Field(default_factory=_uuid)
    text: str = Field(..., min_length=1, description="Human-readable assertion")
    level: ClaimLevel = ClaimLevel.L0
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    domain: Domain = Domain.operational
    topic: str = Field("", description="Free-text tag for grouping")
    entity: str | None = Field(None, description="Specific thing/person this is about")
    source_type: SourceType = SourceType.conversation
    source_ref: str = Field("", description="Path, URL, SHA, or session ID")
    valid_from: datetime = Field(default_factory=_now)
    valid_until: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    promoted_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Protocol 2: Evidence
# ---------------------------------------------------------------------------


class Evidence(BaseModel):
    """Links to a Claim. Supports, contradicts, or is neutral."""

    id: UUID = Field(default_factory=_uuid)
    claim_id: UUID
    content: str = Field(..., min_length=1)
    strength: EvidenceStrength = EvidenceStrength.supports
    source_type: SourceType = SourceType.conversation
    source_ref: str = ""
    timestamp: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Protocol 3: Decision
# ---------------------------------------------------------------------------


class RejectedAlternative(BaseModel):
    option: str
    reason: str


class Decision(BaseModel):
    """A choice made by any component, with full reasoning."""

    id: UUID = Field(default_factory=_uuid)
    topic: str = Field(..., min_length=1)
    chosen_option: str = Field(..., min_length=1)
    reasoning: str = Field(..., min_length=1, description="Why this, not that")
    alternatives_rejected: list[RejectedAlternative] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=_now)
    outcome: str | None = Field(None, description="Filled in post-hoc if evaluated")


# ---------------------------------------------------------------------------
# Protocol 4: Experiment
# ---------------------------------------------------------------------------


class Experiment(BaseModel):
    """A hypothesis tested empirically. Written by any execution engine."""

    id: UUID = Field(default_factory=_uuid)
    hypothesis: str = Field(..., min_length=1)
    method: str = ""
    inputs: dict = Field(default_factory=dict)
    outputs: dict = Field(default_factory=dict)
    metric_name: str = ""
    metric_value: float | None = None
    baseline_value: float | None = None
    kept: bool = False
    commit_sha: str | None = None
    duration_seconds: float | None = None
    timestamp: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Protocol 5: Problem
# ---------------------------------------------------------------------------


class Problem(BaseModel):
    """A discovered issue worth investigating."""

    id: UUID = Field(default_factory=_uuid)
    description: str = Field(..., min_length=1)
    source_claim_ids: list[UUID] = Field(default_factory=list)
    impact: float = Field(0.5, ge=0.0, le=1.0)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    actionability: float = Field(0.5, ge=0.0, le=1.0)
    classification: ProblemClassification = ProblemClassification.unclassified
    status: ProblemStatus = ProblemStatus.discovered
    timestamp: datetime = Field(default_factory=_now)

    @property
    def score(self) -> float:
        return self.impact * self.confidence * self.actionability


# ---------------------------------------------------------------------------
# Protocol 6: Artifact
# ---------------------------------------------------------------------------


class Artifact(BaseModel):
    """Any file or document produced by a component."""

    id: UUID = Field(default_factory=_uuid)
    type: ArtifactType = ArtifactType.report
    path: str = Field(..., min_length=1, description="Where it lives on disk")
    produced_by: str = Field(..., min_length=1, description="Component name")
    timestamp: datetime = Field(default_factory=_now)
    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Supporting: Contradiction (used by Consolidator)
# ---------------------------------------------------------------------------


class Contradiction(BaseModel):
    """Two claims that conflict. Detected by Consolidator, resolved by human or agent."""

    id: UUID = Field(default_factory=_uuid)
    claim_a_id: UUID
    claim_b_id: UUID
    detected_at: datetime = Field(default_factory=_now)
    resolved_at: datetime | None = None
    resolution: str | None = Field(None, description="Which won and why")
