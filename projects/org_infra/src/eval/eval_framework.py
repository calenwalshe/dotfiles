"""Eval framework — rubric-based quality assessment for agent artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalScore:
    agent_id: str
    dimension: str
    score: float  # 0.0 to 1.0
    rationale: str
    pass_threshold: float = 0.5

    @property
    def passed(self) -> bool:
        return self.score >= self.pass_threshold


@dataclass
class EvalReport:
    run_id: str
    scores: list[EvalScore] = field(default_factory=list)

    @property
    def overall_pass(self) -> bool:
        return all(s.passed for s in self.scores)

    @property
    def summary(self) -> str:
        passed = sum(1 for s in self.scores if s.passed)
        total = len(self.scores)
        return f"{passed}/{total} checks passed"


class EvalFramework:
    """Rubric-based evaluation for agent artifacts."""

    def evaluate_run(self, artifacts: dict[str, Any], run_id: str = "") -> EvalReport:
        scores: list[EvalScore] = []

        if "uxr" in artifacts:
            scores.extend(self._eval_uxr(artifacts["uxr"]))
        if "pm" in artifacts:
            scores.extend(self._eval_pm(artifacts["pm"]))
        if "ds" in artifacts:
            scores.extend(self._eval_ds(artifacts["ds"]))
        if "evaluation" in artifacts:
            scores.extend(self._eval_evaluation(artifacts["evaluation"]))
        if "pressure_test" in artifacts:
            scores.extend(self._eval_pressure_test(artifacts["pressure_test"]))
        if "feedback_synthesis" in artifacts:
            scores.extend(self._eval_feedback_synthesis(artifacts["feedback_synthesis"]))

        return EvalReport(run_id=run_id, scores=scores)

    def _eval_uxr(self, artifact: dict) -> list[EvalScore]:
        scores: list[EvalScore] = []

        # Data grounding
        personas = artifact.get("personas", [])
        grounded = sum(1 for p in personas if p.get("data_sources"))
        total = max(len(personas), 1)
        scores.append(EvalScore(
            agent_id="uxr",
            dimension="data_grounding",
            score=grounded / total,
            rationale=f"{grounded}/{total} personas have data sources",
        ))

        # Problem validation
        validations = artifact.get("problem_validation", [])
        scores.append(EvalScore(
            agent_id="uxr",
            dimension="problem_validation",
            score=1.0 if validations else 0.0,
            rationale=f"{len(validations)} validation evidence item(s)",
        ))

        return scores

    def _eval_pm(self, artifact: dict) -> list[EvalScore]:
        scores: list[EvalScore] = []

        # Testable requirements
        reqs = artifact.get("requirements", [])
        with_criteria = sum(1 for r in reqs if r.get("acceptance_criteria"))
        total = max(len(reqs), 1)
        scores.append(EvalScore(
            agent_id="pm",
            dimension="testable_requirements",
            score=with_criteria / total,
            rationale=f"{with_criteria}/{total} requirements have acceptance criteria",
        ))

        # Pitch grounding
        pitch = artifact.get("product_pitch", {})
        has_vp = bool(pitch.get("value_proposition"))
        scores.append(EvalScore(
            agent_id="pm",
            dimension="pitch_grounding",
            score=1.0 if has_vp else 0.0,
            rationale=f"Value proposition {'present' if has_vp else 'missing'}",
        ))

        return scores

    def _eval_ds(self, artifact: dict) -> list[EvalScore]:
        has_feasibility = bool(artifact.get("feasibility_assessment"))
        return [EvalScore(
            agent_id="ds",
            dimension="source_specificity",
            score=1.0 if has_feasibility else 0.0,
            rationale=f"Feasibility assessment {'present' if has_feasibility else 'missing'}",
        )]

    def _eval_evaluation(self, artifact: dict) -> list[EvalScore]:
        criteria = artifact.get("success_criteria", [])
        harness = artifact.get("test_harness_concept", {})
        return [
            EvalScore(
                agent_id="evaluation",
                dimension="measurability",
                score=1.0 if criteria else 0.0,
                rationale=f"{len(criteria)} success criterion/criteria defined",
            ),
            EvalScore(
                agent_id="evaluation",
                dimension="harness_specificity",
                score=1.0 if harness.get("intent") else 0.0,
                rationale=f"Test harness intent {'defined' if harness.get('intent') else 'missing'}",
            ),
        ]

    def _eval_pressure_test(self, artifact: dict) -> list[EvalScore]:
        objections = artifact.get("objections", [])
        specific = sum(1 for o in objections if len(o.get("target_claim", "")) > 10)
        total = max(len(objections), 1)
        return [
            EvalScore(
                agent_id="pressure_test",
                dimension="specificity",
                score=specific / total,
                rationale=f"{specific}/{total} objections target specific claims (>10 chars)",
            ),
            EvalScore(
                agent_id="pressure_test",
                dimension="adversarial_stance",
                score=1.0 if objections else 0.0,
                rationale=f"{len(objections)} objection(s) raised",
            ),
        ]

    def _eval_feedback_synthesis(self, artifact: dict) -> list[EvalScore]:
        alignments = artifact.get("alignments", [])
        conflicts = artifact.get("conflicts", [])
        has_both = bool(alignments) and bool(conflicts)
        return [EvalScore(
            agent_id="feedback_synthesis",
            dimension="minimum_coverage",
            score=1.0 if has_both else 0.0,
            rationale=f"{len(alignments)} alignment(s), {len(conflicts)} conflict(s) — {'meets' if has_both else 'fails'} minimum coverage",
        )]
