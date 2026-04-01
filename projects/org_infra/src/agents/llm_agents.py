"""LLM-powered agent node factory.

Creates LangGraph node functions that delegate to claude -p via AgentRunner.
Falls back to rule-based agents if runner fails or is not available.
"""

from __future__ import annotations

from typing import Any, Callable

from src.agents.prompts.agent_prompts import AGENT_PROMPTS, SCHEMA_HINTS
from src.agents.runner import AgentRunner
from src.graph.state import GraphState


def make_llm_node(
    agent_id: str,
    phase: str,
    context_keys: list[str],
    runner: AgentRunner | None = None,
    fallback: Callable[[GraphState], dict[str, Any]] | None = None,
) -> Callable[[GraphState], dict[str, Any]]:
    """Create a LangGraph node function that runs an agent via claude -p.

    Args:
        agent_id: Agent identifier (must match AGENT_PROMPTS key)
        phase: Pipeline phase this agent runs in
        context_keys: Which artifact keys to inject as context
        runner: AgentRunner instance (None = use fallback only)
        fallback: Rule-based fallback node function

    Returns:
        LangGraph node function
    """
    system_prompt = AGENT_PROMPTS.get(agent_id, f"You are the {agent_id} agent.")
    schema_hint = SCHEMA_HINTS.get(agent_id, "")

    def node(state: GraphState) -> dict[str, Any]:
        artifacts = dict(state.get("artifacts", {}))

        # Build context from specified artifact keys
        context: dict[str, Any] = {
            "problem_statement": state.get("problem_statement", ""),
        }
        for key in context_keys:
            if key in artifacts:
                context[key] = artifacts[key]

        # Try LLM runner
        if runner is not None:
            result = runner.run(
                agent_id=agent_id,
                system_prompt=system_prompt,
                context=context,
                output_schema_hint=schema_hint,
            )

            if result.success and result.artifact:
                artifacts[agent_id] = result.artifact
                # Track tokens
                tokens = state.get("tokens_used", 0) + result.tokens_used
                return {"artifacts": artifacts, "tokens_used": tokens}

        # Fall back to rule-based agent
        if fallback is not None:
            return fallback(state)

        # No runner, no fallback — produce error
        artifacts[agent_id] = {
            "metadata": {"agent_id": agent_id, "phase": phase, "run_id": ""},
            "error": "No runner or fallback available",
        }
        return {"artifacts": artifacts}

    node.__name__ = f"{agent_id}_llm_node"
    node.__doc__ = f"LLM-powered {agent_id} agent (claude -p)"
    return node
