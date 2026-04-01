"""Tests for LLM-enhanced Orchestrator."""

import json
from unittest.mock import MagicMock

import pytest

from src.agents.llm_orchestrator import LLMOrchestrator
from src.agents.runner import AgentResult


def _uxr_artifact():
    return {
        "metadata": {"agent_id": "uxr", "phase": "discovery", "run_id": "test"},
        "personas": [
            {"name": "User", "description": "Test", "needs": [], "pain_points": [], "data_sources": ["logs"]}
        ],
        "problem_validation": [{"source": "test", "finding": "Valid", "confidence": "high"}],
        "user_signals": ["signal"],
        "methodology": "test",
    }


class TestLLMOrchestratorWithoutRunner:
    def test_falls_back_to_rule_based(self):
        orch = LLMOrchestrator(runner=None)
        result = orch.evaluate_gate("discovery", {"uxr": _uxr_artifact()})
        assert result.gate_decision.value == "approve"
        assert "uxr" in result.cited_artifacts

    def test_reject_still_works(self):
        orch = LLMOrchestrator(runner=None)
        result = orch.evaluate_gate("discovery", {})
        assert result.gate_decision.value == "reject"


class TestLLMOrchestratorWithRunner:
    def test_enhances_rationale_on_approve(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = AgentResult(
            agent_id="orchestrator",
            success=True,
            artifact={
                "rationale": "LLM-enhanced: UXR artifact has well-grounded personas with log data.",
                "actionable_feedback": [],
            },
        )

        orch = LLMOrchestrator(runner=mock_runner)
        result = orch.evaluate_gate("discovery", {"uxr": _uxr_artifact()})
        assert result.gate_decision.value == "approve"
        assert "LLM-enhanced" in result.rationale

    def test_enhances_rationale_on_reject(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = AgentResult(
            agent_id="orchestrator",
            success=True,
            artifact={
                "rationale": "Missing UXR artifact entirely.",
                "actionable_feedback": ["Run UXR agent before gate evaluation"],
            },
        )

        orch = LLMOrchestrator(runner=mock_runner)
        result = orch.evaluate_gate("discovery", {})
        assert result.gate_decision.value == "reject"
        assert "Actionable feedback" in result.rationale

    def test_falls_back_on_runner_failure(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = AgentResult(
            agent_id="orchestrator",
            success=False,
            error="Timeout",
        )

        orch = LLMOrchestrator(runner=mock_runner)
        result = orch.evaluate_gate("discovery", {"uxr": _uxr_artifact()})
        # Should still approve based on rule-based checks
        assert result.gate_decision.value == "approve"
        # Rationale should be rule-based (not LLM-enhanced)
        assert "LLM" not in result.rationale

    def test_rule_based_decision_not_overridden(self):
        """LLM can enhance rationale but cannot change the gate decision."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = AgentResult(
            agent_id="orchestrator",
            success=True,
            artifact={"rationale": "Looks good!", "actionable_feedback": []},
        )

        orch = LLMOrchestrator(runner=mock_runner)
        # Empty artifacts = rule-based reject
        result = orch.evaluate_gate("discovery", {})
        # Decision must still be reject (LLM cannot override)
        assert result.gate_decision.value == "reject"
