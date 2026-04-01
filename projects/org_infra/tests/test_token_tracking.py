"""Tests for token tracking."""

import json

import pytest

from src.graph.token_tracker import AgentTokenUsage, TokenTracker


class TestAgentTokenUsage:
    def test_total_tokens(self):
        usage = AgentTokenUsage(agent_id="uxr", input_tokens=100, output_tokens=200)
        assert usage.total_tokens == 300

    def test_estimated_cost(self):
        usage = AgentTokenUsage(agent_id="uxr", input_tokens=1_000_000, output_tokens=1_000_000)
        # 1M input at $3 + 1M output at $15 = $18
        assert usage.estimated_cost_usd == 18.0


class TestTokenTracker:
    def test_record_and_total(self):
        tracker = TokenTracker(run_id="test-001")
        tracker.record("uxr", input_tokens=100, output_tokens=200)
        tracker.record("pm", input_tokens=150, output_tokens=300)
        assert tracker.total_tokens == 750

    def test_record_total_splits(self):
        tracker = TokenTracker(run_id="test-001")
        tracker.record_total("uxr", 1000)
        assert tracker.agent_usage["uxr"].input_tokens == 400
        assert tracker.agent_usage["uxr"].output_tokens == 600

    def test_accumulates_for_same_agent(self):
        tracker = TokenTracker(run_id="test-001")
        tracker.record("uxr", input_tokens=100, output_tokens=200)
        tracker.record("uxr", input_tokens=50, output_tokens=100)
        assert tracker.agent_usage["uxr"].total_tokens == 450

    def test_to_dict(self):
        tracker = TokenTracker(run_id="test-001")
        tracker.record("uxr", input_tokens=100, output_tokens=200)
        d = tracker.to_dict()
        assert d["run_id"] == "test-001"
        assert d["total_tokens"] == 300
        assert "uxr" in d["agents"]
        assert d["agents"]["uxr"]["input_tokens"] == 100

    def test_save_to_file(self, tmp_path):
        tracker = TokenTracker(run_id="test-001")
        tracker.record("uxr", input_tokens=100, output_tokens=200)
        path = tracker.save(tmp_path)
        assert "cost.json" in path
        data = json.loads(open(path).read())
        assert data["total_tokens"] == 300

    def test_exceeds_budget(self):
        tracker = TokenTracker(run_id="test-001")
        tracker.record("uxr", input_tokens=500, output_tokens=600)
        assert tracker.exceeds_budget(1000) is True
        assert tracker.exceeds_budget(2000) is False

    def test_empty_tracker(self):
        tracker = TokenTracker(run_id="test-001")
        assert tracker.total_tokens == 0
        assert tracker.total_cost_usd == 0.0
