from datetime import datetime

import pytest
from pydantic import ValidationError

from src.schemas.agent_artifacts import (
    ArtifactMetadata,
    CommsRecord,
    DataSourceAssessment,
    DSArtifact,
    EvaluationArtifact,
    ExperimentDesign,
    FeedbackSynthesisArtifact,
    Objection,
    OrchestratorArtifact,
    PMArtifact,
    PressureTestArtifact,
    UXRArtifact,
)
from src.schemas.handoff_package import (
    AlignmentItem,
    ConflictItem,
    EvidenceItem,
    Persona,
    ProductPitch,
    Requirement,
    StakeholderInput,
    SuccessCriterion,
    TestCase,
    TestHarnessConcept,
)


@pytest.fixture
def metadata():
    return ArtifactMetadata(agent_id="test-agent", phase="discovery", run_id="run-001")


class TestOrchestratorArtifact:
    def test_valid_approve(self, metadata):
        artifact = OrchestratorArtifact(
            metadata=metadata,
            gate_decision="approve",
            cited_artifacts=["uxr-001", "pm-001"],
            rationale="All required artifacts present and complete",
            current_understanding="Problem validated; personas grounded in data",
        )
        assert artifact.gate_decision == "approve"
        assert len(artifact.cited_artifacts) == 2

    def test_valid_reject_with_gaps(self, metadata):
        artifact = OrchestratorArtifact(
            metadata=metadata,
            gate_decision="reject",
            cited_artifacts=["uxr-001"],
            rationale="UXR artifact lacks data sources",
            gaps=["Persona 2 has no data_sources", "Missing problem validation evidence"],
            current_understanding="Incomplete discovery",
        )
        assert artifact.gate_decision == "reject"
        assert len(artifact.gaps) == 2

    def test_missing_required_fields(self, metadata):
        with pytest.raises(ValidationError):
            OrchestratorArtifact(metadata=metadata)


class TestUXRArtifact:
    def test_valid(self, metadata):
        artifact = UXRArtifact(
            metadata=metadata,
            personas=[
                Persona(
                    name="Power User",
                    description="Frequent catalog browser",
                    needs=["fast search"],
                    pain_points=["slow results"],
                    data_sources=["session_logs"],
                )
            ],
            problem_validation=[
                EvidenceItem(source="analytics", finding="High bounce rate", confidence="high")
            ],
            user_signals=["low filter usage"],
            methodology="12 user interviews + analytics review",
        )
        assert len(artifact.personas) == 1
        assert artifact.personas[0].name == "Power User"

    def test_empty_valid(self, metadata):
        artifact = UXRArtifact(metadata=metadata)
        assert artifact.personas == []


class TestPMArtifact:
    def test_valid(self, metadata):
        artifact = PMArtifact(
            metadata=metadata,
            product_pitch=ProductPitch(
                title="Smart Discovery",
                summary="AI recommendations",
                value_proposition="Reduce abandonment",
                target_audience="Catalog browsers",
            ),
            requirements=[
                Requirement(
                    id="REQ-01",
                    description="Recommendation engine",
                    priority="critical",
                    rationale="Core value prop",
                    acceptance_criteria=["Returns results in 200ms"],
                )
            ],
            prioritization_rationale="Core engine first",
            stakeholder_comms=[
                CommsRecord(
                    direction="outbound",
                    stakeholder="eng_lead",
                    message_summary="Shared pitch for review",
                )
            ],
        )
        assert artifact.product_pitch.title == "Smart Discovery"
        assert len(artifact.requirements) == 1

    def test_missing_pitch_raises(self, metadata):
        with pytest.raises(ValidationError):
            PMArtifact(metadata=metadata)


class TestDSArtifact:
    def test_valid(self, metadata):
        artifact = DSArtifact(
            metadata=metadata,
            feasibility_assessment="Feasible with existing data pipeline",
            data_availability=[
                DataSourceAssessment(
                    source="clickstream",
                    availability="available",
                    quality="high",
                    gaps=["No data for new users"],
                )
            ],
            experiment_design=ExperimentDesign(
                hypothesis="Recommendations reduce bounce rate",
                methodology="A/B test with 10% traffic",
                metrics=["bounce_rate", "session_depth"],
                sample_requirements="10k users per arm",
            ),
            quantitative_findings=["Current bounce rate: 78%"],
        )
        assert artifact.feasibility_assessment
        assert len(artifact.data_availability) == 1

    def test_missing_feasibility_raises(self, metadata):
        with pytest.raises(ValidationError):
            DSArtifact(metadata=metadata)


class TestEvaluationArtifact:
    def test_valid(self, metadata):
        artifact = EvaluationArtifact(
            metadata=metadata,
            success_criteria=[
                SuccessCriterion(
                    metric="Bounce rate",
                    target="< 30%",
                    measurement_method="Analytics funnel",
                )
            ],
            test_harness_concept=TestHarnessConcept(
                intent="Validate recommendation relevance",
                structure=[
                    TestCase(
                        name="Relevance test",
                        description="Check recommendations match browsed categories",
                        category="functional",
                    )
                ],
                coverage_areas=["relevance", "latency"],
            ),
            eval_schema={"uxr": "rubric_based", "pm": "llm_as_judge"},
        )
        assert len(artifact.success_criteria) == 1
        assert artifact.test_harness_concept.intent

    def test_missing_harness_raises(self, metadata):
        with pytest.raises(ValidationError):
            EvaluationArtifact(metadata=metadata)


class TestPressureTestArtifact:
    def test_valid_with_objections(self, metadata):
        artifact = PressureTestArtifact(
            metadata=metadata,
            objections=[
                Objection(
                    target_claim="Reduce abandonment by 40%",
                    objection="No baseline measurement exists to validate this target",
                    severity="high",
                    evidence="Analytics only tracks page views, not search intent",
                    category="measurement",
                )
            ],
            overall_assessment="Pitch makes unsupported claims about measurable outcomes",
            recommended_actions=["Establish baseline metrics before committing to targets"],
        )
        assert len(artifact.objections) == 1
        assert artifact.objections[0].target_claim

    def test_empty_objections_raises(self, metadata):
        with pytest.raises(ValidationError):
            PressureTestArtifact(
                metadata=metadata,
                objections=[],
                overall_assessment="No issues found",
            )

    def test_objection_requires_target_claim(self, metadata):
        with pytest.raises(ValidationError):
            PressureTestArtifact(
                metadata=metadata,
                objections=[Objection(target_claim="", objection="Generic concern")],
            )


class TestFeedbackSynthesisArtifact:
    def test_valid_with_alignments_and_conflicts(self, metadata):
        artifact = FeedbackSynthesisArtifact(
            metadata=metadata,
            stakeholder_inputs=[
                StakeholderInput(
                    stakeholder="eng_lead",
                    input_text="Discovery is the right problem to solve",
                    sentiment="positive",
                )
            ],
            alignments=[
                AlignmentItem(
                    internal_finding="Users struggle with content discovery",
                    external_input="Eng lead confirms discovery is the gap",
                    assessment="Strong alignment on problem definition",
                )
            ],
            conflicts=[
                ConflictItem(
                    internal_finding="Real-time recommendations needed",
                    external_input="Eng lead prefers batch processing",
                    severity="medium",
                    recommended_resolution="Start batch, add real-time in v2",
                )
            ],
            synthesis_summary="Strong alignment on problem, divergence on implementation approach",
        )
        assert len(artifact.alignments) == 1
        assert len(artifact.conflicts) == 1

    def test_empty_valid(self, metadata):
        artifact = FeedbackSynthesisArtifact(metadata=metadata)
        assert artifact.alignments == []
        assert artifact.conflicts == []
