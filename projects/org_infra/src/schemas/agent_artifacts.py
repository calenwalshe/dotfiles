from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.schemas.handoff_package import (
    AlignmentItem,
    ConflictItem,
    EvidenceItem,
    Persona,
    ProductPitch,
    Requirement,
    Severity,
    StakeholderInput,
    SuccessCriterion,
    TestHarnessConcept,
)


class GateDecision(str, Enum):
    approve = "approve"
    reject = "reject"


class ArtifactMetadata(BaseModel):
    agent_id: str
    phase: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: str = ""


# --- Agent 1: Research Orchestrator ---


class OrchestratorArtifact(BaseModel):
    metadata: ArtifactMetadata
    gate_decision: GateDecision
    cited_artifacts: list[str] = Field(
        ..., description="Artifact IDs that informed the decision"
    )
    rationale: str = Field(..., description="Structured reasoning for the decision")
    gaps: list[str] = Field(
        default_factory=list, description="Specific gaps if rejecting"
    )
    current_understanding: str = Field(
        ..., description="Maintained best-current-understanding document"
    )


# --- Agent 2: UX Research ---


class UXRArtifact(BaseModel):
    metadata: ArtifactMetadata
    personas: list[Persona] = Field(default_factory=list)
    problem_validation: list[EvidenceItem] = Field(default_factory=list)
    user_signals: list[str] = Field(default_factory=list)
    methodology: str = ""


# --- Agent 3: PM ---


class CommsRecord(BaseModel):
    direction: str  # "outbound" | "inbound"
    stakeholder: str
    message_summary: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PMArtifact(BaseModel):
    metadata: ArtifactMetadata
    product_pitch: ProductPitch
    requirements: list[Requirement] = Field(default_factory=list)
    prioritization_rationale: str = ""
    stakeholder_comms: list[CommsRecord] = Field(default_factory=list)


# --- Agent 4: Data Science ---


class DataSourceAssessment(BaseModel):
    source: str
    availability: str  # "available" | "partial" | "unavailable"
    quality: str = ""
    gaps: list[str] = Field(default_factory=list)


class ExperimentDesign(BaseModel):
    hypothesis: str
    methodology: str
    metrics: list[str] = Field(default_factory=list)
    sample_requirements: str = ""


class DSArtifact(BaseModel):
    metadata: ArtifactMetadata
    feasibility_assessment: str
    data_availability: list[DataSourceAssessment] = Field(default_factory=list)
    experiment_design: ExperimentDesign | None = None
    quantitative_findings: list[str] = Field(default_factory=list)


# --- Agent 5: Evaluation ---


class EvaluationArtifact(BaseModel):
    metadata: ArtifactMetadata
    success_criteria: list[SuccessCriterion] = Field(default_factory=list)
    test_harness_concept: TestHarnessConcept
    eval_schema: dict = Field(
        default_factory=dict, description="How to score each artifact type"
    )


# --- Agent 6: Pressure Testing ---


class Objection(BaseModel):
    target_claim: str = Field(..., min_length=1, description="The specific claim being challenged")
    objection: str = Field(..., description="The adversarial challenge")
    severity: Severity = Severity.medium
    evidence: str = ""
    category: str = ""


class PressureTestArtifact(BaseModel):
    metadata: ArtifactMetadata
    objections: list[Objection] = Field(
        ..., min_length=1, description="Must have at least one objection"
    )
    overall_assessment: str = ""
    recommended_actions: list[str] = Field(default_factory=list)


# --- Agent 7: Feedback Synthesis ---


class FeedbackSynthesisArtifact(BaseModel):
    metadata: ArtifactMetadata
    stakeholder_inputs: list[StakeholderInput] = Field(default_factory=list)
    alignments: list[AlignmentItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    synthesis_summary: str = ""
