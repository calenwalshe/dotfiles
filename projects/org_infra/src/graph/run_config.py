"""Run configuration for HITL autonomy levels and budgets."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AutonomyLevel(str, Enum):
    autonomous = "autonomous"  # No human stops; circuit breaker only
    supervised = "supervised"  # Stops at phase gates for human review
    guided = "guided"  # Stops after every agent node


@dataclass
class RunConfig:
    autonomy_level: AutonomyLevel = AutonomyLevel.supervised
    token_budget: int = 100_000
    time_budget_seconds: int = 600
    max_gate_retries: int = 3
    run_id: str = ""
