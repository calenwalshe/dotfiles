"""Tests for agent runner — claude -p subprocess wrapper."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.runner import AgentResult, AgentRunner


@pytest.fixture
def runner():
    return AgentRunner(timeout_seconds=10)


class TestAgentRunnerPromptBuilding:
    def test_builds_prompt_with_context(self, runner):
        prompt = runner._build_prompt(
            system_prompt="You are a UX researcher.",
            context={"problem": "Users can't find content", "data": {"users": 100}},
            output_schema_hint="Return a JSON object with personas field.",
        )
        assert "UX researcher" in prompt
        assert "Users can't find content" in prompt
        assert '"users": 100' in prompt
        assert "personas" in prompt
        assert "valid JSON" in prompt

    def test_builds_prompt_without_schema_hint(self, runner):
        prompt = runner._build_prompt(
            system_prompt="Test",
            context={},
            output_schema_hint="",
        )
        assert "Test" in prompt


class TestAgentRunnerOutputParsing:
    def test_parses_direct_json(self, runner):
        result = runner._parse_output(
            "test",
            json.dumps({"result": json.dumps({"personas": []})}),
            1.0,
        )
        assert result.success is True
        assert result.artifact == {"personas": []}

    def test_parses_json_with_wrapper(self, runner):
        wrapper = {"type": "result", "result": '{"key": "value"}'}
        result = runner._parse_output("test", json.dumps(wrapper), 1.0)
        assert result.success is True
        assert result.artifact == {"key": "value"}

    def test_handles_malformed_output(self, runner):
        result = runner._parse_output("test", "not json at all", 1.0)
        assert result.success is False
        assert "parse" in result.error.lower() or "JSON" in result.error

    def test_extracts_json_from_mixed_content(self, runner):
        mixed = 'Some preamble\n{"key": "value"}\nSome postamble'
        result = runner._parse_output("test", json.dumps({"result": mixed}), 1.0)
        assert result.success is True
        assert result.artifact == {"key": "value"}


class TestAgentRunnerExecution:
    @patch("src.agents.runner.subprocess.run")
    def test_successful_run(self, mock_run, runner):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": json.dumps({"personas": ["Alice"]})}),
            stderr="",
        )
        result = runner.run("uxr", "You are a UX researcher", {"problem": "test"})
        assert result.success is True
        assert result.artifact == {"personas": ["Alice"]}
        assert result.agent_id == "uxr"

    @patch("src.agents.runner.subprocess.run")
    def test_nonzero_exit(self, mock_run, runner):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: something failed",
        )
        result = runner.run("uxr", "test", {})
        assert result.success is False
        assert "code 1" in result.error

    @patch("src.agents.runner.subprocess.run")
    def test_timeout(self, mock_run, runner):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="claude", timeout=10)
        result = runner.run("uxr", "test", {})
        assert result.success is False
        assert "Timeout" in result.error

    @patch("src.agents.runner.subprocess.run")
    def test_claude_not_found(self, mock_run, runner):
        mock_run.side_effect = FileNotFoundError()
        result = runner.run("uxr", "test", {})
        assert result.success is False
        assert "not found" in result.error


class TestAgentRunnerTokenEstimate:
    def test_estimates_tokens(self, runner):
        tokens = runner._estimate_tokens("a" * 400)
        assert tokens == 100  # 400 chars / 4
