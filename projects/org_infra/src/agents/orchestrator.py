"""Research Orchestrator — gate agent that controls all phase transitions.

Evaluates agent artifacts against phase-specific rules and produces
auditable approve/reject decisions with cited artifacts and specific gaps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schemas.agent_artifacts import ArtifactMetadata, GateDecision, OrchestratorArtifact


class ResearchOrchestrator:
    """Rule-based gate agent for phase transitions."""

    PHASE_REQUIREMENTS: dict[str, list[str]] = {
        "discovery": ["uxr"],
        "definition": ["pm", "ds"],
        "pitch_evaluation": ["evaluation", "pressure_test", "feedback_synthesis"],
    }

    def evaluate_gate(
        self, phase: str, artifacts: dict[str, Any]
    ) -> OrchestratorArtifact:
        """Evaluate whether artifacts are sufficient to pass the phase gate."""
        required = self.PHASE_REQUIREMENTS.get(phase, [])
        cited: list[str] = []
        gaps: list[str] = []

        for agent_id in required:
            if agent_id not in artifacts:
                gaps.append(f"{agent_id} artifact missing")
                continue

            cited.append(agent_id)
            artifact = artifacts[agent_id]
            agent_gaps = self._check_artifact_quality(phase, agent_id, artifact)
            gaps.extend(agent_gaps)

        decision = GateDecision.reject if gaps else GateDecision.approve
        rationale = self._build_rationale(phase, decision, cited, gaps)

        return OrchestratorArtifact(
            metadata=ArtifactMetadata(
                agent_id="orchestrator",
                phase=phase,
                timestamp=datetime.now(timezone.utc),
                run_id="",
            ),
            gate_decision=decision,
            cited_artifacts=cited,
            rationale=rationale,
            gaps=gaps,
            current_understanding=self.update_understanding(phase, artifacts),
        )

    def _check_artifact_quality(
        self, phase: str, agent_id: str, artifact: dict[str, Any]
    ) -> list[str]:
        """Check artifact-specific quality rules. Returns list of gaps."""
        gaps: list[str] = []

        if agent_id == "uxr":
            personas = artifact.get("personas", [])
            if not personas:
                gaps.append("uxr artifact has 0 personas")
            else:
                for i, p in enumerate(personas):
                    if not p.get("data_sources"):
                        gaps.append(
                            f"uxr persona '{p.get('name', i)}' has no data_sources"
                        )

            if not artifact.get("problem_validation"):
                gaps.append("uxr artifact has no problem_validation evidence")

        elif agent_id == "pm":
            reqs = artifact.get("requirements", [])
            if not reqs:
                gaps.append("pm artifact has 0 requirements")

            pitch = artifact.get("product_pitch", {})
            if not pitch.get("value_proposition"):
                gaps.append("pm artifact product_pitch missing value_proposition")

        elif agent_id == "ds":
            if not artifact.get("feasibility_assessment"):
                gaps.append("ds artifact has no feasibility_assessment")

        elif agent_id == "evaluation":
            if not artifact.get("success_criteria"):
                gaps.append("evaluation artifact has 0 success_criteria")
            harness = artifact.get("test_harness_concept", {})
            if not harness.get("intent"):
                gaps.append("evaluation artifact test_harness_concept missing intent")

        elif agent_id == "pressure_test":
            objections = artifact.get("objections", [])
            if not objections:
                gaps.append("pressure_test artifact has 0 objections")
            else:
                for i, obj in enumerate(objections):
                    if not obj.get("target_claim"):
                        gaps.append(f"pressure_test objection {i} has empty target_claim")

        elif agent_id == "feedback_synthesis":
            if not artifact.get("alignments"):
                gaps.append("feedback_synthesis artifact has 0 alignments")
            if not artifact.get("conflicts"):
                gaps.append("feedback_synthesis artifact has 0 conflicts")

        return gaps

    def _build_rationale(
        self,
        phase: str,
        decision: GateDecision,
        cited: list[str],
        gaps: list[str],
    ) -> str:
        """Build structured rationale string for the gate decision."""
        if decision == GateDecision.approve:
            return (
                f"Phase '{phase}' gate approved. "
                f"Evaluated artifacts: {', '.join(cited)}. "
                f"All required artifacts present and meet quality checks."
            )
        return (
            f"Phase '{phase}' gate rejected. "
            f"Evaluated artifacts: {', '.join(cited)}. "
            f"Gaps found: {'; '.join(gaps)}."
        )

    def update_understanding(
        self, phase: str, artifacts: dict[str, Any]
    ) -> str:
        """Generate current best understanding document from available artifacts."""
        sections: list[str] = [f"# Current Understanding (after {phase} phase)\n"]

        if "uxr" in artifacts:
            uxr = artifacts["uxr"]
            personas = uxr.get("personas", [])
            sections.append(f"## User Research\n- {len(personas)} persona(s) identified")
            for p in personas:
                sections.append(f"  - {p.get('name', 'Unknown')}: {p.get('description', '')}")
            validations = uxr.get("problem_validation", [])
            if validations:
                sections.append(f"- {len(validations)} validation evidence item(s)")

        if "pm" in artifacts:
            pm = artifacts["pm"]
            pitch = pm.get("product_pitch", {})
            sections.append(f"\n## Product\n- Pitch: {pitch.get('title', 'Untitled')}")
            reqs = pm.get("requirements", [])
            sections.append(f"- {len(reqs)} requirement(s) defined")

        if "ds" in artifacts:
            ds = artifacts["ds"]
            sections.append(
                f"\n## Data Science\n- Feasibility: {ds.get('feasibility_assessment', 'TBD')[:100]}"
            )

        if "evaluation" in artifacts:
            ev = artifacts["evaluation"]
            criteria = ev.get("success_criteria", [])
            sections.append(f"\n## Evaluation\n- {len(criteria)} success criterion/criteria")

        if "pressure_test" in artifacts:
            pt = artifacts["pressure_test"]
            objections = pt.get("objections", [])
            sections.append(f"\n## Pressure Testing\n- {len(objections)} objection(s) raised")

        if "feedback_synthesis" in artifacts:
            fs = artifacts["feedback_synthesis"]
            sections.append(
                f"\n## Stakeholder Feedback\n"
                f"- {len(fs.get('alignments', []))} alignment(s), "
                f"{len(fs.get('conflicts', []))} conflict(s)"
            )

        return "\n".join(sections)
