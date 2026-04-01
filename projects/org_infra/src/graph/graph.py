"""LangGraph state machine for the research-to-engineering handoff pipeline.

Four phases: Discovery → Definition → Pitch & Evaluation → Handoff.
Real agent implementations produce typed artifacts. Gate nodes use
Orchestrator for auditable phase transitions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.ds import DataScienceAgent
from src.agents.evaluation import EvaluationAgent
from src.agents.feedback_synthesis import FeedbackSynthesisAgent
from src.agents.orchestrator import ResearchOrchestrator
from src.agents.pm import PMAgent
from src.agents.pressure_test import PressureTestAgent
from src.agents.uxr import UXResearchAgent
from src.assembler.assembler import HandoffAssembler
from src.graph.state import GraphState
from src.integrations.comms import CommsAdapter, MockCommsAdapter

_orchestrator = ResearchOrchestrator()


# --- Agent nodes (real implementations) ---


def orchestrator_intake(state: GraphState) -> dict[str, Any]:
    """Parse problem statement and initialize pipeline."""
    return {
        "current_phase": "discovery",
        "artifacts": state.get("artifacts", {}),
        "gate_decisions": [],
    }


def uxr_node(state: GraphState) -> dict[str, Any]:
    """UX Research — produces personas, problem validation, signals."""
    agent = UXResearchAgent()
    result = agent.run(
        state.get("problem_statement", ""),
        run_id=state.get("run_id", ""),
    )
    artifacts = dict(state.get("artifacts", {}))
    artifacts["uxr"] = result.model_dump(mode="json")
    return {"artifacts": artifacts}


def pm_node(state: GraphState) -> dict[str, Any]:
    """PM — produces pitch, requirements, runs stakeholder comms."""
    comms: CommsAdapter = state.get("comms_adapter") or MockCommsAdapter()  # type: ignore[assignment]
    agent = PMAgent(comms_adapter=comms)
    uxr = state.get("artifacts", {}).get("uxr", {})
    result = agent.run(
        state.get("problem_statement", ""),
        uxr,
        run_id=state.get("run_id", ""),
    )
    artifacts = dict(state.get("artifacts", {}))
    artifacts["pm"] = result.model_dump(mode="json")
    return {"artifacts": artifacts}


def ds_node(state: GraphState) -> dict[str, Any]:
    """Data Science — produces feasibility, experiments."""
    agent = DataScienceAgent()
    arts = state.get("artifacts", {})
    result = agent.run(
        state.get("problem_statement", ""),
        arts.get("uxr", {}),
        arts.get("pm", {}),
        run_id=state.get("run_id", ""),
    )
    artifacts = dict(arts)
    artifacts["ds"] = result.model_dump(mode="json")
    return {"artifacts": artifacts}


def evaluation_node(state: GraphState) -> dict[str, Any]:
    """Evaluation — produces success criteria, test harness concept."""
    agent = EvaluationAgent()
    arts = state.get("artifacts", {})
    result = agent.run(arts, run_id=state.get("run_id", ""))
    artifacts = dict(arts)
    artifacts["evaluation"] = result.model_dump(mode="json")
    return {"artifacts": artifacts}


def pressure_test_node(state: GraphState) -> dict[str, Any]:
    """Pressure Testing — produces adversarial objections."""
    agent = PressureTestAgent()
    arts = state.get("artifacts", {})
    result = agent.run(arts, run_id=state.get("run_id", ""))
    artifacts = dict(arts)
    artifacts["pressure_test"] = result.model_dump(mode="json")
    return {"artifacts": artifacts}


def feedback_synthesis_node(state: GraphState) -> dict[str, Any]:
    """Feedback Synthesis — surfaces alignments and conflicts."""
    agent = FeedbackSynthesisAgent()
    arts = state.get("artifacts", {})
    result = agent.run(arts, run_id=state.get("run_id", ""))
    artifacts = dict(arts)
    artifacts["feedback_synthesis"] = result.model_dump(mode="json")
    return {"artifacts": artifacts}


def assembler_node(state: GraphState) -> dict[str, Any]:
    """Assembles all agent artifacts into a schema-conformant handoff package."""
    assembler = HandoffAssembler()
    arts = state.get("artifacts", {})
    run_id = state.get("run_id", "")
    package = assembler.assemble(arts, run_id=run_id)
    return {
        "handoff_package": package.model_dump(mode="json"),
        "current_phase": "handoff",
    }


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
    return _run_gate(state, "discovery", "definition")


def gate_definition(state: GraphState) -> dict[str, Any]:
    return _run_gate(state, "definition", "pitch_evaluation")


def gate_pitch_evaluation(state: GraphState) -> dict[str, Any]:
    return _run_gate(state, "pitch_evaluation", "handoff")


# --- Gate routing ---


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

    graph.set_entry_point("orchestrator_intake")

    graph.add_edge("orchestrator_intake", "uxr")
    graph.add_edge("uxr", "gate_discovery")

    graph.add_conditional_edges(
        "gate_discovery",
        route_after_gate_discovery,
        {"pm": "pm", "uxr": "uxr"},
    )
    graph.add_edge("pm", "ds")
    graph.add_edge("ds", "gate_definition")

    graph.add_conditional_edges(
        "gate_definition",
        route_after_gate_definition,
        {"evaluation": "evaluation", "pm": "pm"},
    )
    graph.add_edge("evaluation", "pressure_test")
    graph.add_edge("pressure_test", "feedback_synthesis")
    graph.add_edge("feedback_synthesis", "gate_pitch_evaluation")

    graph.add_conditional_edges(
        "gate_pitch_evaluation",
        route_after_gate_pitch_evaluation,
        {"assembler": "assembler", "evaluation": "evaluation"},
    )
    graph.add_edge("assembler", END)

    return graph.compile()
