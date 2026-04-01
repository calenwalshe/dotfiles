"""Evaluation agent — success criteria, test harness concept, eval schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schemas.agent_artifacts import ArtifactMetadata, EvaluationArtifact
from src.schemas.handoff_package import SuccessCriterion, TestCase, TestHarnessConcept


class EvaluationAgent:
    """Produces success criteria and test harness concept from prior artifacts."""

    def run(self, artifacts: dict[str, Any], run_id: str = "") -> EvaluationArtifact:
        pm = artifacts.get("pm", {})
        requirements = pm.get("requirements", [])

        return EvaluationArtifact(
            metadata=ArtifactMetadata(
                agent_id="evaluation",
                phase="pitch_evaluation",
                timestamp=datetime.now(timezone.utc),
                run_id=run_id,
            ),
            success_criteria=self._define_criteria(requirements),
            test_harness_concept=self._design_harness(requirements),
            eval_schema=self._build_eval_schema(),
        )

    def _define_criteria(self, requirements: list[dict]) -> list[SuccessCriterion]:
        criteria = []
        for req in requirements:
            criteria.append(
                SuccessCriterion(
                    metric=f"Completion of {req.get('id', 'REQ')}",
                    target="All acceptance criteria met",
                    measurement_method="Automated test + manual verification",
                )
            )
        if not criteria:
            criteria.append(
                SuccessCriterion(
                    metric="Core functionality",
                    target="System produces valid handoff package",
                    measurement_method="Schema validation",
                )
            )
        return criteria

    def _design_harness(self, requirements: list[dict]) -> TestHarnessConcept:
        test_cases = []
        for req in requirements:
            for ac in req.get("acceptance_criteria", []):
                test_cases.append(
                    TestCase(
                        name=f"Test {req.get('id', 'REQ')}: {ac[:40]}",
                        description=f"Verify: {ac}",
                        category="functional",
                        expected_behavior=ac,
                    )
                )
        return TestHarnessConcept(
            intent="Validate all requirements are met via acceptance criteria",
            structure=test_cases,
            coverage_areas=["functional", "integration", "quality"],
        )

    def _build_eval_schema(self) -> dict:
        return {
            "uxr": {"method": "rubric_based", "dimensions": ["data_grounding", "specificity"]},
            "pm": {"method": "rubric_based", "dimensions": ["testability", "rationale"]},
            "ds": {"method": "rubric_based", "dimensions": ["source_specificity", "rigor"]},
            "pressure_test": {"method": "llm_as_judge", "dimensions": ["specificity", "adversarial_stance"]},
            "feedback_synthesis": {"method": "rubric_based", "dimensions": ["alignment_specificity", "conflict_resolution"]},
        }
