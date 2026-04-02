"""Phase 5: Confidence Decay — apply time-based decay to all claims."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import ClaimLevel, SourceType


def run_decay(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
) -> list[str]:
    """Decay confidence of all claims based on domain half-life.

    For file-backed claims where the source file no longer exists, expire immediately.
    For claims whose decayed confidence drops below threshold, set valid_until = now.
    """
    actions: list[str] = []
    now = datetime.now(timezone.utc)

    # Query all claims (no valid_at filter — we want everything including expired)
    all_claims = store.query_claims(limit=10000)

    for claim in all_claims:
        half_life = config.domain_half_lives.get(claim.domain, 30.0)
        age_days = (now - claim.valid_from).total_seconds() / 86400.0

        # File-backed claim: check source existence
        if claim.source_type == SourceType.file and claim.source_ref:
            if not Path(claim.source_ref).exists():
                store.update_claim(claim.id, valid_until=now, confidence=0.0)
                action = f"expired:{claim.id}:file_missing"
                actions.append(action)
                audit.record(
                    phase="decay",
                    action="expire",
                    claim_id=str(claim.id),
                    reason=f"Source file missing: {claim.source_ref}",
                    details={"source_ref": claim.source_ref},
                )
                continue

        # Calculate decayed confidence
        decayed = claim.confidence * math.exp(-0.693 * age_days / half_life)

        if decayed < config.confidence_expiry_threshold:
            # Expire the claim
            store.update_claim(claim.id, valid_until=now, confidence=decayed)
            action = f"expired:{claim.id}:below_threshold"
            actions.append(action)
            audit.record(
                phase="decay",
                action="expire",
                claim_id=str(claim.id),
                reason=f"Decayed confidence {decayed:.4f} below threshold {config.confidence_expiry_threshold}",
                details={
                    "original_confidence": claim.confidence,
                    "decayed_confidence": decayed,
                    "age_days": age_days,
                    "half_life": half_life,
                },
            )
        elif abs(decayed - claim.confidence) > 0.001:
            # Update confidence (only if meaningfully changed)
            store.update_claim(claim.id, confidence=decayed)
            action = f"decayed:{claim.id}"
            actions.append(action)
            audit.record(
                phase="decay",
                action="decay",
                claim_id=str(claim.id),
                reason=f"Confidence decayed from {claim.confidence:.4f} to {decayed:.4f}",
                details={
                    "original_confidence": claim.confidence,
                    "decayed_confidence": decayed,
                    "age_days": age_days,
                    "half_life": half_life,
                },
            )

    return actions
