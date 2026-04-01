import pytest

from src.agents.orchestrator import ResearchOrchestrator


@pytest.fixture
def orchestrator():
    return ResearchOrchestrator()


def _uxr_artifact(personas=None, problem_validation=None):
    return {
        "metadata": {"agent_id": "uxr", "phase": "discovery", "run_id": "test"},
        "personas": personas
        or [
            {
                "name": "Test User",
                "description": "Test",
                "needs": ["x"],
                "pain_points": ["y"],
                "data_sources": ["logs"],
            }
        ],
        "problem_validation": problem_validation
        or [{"source": "test", "finding": "test finding", "confidence": "high"}],
        "user_signals": ["test signal"],
        "methodology": "test",
    }


def _pm_artifact(requirements=None):
    if requirements is None:
        requirements = [
            {
                "id": "REQ-01",
                "description": "Test req",
                "priority": "high",
                "rationale": "Test",
                "acceptance_criteria": ["Test"],
            }
        ]
    return {
        "metadata": {"agent_id": "pm", "phase": "definition", "run_id": "test"},
        "product_pitch": {
            "title": "Test",
            "summary": "Test",
            "value_proposition": "Test value",
            "target_audience": "Test audience",
        },
        "requirements": requirements,
        "prioritization_rationale": "Test",
        "stakeholder_comms": [],
    }


def _ds_artifact(feasibility="Feasible"):
    return {
        "metadata": {"agent_id": "ds", "phase": "definition", "run_id": "test"},
        "feasibility_assessment": feasibility,
        "data_availability": [],
        "experiment_design": None,
        "quantitative_findings": [],
    }


def _evaluation_artifact():
    return {
        "metadata": {"agent_id": "evaluation", "phase": "pitch_evaluation", "run_id": "test"},
        "success_criteria": [{"metric": "Test", "target": "100%", "measurement_method": "Test"}],
        "test_harness_concept": {
            "intent": "Test validation",
            "structure": [],
            "coverage_areas": ["test"],
        },
        "eval_schema": {},
    }


def _pressure_test_artifact(objections=None):
    if objections is None:
        objections = [
            {
                "target_claim": "Test claim",
                "objection": "Test objection",
                "severity": "medium",
                "evidence": "Test evidence",
                "category": "test",
            }
        ]
    return {
        "metadata": {
            "agent_id": "pressure_test",
            "phase": "pitch_evaluation",
            "run_id": "test",
        },
        "objections": objections,
        "overall_assessment": "Test",
        "recommended_actions": [],
    }


def _feedback_synthesis_artifact():
    return {
        "metadata": {
            "agent_id": "feedback_synthesis",
            "phase": "pitch_evaluation",
            "run_id": "test",
        },
        "stakeholder_inputs": [],
        "alignments": [
            {
                "internal_finding": "Test finding",
                "external_input": "Test input",
                "assessment": "Test",
            }
        ],
        "conflicts": [
            {
                "internal_finding": "Test finding",
                "external_input": "Test conflict",
                "severity": "medium",
                "recommended_resolution": "Test",
            }
        ],
        "synthesis_summary": "Test",
    }


class TestDiscoveryGate:
    def test_approve_valid_uxr(self, orchestrator):
        artifacts = {"uxr": _uxr_artifact()}
        result = orchestrator.evaluate_gate("discovery", artifacts)
        assert result.gate_decision.value == "approve"
        assert "uxr" in result.cited_artifacts
        assert result.gaps == []

    def test_reject_persona_no_data_sources(self, orchestrator):
        uxr = _uxr_artifact(
            personas=[
                {
                    "name": "No Sources",
                    "description": "Test",
                    "needs": [],
                    "pain_points": [],
                    "data_sources": [],
                }
            ]
        )
        result = orchestrator.evaluate_gate("discovery", {"uxr": uxr})
        assert result.gate_decision.value == "reject"
        assert any("data_sources" in g for g in result.gaps)

    def test_reject_missing_uxr(self, orchestrator):
        result = orchestrator.evaluate_gate("discovery", {})
        assert result.gate_decision.value == "reject"
        assert "uxr artifact missing" in result.gaps


class TestDefinitionGate:
    def test_approve_valid(self, orchestrator):
        artifacts = {"pm": _pm_artifact(), "ds": _ds_artifact()}
        result = orchestrator.evaluate_gate("definition", artifacts)
        assert result.gate_decision.value == "approve"
        assert "pm" in result.cited_artifacts
        assert "ds" in result.cited_artifacts

    def test_reject_pm_no_requirements(self, orchestrator):
        artifacts = {"pm": _pm_artifact(requirements=[]), "ds": _ds_artifact()}
        result = orchestrator.evaluate_gate("definition", artifacts)
        assert result.gate_decision.value == "reject"
        assert any("0 requirements" in g for g in result.gaps)


class TestPitchEvaluationGate:
    def test_approve_all_valid(self, orchestrator):
        artifacts = {
            "evaluation": _evaluation_artifact(),
            "pressure_test": _pressure_test_artifact(),
            "feedback_synthesis": _feedback_synthesis_artifact(),
        }
        result = orchestrator.evaluate_gate("pitch_evaluation", artifacts)
        assert result.gate_decision.value == "approve"
        assert len(result.cited_artifacts) == 3

    def test_reject_pressure_test_no_objections(self, orchestrator):
        artifacts = {
            "evaluation": _evaluation_artifact(),
            "pressure_test": _pressure_test_artifact(objections=[]),
            "feedback_synthesis": _feedback_synthesis_artifact(),
        }
        result = orchestrator.evaluate_gate("pitch_evaluation", artifacts)
        assert result.gate_decision.value == "reject"
        assert any("0 objections" in g for g in result.gaps)


class TestUnderstandingDoc:
    def test_includes_persona_info(self, orchestrator):
        artifacts = {"uxr": _uxr_artifact()}
        doc = orchestrator.update_understanding("discovery", artifacts)
        assert "Test User" in doc
        assert "persona" in doc.lower()

    def test_includes_pitch_title(self, orchestrator):
        artifacts = {"uxr": _uxr_artifact(), "pm": _pm_artifact()}
        doc = orchestrator.update_understanding("definition", artifacts)
        assert "Test" in doc
