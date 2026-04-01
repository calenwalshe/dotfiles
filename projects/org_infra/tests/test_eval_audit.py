"""Tests for eval framework — verifies auditable quality scores."""

import pytest

from src.eval.eval_framework import EvalFramework
from src.graph.graph import build_graph
from src.graph.run_config import AutonomyLevel, RunConfig


@pytest.fixture
def framework():
    return EvalFramework()


@pytest.fixture
def run_artifacts():
    """Run the full pipeline and return artifacts."""
    graph = build_graph(RunConfig(autonomy_level=AutonomyLevel.autonomous))
    result = graph.invoke({"problem_statement": "Users cannot discover relevant content"})
    return result["artifacts"]


class TestEvalFramework:
    def test_produces_scores_for_all_agents(self, framework, run_artifacts):
        report = framework.evaluate_run(run_artifacts, run_id="test-001")
        agent_ids = {s.agent_id for s in report.scores}
        expected = {"uxr", "pm", "ds", "evaluation", "pressure_test", "feedback_synthesis"}
        assert expected == agent_ids

    def test_all_scores_are_auditable(self, framework, run_artifacts):
        report = framework.evaluate_run(run_artifacts, run_id="test-001")
        for score in report.scores:
            assert score.agent_id, "Score must have agent_id"
            assert score.dimension, "Score must have dimension"
            assert 0.0 <= score.score <= 1.0, f"Score out of range: {score.score}"
            assert score.rationale, "Score must have rationale"

    def test_overall_pass_on_valid_run(self, framework, run_artifacts):
        report = framework.evaluate_run(run_artifacts, run_id="test-001")
        assert report.overall_pass, f"Expected overall pass, got: {report.summary}"

    def test_summary_format(self, framework, run_artifacts):
        report = framework.evaluate_run(run_artifacts, run_id="test-001")
        assert "/" in report.summary
        assert "passed" in report.summary

    def test_eval_empty_artifacts(self, framework):
        report = framework.evaluate_run({}, run_id="empty")
        assert len(report.scores) == 0
        assert report.overall_pass is True  # vacuously true
