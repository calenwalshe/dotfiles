"""Data Science agent — quantitative feasibility, data availability, experiment design."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schemas.agent_artifacts import (
    ArtifactMetadata,
    DataSourceAssessment,
    DSArtifact,
    ExperimentDesign,
)


class DataScienceAgent:
    """Produces feasibility assessment and experiment design."""

    def run(
        self,
        problem_statement: str,
        uxr_artifact: dict[str, Any],
        pm_artifact: dict[str, Any],
        run_id: str = "",
    ) -> DSArtifact:
        return DSArtifact(
            metadata=ArtifactMetadata(
                agent_id="ds",
                phase="definition",
                timestamp=datetime.now(timezone.utc),
                run_id=run_id,
            ),
            feasibility_assessment=self._assess_feasibility(problem_statement),
            data_availability=self._check_data(problem_statement),
            experiment_design=self._design_experiment(pm_artifact),
            quantitative_findings=self._extract_findings(uxr_artifact),
        )

    def _assess_feasibility(self, problem_statement: str) -> str:
        return (
            f"Feasibility assessment for: {problem_statement[:60]}. "
            "Based on rule-based analysis: the problem is well-scoped and "
            "data requirements appear achievable with standard infrastructure. "
            "Recommend proceeding with experiment design."
        )

    def _check_data(self, problem_statement: str) -> list[DataSourceAssessment]:
        return [
            DataSourceAssessment(
                source="problem_domain_data",
                availability="partial",
                quality="Assessment pending — needs real data audit",
                gaps=["Exact data schema unknown until implementation"],
            )
        ]

    def _design_experiment(self, pm_artifact: dict[str, Any]) -> ExperimentDesign:
        reqs = pm_artifact.get("requirements", [])
        primary_req = reqs[0]["description"] if reqs else "Core solution"
        return ExperimentDesign(
            hypothesis=f"Implementing '{primary_req}' will resolve the identified user pain point",
            methodology="A/B test comparing solution vs current state",
            metrics=["task_completion_rate", "time_to_resolution", "user_satisfaction"],
            sample_requirements="Minimum 100 users per arm for statistical significance",
        )

    def _extract_findings(self, uxr_artifact: dict[str, Any]) -> list[str]:
        findings: list[str] = []
        personas = uxr_artifact.get("personas", [])
        findings.append(f"{len(personas)} user persona(s) identified in research")
        validations = uxr_artifact.get("problem_validation", [])
        findings.append(f"{len(validations)} problem validation evidence item(s)")
        return findings
