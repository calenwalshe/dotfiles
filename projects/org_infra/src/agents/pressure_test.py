"""Pressure Testing agent — adversarial review of assumptions and pitch."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schemas.agent_artifacts import ArtifactMetadata, Objection, PressureTestArtifact
from src.schemas.handoff_package import Severity


class PressureTestAgent:
    """Adversarially challenges pitch claims with specific named objections."""

    def run(self, artifacts: dict[str, Any], run_id: str = "") -> PressureTestArtifact:
        pm = artifacts.get("pm", {})
        uxr = artifacts.get("uxr", {})
        ds = artifacts.get("ds", {})

        objections = self._generate_objections(pm, uxr, ds)

        return PressureTestArtifact(
            metadata=ArtifactMetadata(
                agent_id="pressure_test",
                phase="pitch_evaluation",
                timestamp=datetime.now(timezone.utc),
                run_id=run_id,
            ),
            objections=objections,
            overall_assessment=self._assess(objections),
            recommended_actions=self._recommend(objections),
        )

    def _generate_objections(
        self, pm: dict, uxr: dict, ds: dict
    ) -> list[Objection]:
        objections: list[Objection] = []

        # Challenge the pitch value proposition
        pitch = pm.get("product_pitch", {})
        if pitch.get("value_proposition"):
            objections.append(
                Objection(
                    target_claim=pitch["value_proposition"],
                    objection="Value proposition lacks quantitative evidence. "
                    "No baseline metrics cited to support the claimed improvement.",
                    severity=Severity.high,
                    evidence="No quantitative targets found in pitch or UXR findings",
                    category="measurement",
                )
            )

        # Challenge requirements completeness
        reqs = pm.get("requirements", [])
        if reqs:
            critical = [r for r in reqs if r.get("priority") == "critical"]
            if critical:
                objections.append(
                    Objection(
                        target_claim=f"Requirement {critical[0].get('id', 'unknown')}: {critical[0].get('description', '')[:60]}",
                        objection="Critical requirement acceptance criteria may not be "
                        "independently verifiable without production data.",
                        severity=Severity.medium,
                        evidence="Acceptance criteria reference outcomes that require real users",
                        category="feasibility",
                    )
                )

        # Challenge data assumptions
        feasibility = ds.get("feasibility_assessment", "")
        if "feasible" in feasibility.lower():
            objections.append(
                Objection(
                    target_claim="DS feasibility assessment concludes 'feasible'",
                    objection="Feasibility assessment uses partial data availability. "
                    "The gap between 'partial' and 'available' may be larger than assessed.",
                    severity=Severity.medium,
                    evidence="Data availability marked as 'partial' in DS artifact",
                    category="data_risk",
                )
            )

        # Challenge persona grounding
        personas = uxr.get("personas", [])
        for p in personas:
            sources = p.get("data_sources", [])
            if len(sources) == 1:
                objections.append(
                    Objection(
                        target_claim=f"Persona '{p.get('name', 'unknown')}' is well-grounded",
                        objection=f"Persona relies on single data source ({sources[0]}). "
                        "Single-source personas risk being artifacts of methodology, not real user segments.",
                        severity=Severity.low,
                        evidence=f"Persona data_sources: {sources}",
                        category="research_quality",
                    )
                )

        return objections

    def _assess(self, objections: list[Objection]) -> str:
        high = sum(1 for o in objections if o.severity == Severity.high)
        medium = sum(1 for o in objections if o.severity == Severity.medium)
        return (
            f"Pressure test identified {len(objections)} objection(s): "
            f"{high} high, {medium} medium severity. "
            f"{'High-severity issues should be addressed before handoff.' if high else 'No blocking issues.'}"
        )

    def _recommend(self, objections: list[Objection]) -> list[str]:
        actions: list[str] = []
        for o in objections:
            if o.severity in (Severity.high, Severity.critical):
                actions.append(f"Address: {o.target_claim[:60]} — {o.objection[:80]}")
        return actions
