"""Core protocols for the autonomous R&D platform.

These six types are the typed interfaces every component reads and writes through.
No component imports another component — they all import these protocols.
"""

from src.protocols.schemas import (
    Artifact,
    ArtifactType,
    Claim,
    ClaimLevel,
    Contradiction,
    Decision,
    Domain,
    Evidence,
    EvidenceStrength,
    Experiment,
    Problem,
    ProblemClassification,
    ProblemStatus,
    RejectedAlternative,
    SourceType,
)

__all__ = [
    "Artifact",
    "ArtifactType",
    "Claim",
    "ClaimLevel",
    "Contradiction",
    "Decision",
    "Domain",
    "Evidence",
    "EvidenceStrength",
    "Experiment",
    "Problem",
    "ProblemClassification",
    "ProblemStatus",
    "RejectedAlternative",
    "SourceType",
]
