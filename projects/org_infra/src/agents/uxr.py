"""UX Research agent — user signal synthesis, persona generation, problem validation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schemas.agent_artifacts import ArtifactMetadata, UXRArtifact
from src.schemas.handoff_package import EvidenceItem, Persona


class UXResearchAgent:
    """Produces typed UXR artifact from problem statement and available data."""

    def run(self, problem_statement: str, run_id: str = "") -> UXRArtifact:
        return UXRArtifact(
            metadata=ArtifactMetadata(
                agent_id="uxr",
                phase="discovery",
                timestamp=datetime.now(timezone.utc),
                run_id=run_id,
            ),
            personas=self._generate_personas(problem_statement),
            problem_validation=self._validate_problem(problem_statement),
            user_signals=self._extract_signals(problem_statement),
            methodology="Rule-based extraction from problem statement (no LLM)",
        )

    def _generate_personas(self, problem_statement: str) -> list[Persona]:
        return [
            Persona(
                name="Primary User",
                description=f"User affected by: {problem_statement[:80]}",
                needs=["solution to stated problem"],
                pain_points=["current state described in problem"],
                data_sources=["problem_statement_analysis"],
            ),
            Persona(
                name="Secondary Stakeholder",
                description="Internal stakeholder impacted by the problem domain",
                needs=["visibility into solution progress"],
                pain_points=["lack of structured information"],
                data_sources=["problem_statement_analysis"],
            ),
        ]

    def _validate_problem(self, problem_statement: str) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                source="problem_statement_analysis",
                finding=f"Problem statement identifies a clear gap: {problem_statement[:60]}",
                confidence="medium",
            )
        ]

    def _extract_signals(self, problem_statement: str) -> list[str]:
        return [
            "Problem statement provided by human stakeholder",
            "Gap identified in current workflow",
        ]
