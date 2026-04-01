import pytest

from src.graph.graph import build_graph
from src.graph.run_config import AutonomyLevel, RunConfig


@pytest.fixture
def graph():
    return build_graph(RunConfig(autonomy_level=AutonomyLevel.autonomous))


@pytest.fixture
def initial_state():
    return {
        "problem_statement": "Users cannot discover relevant content in large catalogs",
    }


class TestGraphBuilds:
    def test_graph_compiles(self, graph):
        assert graph is not None


class TestEndToEnd:
    def test_full_run_produces_handoff_package(self, graph, initial_state):
        result = graph.invoke(initial_state)
        assert result.get("handoff_package") is not None
        assert "metadata" in result["handoff_package"]
        assert "problem_statement" in result["handoff_package"]

    def test_full_run_traverses_all_phases(self, graph, initial_state):
        result = graph.invoke(initial_state)
        decisions = result.get("gate_decisions", [])
        assert len(decisions) == 3  # 3 gates = 4 phases
        gate_names = [d["gate"] for d in decisions]
        assert gate_names == ["discovery", "definition", "pitch_evaluation"]

    def test_all_gates_approve(self, graph, initial_state):
        result = graph.invoke(initial_state)
        decisions = result.get("gate_decisions", [])
        for d in decisions:
            assert d["decision"] == "approve", f"Gate {d['gate']} rejected: {d.get('missing')}"

    def test_final_phase_is_handoff(self, graph, initial_state):
        result = graph.invoke(initial_state)
        assert result["current_phase"] == "handoff"


class TestArtifactPresence:
    def test_all_agents_produce_artifacts(self, graph, initial_state):
        result = graph.invoke(initial_state)
        artifacts = result.get("artifacts", {})
        expected_agents = ["uxr", "pm", "ds", "evaluation", "pressure_test", "feedback_synthesis"]
        for agent in expected_agents:
            assert agent in artifacts, f"Missing artifact from {agent}"

    def test_handoff_package_has_all_sections(self, graph, initial_state):
        result = graph.invoke(initial_state)
        package = result["handoff_package"]
        expected = [
            "problem_statement", "user_research", "product_pitch",
            "requirements", "eval_criteria", "test_harness_concept",
            "feedback_synthesis", "risk_log", "open_assumptions",
        ]
        for section in expected:
            assert section in package, f"Missing section: {section}"
