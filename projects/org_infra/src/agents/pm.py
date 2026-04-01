"""PM agent — product pitch, requirements, stakeholder communication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.integrations.comms import CommsAdapter, CommsMessage
from src.schemas.agent_artifacts import ArtifactMetadata, CommsRecord, PMArtifact
from src.schemas.handoff_package import ProductPitch, Requirement


class PMAgent:
    """Produces product pitch, requirements, and manages stakeholder comms."""

    def __init__(self, comms_adapter: CommsAdapter) -> None:
        self.comms = comms_adapter

    def run(
        self,
        problem_statement: str,
        uxr_artifact: dict[str, Any],
        run_id: str = "",
    ) -> PMArtifact:
        pitch = self._generate_pitch(problem_statement, uxr_artifact)
        requirements = self._generate_requirements(problem_statement, uxr_artifact)
        comms_records = self._run_stakeholder_cycle(pitch)

        return PMArtifact(
            metadata=ArtifactMetadata(
                agent_id="pm",
                phase="definition",
                timestamp=datetime.now(timezone.utc),
                run_id=run_id,
            ),
            product_pitch=pitch,
            requirements=requirements,
            prioritization_rationale="Priority based on user pain point severity from UXR findings",
            stakeholder_comms=comms_records,
        )

    def _generate_pitch(
        self, problem_statement: str, uxr_artifact: dict[str, Any]
    ) -> ProductPitch:
        personas = uxr_artifact.get("personas", [])
        audience = personas[0]["name"] if personas else "Target users"
        return ProductPitch(
            title=f"Solution for: {problem_statement[:50]}",
            summary=f"Addressing the gap identified in discovery: {problem_statement[:80]}",
            value_proposition=f"Resolves the core problem for {audience}",
            target_audience=audience,
            differentiation="Research-validated approach based on UXR findings",
        )

    def _generate_requirements(
        self, problem_statement: str, uxr_artifact: dict[str, Any]
    ) -> list[Requirement]:
        return [
            Requirement(
                id="REQ-01",
                description=f"Core solution addressing: {problem_statement[:60]}",
                priority="critical",
                rationale="Directly addresses primary user pain point from UXR",
                acceptance_criteria=[
                    "Solution is functional for primary persona use case",
                    "Passes evaluation criteria defined by Evaluation agent",
                ],
            ),
            Requirement(
                id="REQ-02",
                description="Stakeholder visibility and reporting",
                priority="medium",
                rationale="Secondary stakeholder need identified in UXR",
                acceptance_criteria=["Stakeholders can view solution progress"],
            ),
        ]

    def _run_stakeholder_cycle(self, pitch: ProductPitch) -> list[CommsRecord]:
        records: list[CommsRecord] = []

        self.comms.send(
            CommsMessage(
                to="stakeholders",
                subject=f"Review: {pitch.title}",
                body=f"Please review this pitch:\n\n{pitch.summary}\n\nValue: {pitch.value_proposition}",
            )
        )
        records.append(
            CommsRecord(
                direction="outbound",
                stakeholder="stakeholders",
                message_summary=f"Sent pitch for review: {pitch.title}",
            )
        )

        responses = self.comms.poll_responses()
        for resp in responses:
            records.append(
                CommsRecord(
                    direction="inbound",
                    stakeholder=resp.from_stakeholder,
                    message_summary=resp.body[:100],
                )
            )

        return records
