"""Consolidator configuration — all tunable parameters in one place."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.protocols.schemas import Domain


@dataclass
class L0L1Rules:
    """Rules for L0 -> L1 promotion gate."""

    provenance_required: bool = True  # CALIBRATE
    timestamp_required: bool = True  # CALIBRATE
    max_text_length: int = 500  # CALIBRATE — atomicity proxy


@dataclass
class ConsolidatorConfig:
    """All consolidation parameters. Every numeric value is tagged CALIBRATE."""

    # Domain-specific half-lives in days
    domain_half_lives: dict[Domain, float] = field(default_factory=lambda: {
        Domain.codebase: 7.0,  # CALIBRATE
        Domain.competitive: 14.0,  # CALIBRATE
        Domain.operational: 30.0,  # CALIBRATE
        Domain.product: 60.0,  # CALIBRATE
        Domain.user: 90.0,  # CALIBRATE
    })

    # Embedding similarity thresholds
    cosine_corroboration_threshold: float = 0.85  # CALIBRATE
    cosine_dedup_threshold: float = 0.90  # CALIBRATE

    # NLI thresholds
    nli_contradiction_threshold: float = 0.7  # CALIBRATE
    nli_ambiguous_range: tuple[float, float] = (0.4, 0.7)  # CALIBRATE

    # L0 -> L1 promotion rules
    l0_l1_rules: L0L1Rules = field(default_factory=L0L1Rules)

    # Budget cap per consolidation cycle in USD
    budget_cap_per_cycle: float = 0.50  # CALIBRATE

    # Archive settings
    archive_after_days: int = 90  # CALIBRATE

    # Below this decayed confidence, claim expires
    confidence_expiry_threshold: float = 0.1  # CALIBRATE
