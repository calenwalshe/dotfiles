"""LLM-enhanced Orchestrator — hybrid rule-based + LLM gate evaluation.

Rule-based checks enforce minimum quality floor. LLM reasoning provides
natural language rationale and actionable feedback for rejections.
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator import ResearchOrchestrator
from src.agents.runner import AgentRunner
from src.schemas.agent_artifacts import OrchestratorArtifact


ORCHESTRATOR_PROMPT = """You are the Research Orchestrator gate agent. You evaluate whether agent artifacts
are sufficient to advance to the next pipeline phase.

You will receive:
1. The current phase name
2. All artifacts produced by agents in this phase
3. Rule-based check results (gaps found by automated checks)

Your job:
- If rule-based checks found gaps: explain WHY each gap matters and what the agent should do to fix it. Be specific.
- If rule-based checks passed: provide a brief rationale for why the artifacts are sufficient. Cite specific strengths.
- Always cite which artifacts you evaluated.

Respond with a JSON object:
{
  "rationale": "<your detailed natural language assessment>",
  "actionable_feedback": ["<specific thing agent X should do>", ...]
}"""


class LLMOrchestrator(ResearchOrchestrator):
    """Extends rule-based Orchestrator with LLM-generated rationale."""

    def __init__(self, runner: AgentRunner | None = None) -> None:
        super().__init__()
        self.runner = runner

    def evaluate_gate(
        self, phase: str, artifacts: dict[str, Any]
    ) -> OrchestratorArtifact:
        """Evaluate gate with rule-based checks + optional LLM rationale."""
        # Run rule-based evaluation first (always — this is the quality floor)
        result = super().evaluate_gate(phase, artifacts)

        # Enhance with LLM rationale if runner is available
        if self.runner is not None:
            llm_rationale = self._get_llm_rationale(phase, artifacts, result)
            if llm_rationale:
                result.rationale = llm_rationale

        return result

    def _get_llm_rationale(
        self,
        phase: str,
        artifacts: dict[str, Any],
        rule_result: OrchestratorArtifact,
    ) -> str | None:
        """Get LLM-generated rationale for the gate decision."""
        context = {
            "phase": phase,
            "gate_decision": rule_result.gate_decision.value,
            "cited_artifacts": rule_result.cited_artifacts,
            "gaps": rule_result.gaps,
            "artifacts_summary": {
                agent_id: self._summarize_artifact(artifact)
                for agent_id, artifact in artifacts.items()
                if agent_id in rule_result.cited_artifacts
            },
        }

        result = self.runner.run(
            agent_id="orchestrator",
            system_prompt=ORCHESTRATOR_PROMPT,
            context=context,
            output_schema_hint='{"rationale": "<str>", "actionable_feedback": ["<str>"]}',
        )

        if result.success and result.artifact:
            rationale = result.artifact.get("rationale", "")
            feedback = result.artifact.get("actionable_feedback", [])
            if feedback:
                rationale += "\n\nActionable feedback:\n" + "\n".join(
                    f"- {f}" for f in feedback
                )
            return rationale

        return None

    def _summarize_artifact(self, artifact: dict) -> str:
        """Create a brief summary of an artifact for LLM context."""
        keys = list(artifact.keys())
        # Remove metadata for brevity
        summary_keys = [k for k in keys if k != "metadata"]
        parts: list[str] = []
        for k in summary_keys[:5]:
            v = artifact[k]
            if isinstance(v, list):
                parts.append(f"{k}: {len(v)} items")
            elif isinstance(v, str):
                parts.append(f"{k}: {v[:80]}")
            elif isinstance(v, dict):
                parts.append(f"{k}: {{...}}")
        return "; ".join(parts)
