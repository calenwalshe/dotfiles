"""End-to-end tests: full pipeline on synthetic input with real agents."""

import pytest

from src.graph.graph import build_graph
from src.graph.run_config import AutonomyLevel, RunConfig
from src.schemas.handoff_package import HandoffPackage


@pytest.fixture
def graph():
    return build_graph(RunConfig(autonomy_level=AutonomyLevel.autonomous))


PROBLEM = "Users cannot discover relevant content in large catalogs"


class TestEndToEndSynthetic:
    def test_full_pipeline_produces_valid_handoff_package(self, graph):
        result = graph.invoke({"problem_statement": PROBLEM})

        # Verify we reached handoff phase
        assert result["current_phase"] == "handoff"

        # Verify all 3 gates approved
        decisions = result["gate_decisions"]
        assert len(decisions) == 3
        for d in decisions:
            assert d["decision"] == "approve"

        # Verify handoff package is schema-conformant
        package = HandoffPackage(**result["handoff_package"])
        assert package.problem_statement.statement
        assert len(package.user_research.personas) >= 1
        assert package.product_pitch.title
        assert len(package.requirements.build) >= 1
        assert len(package.eval_criteria.success_criteria) >= 1
        assert package.test_harness_concept.intent
        assert len(package.feedback_synthesis.alignments) >= 1
        assert len(package.feedback_synthesis.conflicts) >= 1
        assert len(package.risk_log.risks) >= 1

    def test_all_agents_contributed(self, graph):
        result = graph.invoke({"problem_statement": PROBLEM})
        artifacts = result["artifacts"]
        expected_agents = ["uxr", "pm", "ds", "evaluation", "pressure_test", "feedback_synthesis"]
        for agent in expected_agents:
            assert agent in artifacts, f"Missing artifact from {agent}"

    def test_gate_decisions_cite_artifacts(self, graph):
        result = graph.invoke({"problem_statement": PROBLEM})
        for d in result["gate_decisions"]:
            assert d["cited_artifacts"], f"Gate {d['gate']} has no cited artifacts"
            assert d["rationale"], f"Gate {d['gate']} has no rationale"

    def test_pressure_test_has_specific_objections(self, graph):
        result = graph.invoke({"problem_statement": PROBLEM})
        pt = result["artifacts"]["pressure_test"]
        assert len(pt["objections"]) >= 1
        for obj in pt["objections"]:
            assert obj["target_claim"], "Objection must target a specific claim"
            assert len(obj["target_claim"]) > 5, "Target claim should be substantive"

    def test_feedback_synthesis_has_alignment_and_conflict(self, graph):
        result = graph.invoke({"problem_statement": PROBLEM})
        fs = result["artifacts"]["feedback_synthesis"]
        assert len(fs["alignments"]) >= 1
        assert len(fs["conflicts"]) >= 1
