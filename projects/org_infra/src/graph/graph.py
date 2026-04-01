"""LangGraph state machine for the research-to-engineering handoff pipeline.

Four phases: Discovery → Definition → Pitch & Evaluation → Handoff.
Stub nodes produce minimal valid artifacts. Gate nodes check artifact
presence before advancing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.orchestrator import ResearchOrchestrator
from src.graph.state import GraphState

_orchestrator = ResearchOrchestrator()


def _metadata(agent_id: str, phase: str) -> dict:
    return {
        "agent_id": agent_id,
        "phase": phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": "stub-run",
    }


# --- Stub agent nodes ---


def orchestrator_intake(state: GraphState) -> dict[str, Any]:
    """Parse problem statement and initialize pipeline."""
    return {
        "current_phase": "discovery",
        "artifacts": state.get("artifacts", {}),
        "gate_decisions": [],
    }


def uxr_node(state: GraphState) -> dict[str, Any]:
    """UX Research stub — produces minimal valid artifact."""
    artifacts = dict(state.get("artifacts", {}))
    artifacts["uxr"] = {
        "metadata": _metadata("uxr", "discovery"),
        "personas": [
            {
                "name": "Stub Persona",
                "description": "Auto-generated stub persona",
                "needs": ["placeholder"],
                "pain_points": ["placeholder"],
                "data_sources": ["stub"],
            }
        ],
        "problem_validation": [
            {"source": "stub", "finding": "Stub validation", "confidence": "low"}
        ],
        "user_signals": ["stub signal"],
        "methodology": "Stub — no real research",
    }
    return {"artifacts": artifacts}


def pm_node(state: GraphState) -> dict[str, Any]:
    """PM stub — produces minimal valid artifact."""
    artifacts = dict(state.get("artifacts", {}))
    artifacts["pm"] = {
        "metadata": _metadata("pm", "definition"),
        "product_pitch": {
            "title": "Stub Pitch",
            "summary": "Stub summary",
            "value_proposition": "Stub value",
            "target_audience": "Stub audience",
        },
        "requirements": [
            {
                "id": "STUB-01",
                "description": "Stub requirement",
                "priority": "medium",
                "rationale": "Stub",
                "acceptance_criteria": ["Stub criterion"],
            }
        ],
        "prioritization_rationale": "Stub ordering",
        "stakeholder_comms": [],
    }
    return {"artifacts": artifacts}


def ds_node(state: GraphState) -> dict[str, Any]:
    """Data Science stub — produces minimal valid artifact."""
    artifacts = dict(state.get("artifacts", {}))
    artifacts["ds"] = {
        "metadata": _metadata("ds", "definition"),
        "feasibility_assessment": "Stub feasibility — needs real analysis",
        "data_availability": [],
        "experiment_design": None,
        "quantitative_findings": [],
    }
    return {"artifacts": artifacts}


def evaluation_node(state: GraphState) -> dict[str, Any]:
    """Evaluation stub — produces minimal valid artifact."""
    artifacts = dict(state.get("artifacts", {}))
    artifacts["evaluation"] = {
        "metadata": _metadata("evaluation", "pitch_evaluation"),
        "success_criteria": [
            {
                "metric": "Stub metric",
                "target": "TBD",
                "measurement_method": "TBD",
            }
        ],
        "test_harness_concept": {
            "intent": "Stub — validate core functionality",
            "structure": [],
            "coverage_areas": ["stub"],
        },
        "eval_schema": {},
    }
    return {"artifacts": artifacts}


def pressure_test_node(state: GraphState) -> dict[str, Any]:
    """Pressure Testing stub — produces minimal valid artifact with 1 objection."""
    artifacts = dict(state.get("artifacts", {}))
    artifacts["pressure_test"] = {
        "metadata": _metadata("pressure_test", "pitch_evaluation"),
        "objections": [
            {
                "target_claim": "Stub claim from pitch",
                "objection": "Stub objection — needs real adversarial analysis",
                "severity": "low",
                "evidence": "Stub",
                "category": "stub",
            }
        ],
        "overall_assessment": "Stub assessment",
        "recommended_actions": [],
    }
    return {"artifacts": artifacts}


def feedback_synthesis_node(state: GraphState) -> dict[str, Any]:
    """Feedback Synthesis stub — produces minimal valid artifact."""
    artifacts = dict(state.get("artifacts", {}))
    artifacts["feedback_synthesis"] = {
        "metadata": _metadata("feedback_synthesis", "pitch_evaluation"),
        "stakeholder_inputs": [],
        "alignments": [
            {
                "internal_finding": "Stub finding",
                "external_input": "Stub input",
                "assessment": "Stub alignment",
            }
        ],
        "conflicts": [
            {
                "internal_finding": "Stub finding",
                "external_input": "Stub conflict",
                "severity": "low",
                "recommended_resolution": "Stub resolution",
            }
        ],
        "synthesis_summary": "Stub synthesis",
    }
    return {"artifacts": artifacts}


def assembler_node(state: GraphState) -> dict[str, Any]:
    """Handoff package assembler stub — collects all artifacts into package."""
    artifacts = state.get("artifacts", {})
    handoff_package = {
        "metadata": {
            "schema_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "run_id": "stub-run",
            "source_agents": list(artifacts.keys()),
        },
        "artifacts": artifacts,
        "assembled": True,
    }
    return {"handoff_package": handoff_package, "current_phase": "handoff"}


# --- Gate nodes ---


def _run_gate(state: GraphState, phase: str, next_phase: str) -> dict[str, Any]:
    """Run Orchestrator gate evaluation for a given phase."""
    artifacts = state.get("artifacts", {})
    result = _orchestrator.evaluate_gate(phase, artifacts)

    decision = {
        "gate": phase,
        "decision": result.gate_decision.value,
        "cited_artifacts": result.cited_artifacts,
        "gaps": result.gaps,
        "rationale": result.rationale,
        "current_understanding": result.current_understanding,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    decisions = list(state.get("gate_decisions", []))
    decisions.append(decision)
    update: dict[str, Any] = {"gate_decisions": decisions}
    if result.gate_decision.value == "approve":
        update["current_phase"] = next_phase
    return update


def gate_discovery(state: GraphState) -> dict[str, Any]:
    """Gate 1: Orchestrator evaluates discovery phase artifacts."""
    return _run_gate(state, "discovery", "definition")


def gate_definition(state: GraphState) -> dict[str, Any]:
    """Gate 2: Orchestrator evaluates definition phase artifacts."""
    return _run_gate(state, "definition", "pitch_evaluation")


def gate_pitch_evaluation(state: GraphState) -> dict[str, Any]:
    """Gate 3: Orchestrator evaluates pitch & evaluation phase artifacts."""
    return _run_gate(state, "pitch_evaluation", "handoff")


# --- Gate routing functions ---


def route_after_gate_discovery(state: GraphState) -> str:
    decisions = state.get("gate_decisions", [])
    if decisions and decisions[-1].get("decision") == "approve":
        return "pm"
    return "uxr"


def route_after_gate_definition(state: GraphState) -> str:
    decisions = state.get("gate_decisions", [])
    if decisions and decisions[-1].get("decision") == "approve":
        return "evaluation"
    return "pm"


def route_after_gate_pitch_evaluation(state: GraphState) -> str:
    decisions = state.get("gate_decisions", [])
    if decisions and decisions[-1].get("decision") == "approve":
        return "assembler"
    return "evaluation"


# --- Graph builder ---


def build_graph() -> Any:
    """Build and compile the research-to-engineering handoff graph."""
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("orchestrator_intake", orchestrator_intake)
    graph.add_node("uxr", uxr_node)
    graph.add_node("gate_discovery", gate_discovery)
    graph.add_node("pm", pm_node)
    graph.add_node("ds", ds_node)
    graph.add_node("gate_definition", gate_definition)
    graph.add_node("evaluation", evaluation_node)
    graph.add_node("pressure_test", pressure_test_node)
    graph.add_node("feedback_synthesis", feedback_synthesis_node)
    graph.add_node("gate_pitch_evaluation", gate_pitch_evaluation)
    graph.add_node("assembler", assembler_node)

    # Entry point
    graph.set_entry_point("orchestrator_intake")

    # Discovery phase
    graph.add_edge("orchestrator_intake", "uxr")
    graph.add_edge("uxr", "gate_discovery")

    # Gate 1 → Definition phase
    graph.add_conditional_edges(
        "gate_discovery",
        route_after_gate_discovery,
        {"pm": "pm", "uxr": "uxr"},
    )
    graph.add_edge("pm", "ds")
    graph.add_edge("ds", "gate_definition")

    # Gate 2 → Pitch & Evaluation phase
    graph.add_conditional_edges(
        "gate_definition",
        route_after_gate_definition,
        {"evaluation": "evaluation", "pm": "pm"},
    )
    graph.add_edge("evaluation", "pressure_test")
    graph.add_edge("pressure_test", "feedback_synthesis")
    graph.add_edge("feedback_synthesis", "gate_pitch_evaluation")

    # Gate 3 → Handoff
    graph.add_conditional_edges(
        "gate_pitch_evaluation",
        route_after_gate_pitch_evaluation,
        {"assembler": "assembler", "evaluation": "evaluation"},
    )
    graph.add_edge("assembler", END)

    return graph.compile()
