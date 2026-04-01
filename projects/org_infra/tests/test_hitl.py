"""Tests for HITL framework — autonomy levels and circuit breaker."""

import time

import pytest

from src.graph.circuit_breaker import CircuitBreaker
from src.graph.graph import AGENT_NODES, GATE_NODES, build_graph
from src.graph.run_config import AutonomyLevel, RunConfig


PROBLEM = "Users cannot discover relevant content in large catalogs"


class TestRunConfig:
    def test_defaults_to_supervised(self):
        config = RunConfig()
        assert config.autonomy_level == AutonomyLevel.supervised

    def test_all_levels_valid(self):
        for level in AutonomyLevel:
            config = RunConfig(autonomy_level=level)
            assert config.autonomy_level == level


class TestAutonomousMode:
    def test_runs_to_completion(self):
        config = RunConfig(autonomy_level=AutonomyLevel.autonomous)
        graph = build_graph(config)
        result = graph.invoke({"problem_statement": PROBLEM})
        assert result.get("handoff_package") is not None
        assert result["current_phase"] == "handoff"

    def test_no_interrupts(self):
        config = RunConfig(autonomy_level=AutonomyLevel.autonomous)
        graph = build_graph(config)
        # Autonomous graph should run to completion in a single invoke
        result = graph.invoke({"problem_statement": PROBLEM})
        assert len(result.get("gate_decisions", [])) == 3


class TestSupervisedMode:
    def test_compiles_with_gate_interrupts(self):
        config = RunConfig(autonomy_level=AutonomyLevel.supervised)
        graph = build_graph(config)
        # Graph should compile — interrupt_before is a compile-time config
        assert graph is not None


class TestGuidedMode:
    def test_compiles_with_all_interrupts(self):
        config = RunConfig(autonomy_level=AutonomyLevel.guided)
        graph = build_graph(config)
        assert graph is not None


class TestCircuitBreakerBudget:
    def test_trips_on_token_budget(self):
        config = RunConfig(token_budget=1000)
        cb = CircuitBreaker(config=config)
        cb.record_tokens(1001)
        tripped, reason = cb.check_budget()
        assert tripped is True
        assert "Token budget" in reason

    def test_no_trip_under_budget(self):
        config = RunConfig(token_budget=1000)
        cb = CircuitBreaker(config=config)
        cb.record_tokens(500)
        tripped, _ = cb.check_budget()
        assert tripped is False

    def test_trips_on_time_budget(self):
        config = RunConfig(time_budget_seconds=0)
        cb = CircuitBreaker(config=config, start_time=time.time() - 1)
        tripped, reason = cb.check_budget()
        assert tripped is True
        assert "Time budget" in reason

    def test_should_halt_combines_checks(self):
        config = RunConfig(token_budget=100)
        cb = CircuitBreaker(config=config)
        cb.record_tokens(200)
        tripped, reason = cb.should_halt()
        assert tripped is True


class TestCircuitBreakerPlateau:
    def test_detects_plateau(self):
        config = RunConfig()
        cb = CircuitBreaker(config=config)
        cb.check_eval_plateau(0.7)
        _, _ = cb.check_eval_plateau(0.7)  # same score
        tripped, reason = cb.check_eval_plateau(0.7)  # still same
        assert tripped is True
        assert "plateau" in reason.lower()

    def test_no_plateau_when_improving(self):
        config = RunConfig()
        cb = CircuitBreaker(config=config)
        cb.check_eval_plateau(0.5)
        tripped, _ = cb.check_eval_plateau(0.7)
        assert tripped is False

    def test_no_plateau_on_single_score(self):
        config = RunConfig()
        cb = CircuitBreaker(config=config)
        tripped, _ = cb.check_eval_plateau(0.8)
        assert tripped is False


class TestBackwardCompatibility:
    def test_default_build_graph_still_works(self):
        graph = build_graph()
        assert graph is not None

    def test_existing_e2e_still_passes(self):
        config = RunConfig(autonomy_level=AutonomyLevel.autonomous)
        graph = build_graph(config)
        result = graph.invoke({"problem_statement": PROBLEM})
        assert result["current_phase"] == "handoff"
        assert len(result["gate_decisions"]) == 3
