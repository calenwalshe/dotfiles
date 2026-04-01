"""Handoff package assembler — aggregates agent artifacts into typed package."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schemas.handoff_package import (
    Assumption,
    EvalCriteria,
    FeedbackSynthesis,
    HandoffPackage,
    OpenAssumptions,
    PackageMetadata,
    ProblemStatement,
    ProductPitch,
    Requirements,
    Risk,
    RiskLog,
    TestHarnessConcept,
    UserResearch,
)


class HandoffAssembler:
    """Assembles agent artifacts into a schema-conformant HandoffPackage."""

    def assemble(self, artifacts: dict[str, Any], run_id: str = "") -> HandoffPackage:
        uxr = artifacts.get("uxr", {})
        pm = artifacts.get("pm", {})
        ds = artifacts.get("ds", {})
        evaluation = artifacts.get("evaluation", {})
        pressure_test = artifacts.get("pressure_test", {})
        feedback = artifacts.get("feedback_synthesis", {})

        return HandoffPackage(
            metadata=PackageMetadata(
                schema_version="1.0.0",
                created_at=datetime.now(timezone.utc),
                run_id=run_id,
                source_agents=list(artifacts.keys()),
            ),
            problem_statement=ProblemStatement(
                statement=self._extract_problem(uxr),
                evidence=[
                    {"source": v.get("source", ""), "finding": v.get("finding", ""), "confidence": v.get("confidence", "medium")}
                    for v in uxr.get("problem_validation", [])
                ],
                target_users=[p.get("name", "") for p in uxr.get("personas", [])],
                validated=bool(uxr.get("problem_validation")),
            ),
            user_research=UserResearch(**{
                k: uxr[k] for k in ("personas", "problem_validation", "user_signals", "methodology")
                if k in uxr
            }),
            product_pitch=ProductPitch(**pm.get("product_pitch", {
                "title": "Not generated",
                "summary": "",
                "value_proposition": "",
                "target_audience": "",
            })),
            requirements=Requirements(
                build=pm.get("requirements", []),
                not_build=[],
                prioritization_rationale=pm.get("prioritization_rationale", ""),
            ),
            eval_criteria=EvalCriteria(
                success_criteria=evaluation.get("success_criteria", []),
                guardrails=[],
            ),
            test_harness_concept=TestHarnessConcept(**evaluation.get("test_harness_concept", {
                "intent": "Not generated",
                "structure": [],
                "coverage_areas": [],
            })),
            feedback_synthesis=FeedbackSynthesis(
                stakeholder_inputs=feedback.get("stakeholder_inputs", []),
                alignments=feedback.get("alignments", []),
                conflicts=feedback.get("conflicts", []),
            ),
            risk_log=RiskLog(
                risks=self._extract_risks(pressure_test, ds),
            ),
            open_assumptions=OpenAssumptions(
                assumptions=self._extract_assumptions(ds),
            ),
        )

    def _extract_problem(self, uxr: dict) -> str:
        validations = uxr.get("problem_validation", [])
        if validations:
            return validations[0].get("finding", "Problem statement not extracted")
        return "Problem statement not extracted"

    def _extract_risks(self, pressure_test: dict, ds: dict) -> list[dict]:
        risks: list[dict] = []
        for i, obj in enumerate(pressure_test.get("objections", [])):
            risks.append({
                "id": f"RISK-PT-{i+1:02d}",
                "description": f"{obj.get('target_claim', '')}: {obj.get('objection', '')}",
                "severity": obj.get("severity", "medium"),
                "likelihood": "medium",
                "mitigation": "",
                "owner": "engineering",
            })
        return risks

    def _extract_assumptions(self, ds: dict) -> list[dict]:
        assumptions: list[dict] = []
        for gap in ds.get("data_availability", []):
            for g in gap.get("gaps", []):
                assumptions.append({
                    "statement": g,
                    "status": "open",
                    "owner": "engineering",
                    "resolution_needed_by": "Before implementation",
                })
        return assumptions
