"""Feedback Synthesis agent — collects and integrates stakeholder feedback."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.schemas.agent_artifacts import ArtifactMetadata, FeedbackSynthesisArtifact
from src.schemas.handoff_package import (
    AlignmentItem,
    ConflictItem,
    Severity,
    StakeholderInput,
)


class FeedbackSynthesisAgent:
    """Surfaces alignments and conflicts between internal findings and stakeholder input."""

    def run(self, artifacts: dict[str, Any], run_id: str = "") -> FeedbackSynthesisArtifact:
        pm = artifacts.get("pm", {})
        uxr = artifacts.get("uxr", {})

        stakeholder_inputs = self._collect_inputs(pm)
        alignments = self._find_alignments(stakeholder_inputs, uxr, pm)
        conflicts = self._find_conflicts(stakeholder_inputs, uxr, pm)

        return FeedbackSynthesisArtifact(
            metadata=ArtifactMetadata(
                agent_id="feedback_synthesis",
                phase="pitch_evaluation",
                timestamp=datetime.now(timezone.utc),
                run_id=run_id,
            ),
            stakeholder_inputs=stakeholder_inputs,
            alignments=alignments,
            conflicts=conflicts,
            synthesis_summary=self._summarize(alignments, conflicts),
        )

    def _collect_inputs(self, pm: dict) -> list[StakeholderInput]:
        inputs: list[StakeholderInput] = []
        for comm in pm.get("stakeholder_comms", []):
            if comm.get("direction") == "inbound":
                inputs.append(
                    StakeholderInput(
                        stakeholder=comm.get("stakeholder", "unknown"),
                        input_text=comm.get("message_summary", ""),
                        sentiment=comm.get("sentiment", "neutral"),
                    )
                )
        if not inputs:
            inputs.append(
                StakeholderInput(
                    stakeholder="system",
                    input_text="No stakeholder responses received during comms cycle",
                    sentiment="neutral",
                )
            )
        return inputs

    def _find_alignments(
        self,
        inputs: list[StakeholderInput],
        uxr: dict,
        pm: dict,
    ) -> list[AlignmentItem]:
        alignments: list[AlignmentItem] = []
        pitch = pm.get("product_pitch", {})
        problem_validations = uxr.get("problem_validation", [])

        if problem_validations and pitch.get("value_proposition"):
            alignments.append(
                AlignmentItem(
                    internal_finding=f"UXR validated problem: {problem_validations[0].get('finding', '')[:60]}",
                    external_input=f"Stakeholder received pitch: {pitch.get('title', '')[:40]}",
                    assessment="Problem definition aligns between internal research and stakeholder communication",
                )
            )

        return alignments

    def _find_conflicts(
        self,
        inputs: list[StakeholderInput],
        uxr: dict,
        pm: dict,
    ) -> list[ConflictItem]:
        conflicts: list[ConflictItem] = []
        reqs = pm.get("requirements", [])

        for inp in inputs:
            if any(word in inp.input_text.lower() for word in ["concern", "worried", "timeline", "risk"]):
                conflicts.append(
                    ConflictItem(
                        internal_finding=f"PM prioritized {len(reqs)} requirement(s) as achievable",
                        external_input=f"Stakeholder {inp.stakeholder}: '{inp.input_text[:60]}'",
                        severity=Severity.medium,
                        recommended_resolution="Review timeline assumptions with stakeholder; consider phased delivery",
                    )
                )

        if not conflicts:
            conflicts.append(
                ConflictItem(
                    internal_finding="Internal assessment assumes standard implementation timeline",
                    external_input="No explicit stakeholder pushback received (may indicate insufficient engagement)",
                    severity=Severity.low,
                    recommended_resolution="Proactively solicit specific timeline and resource feedback",
                )
            )

        return conflicts

    def _summarize(
        self, alignments: list[AlignmentItem], conflicts: list[ConflictItem]
    ) -> str:
        return (
            f"Synthesis: {len(alignments)} alignment(s), {len(conflicts)} conflict(s). "
            f"{'Overall direction confirmed by stakeholders.' if alignments else 'No strong alignment signals.'} "
            f"{'Conflicts require attention before handoff.' if any(c.severity in (Severity.high, Severity.critical) for c in conflicts) else 'No blocking conflicts.'}"
        )
