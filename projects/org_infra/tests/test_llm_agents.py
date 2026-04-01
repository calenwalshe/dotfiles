"""Tests for LLM agent node factory and prompt library."""

import pytest

from src.agents.llm_agents import make_llm_node
from src.agents.prompts.agent_prompts import AGENT_PROMPTS, SCHEMA_HINTS


class TestPromptLibrary:
    def test_all_agents_have_prompts(self):
        expected = {"uxr", "pm", "ds", "evaluation", "pressure_test", "feedback_synthesis"}
        assert expected == set(AGENT_PROMPTS.keys())

    def test_all_agents_have_schema_hints(self):
        expected = {"uxr", "pm", "ds", "evaluation", "pressure_test", "feedback_synthesis"}
        assert expected == set(SCHEMA_HINTS.keys())

    def test_prompts_are_substantive(self):
        for agent_id, prompt in AGENT_PROMPTS.items():
            assert len(prompt) > 100, f"{agent_id} prompt too short"
            assert "Rules:" in prompt, f"{agent_id} prompt missing rules"

    def test_schema_hints_are_valid_json_templates(self):
        for agent_id, hint in SCHEMA_HINTS.items():
            assert "metadata" in hint, f"{agent_id} schema hint missing metadata"
            assert agent_id in hint, f"{agent_id} schema hint doesn't reference own agent_id"


class TestLLMNodeFactory:
    def test_creates_node_with_fallback(self):
        def fallback(state):
            artifacts = dict(state.get("artifacts", {}))
            artifacts["uxr"] = {"fallback": True}
            return {"artifacts": artifacts}

        node = make_llm_node(
            agent_id="uxr",
            phase="discovery",
            context_keys=[],
            runner=None,  # No runner — should use fallback
            fallback=fallback,
        )

        result = node({"problem_statement": "test", "artifacts": {}})
        assert result["artifacts"]["uxr"]["fallback"] is True

    def test_node_without_runner_or_fallback_produces_error(self):
        node = make_llm_node(
            agent_id="uxr",
            phase="discovery",
            context_keys=[],
            runner=None,
            fallback=None,
        )

        result = node({"problem_statement": "test", "artifacts": {}})
        assert "error" in result["artifacts"]["uxr"]

    def test_node_injects_context_from_artifacts(self):
        """Verify the node passes artifact context to the runner."""
        from unittest.mock import MagicMock
        from src.agents.runner import AgentResult

        mock_runner = MagicMock()
        mock_runner.run.return_value = AgentResult(
            agent_id="pm",
            success=True,
            artifact={"product_pitch": {"title": "test"}},
            tokens_used=50,
        )

        node = make_llm_node(
            agent_id="pm",
            phase="definition",
            context_keys=["uxr"],
            runner=mock_runner,
        )

        state = {
            "problem_statement": "test problem",
            "artifacts": {"uxr": {"personas": []}},
        }
        result = node(state)

        # Verify runner was called with uxr context
        call_args = mock_runner.run.call_args
        context = call_args.kwargs.get("context") or call_args[0][2]
        assert "uxr" in context
        assert result["artifacts"]["pm"]["product_pitch"]["title"] == "test"
        assert result["tokens_used"] == 50
