from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Priority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


# --- Sub-models for each handoff package section ---


class EvidenceItem(BaseModel):
    source: str
    finding: str
    confidence: str = "medium"


class ProblemStatement(BaseModel):
    statement: str = Field(..., description="Validated problem statement")
    evidence: list[EvidenceItem] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    validated: bool = False


class Persona(BaseModel):
    name: str
    description: str
    needs: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)


class UserResearch(BaseModel):
    personas: list[Persona] = Field(default_factory=list)
    problem_validation: list[EvidenceItem] = Field(default_factory=list)
    user_signals: list[str] = Field(default_factory=list)
    methodology: str = ""


class ProductPitch(BaseModel):
    title: str
    summary: str
    value_proposition: str
    target_audience: str
    differentiation: str = ""


class Requirement(BaseModel):
    id: str
    description: str
    priority: Priority
    rationale: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)


class Requirements(BaseModel):
    build: list[Requirement] = Field(default_factory=list, description="What to build")
    not_build: list[str] = Field(default_factory=list, description="What not to build, with reasons")
    prioritization_rationale: str = ""


class SuccessCriterion(BaseModel):
    metric: str
    target: str
    measurement_method: str = ""


class EvalCriteria(BaseModel):
    success_criteria: list[SuccessCriterion] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


class TestCase(BaseModel):
    name: str
    description: str
    category: str = ""
    expected_behavior: str = ""


class TestHarnessConcept(BaseModel):
    intent: str = Field(..., description="What the test harness is designed to validate")
    structure: list[TestCase] = Field(default_factory=list)
    coverage_areas: list[str] = Field(default_factory=list)


class StakeholderInput(BaseModel):
    stakeholder: str
    input_text: str
    sentiment: str = ""


class AlignmentItem(BaseModel):
    internal_finding: str
    external_input: str
    assessment: str = ""


class ConflictItem(BaseModel):
    internal_finding: str
    external_input: str
    severity: Severity = Severity.medium
    recommended_resolution: str = ""


class FeedbackSynthesis(BaseModel):
    stakeholder_inputs: list[StakeholderInput] = Field(default_factory=list)
    alignments: list[AlignmentItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)


class Risk(BaseModel):
    id: str
    description: str
    severity: Severity
    likelihood: str = "medium"
    mitigation: str = ""
    owner: str = ""


class RiskLog(BaseModel):
    risks: list[Risk] = Field(default_factory=list)


class Assumption(BaseModel):
    statement: str
    status: str = "open"
    owner: str = "engineering"
    resolution_needed_by: str = ""


class OpenAssumptions(BaseModel):
    assumptions: list[Assumption] = Field(default_factory=list)


class PackageMetadata(BaseModel):
    schema_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    run_id: str = ""
    source_agents: list[str] = Field(default_factory=list)


# --- Top-level handoff package ---


class HandoffPackage(BaseModel):
    metadata: PackageMetadata = Field(default_factory=PackageMetadata)
    problem_statement: ProblemStatement
    user_research: UserResearch
    product_pitch: ProductPitch
    requirements: Requirements
    eval_criteria: EvalCriteria
    test_harness_concept: TestHarnessConcept
    feedback_synthesis: FeedbackSynthesis
    risk_log: RiskLog
    open_assumptions: OpenAssumptions
