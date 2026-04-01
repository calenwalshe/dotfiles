from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    problem_statement: str
    run_id: str  # unique run identifier
    current_phase: str  # "discovery" | "definition" | "pitch_evaluation" | "handoff"
    artifacts: dict[str, Any]  # agent_id -> serialized artifact dict
    gate_decisions: list[dict]  # history of gate decisions
    handoff_package: dict | None  # final assembled output
    comms_adapter: Any  # optional CommsAdapter instance
    error: str | None
