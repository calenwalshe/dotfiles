"""Phase 4a: L0 -> L1 Promote — check provenance, timestamp, atomicity."""

from __future__ import annotations

from datetime import datetime, timezone

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import ClaimLevel


def run_promote(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
) -> list[str]:
    """Promote L0 claims to L1 if they pass all gates.

    Gates (from config.l0_l1_rules):
    - provenance: source_type and source_ref must be set
    - timestamp: valid_from must be set
    - atomicity: text length must be <= max_text_length
    """
    actions: list[str] = []
    rules = config.l0_l1_rules
    now = datetime.now(timezone.utc)

    l0_claims = store.query_claims(level=ClaimLevel.L0, limit=10000)

    for claim in l0_claims:
        failures: list[str] = []

        # Check provenance
        if rules.provenance_required:
            if not claim.source_type or not claim.source_ref:
                failures.append("missing_provenance")

        # Check timestamp
        if rules.timestamp_required:
            if claim.valid_from is None:
                failures.append("missing_timestamp")

        # Check atomicity (text length)
        if len(claim.text) > rules.max_text_length:
            failures.append(f"text_too_long:{len(claim.text)}>{rules.max_text_length}")

        if failures:
            action = f"skipped:{claim.id}:{','.join(failures)}"
            actions.append(action)
            audit.record(
                phase="promote",
                action="skip",
                claim_id=str(claim.id),
                reason=f"Failed gates: {', '.join(failures)}",
                details={"failures": failures},
            )
        else:
            store.update_claim(claim.id, level=ClaimLevel.L1, promoted_at=now)
            action = f"promoted:{claim.id}"
            actions.append(action)
            audit.record(
                phase="promote",
                action="promote",
                claim_id=str(claim.id),
                reason="All L0->L1 gates passed",
                details={
                    "source_type": claim.source_type.value,
                    "source_ref": claim.source_ref,
                    "text_length": len(claim.text),
                },
            )

    return actions
