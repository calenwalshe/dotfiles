"""Phase 6: Archive — move expired and promoted-past claims to archive table."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import ClaimLevel


def run_archive(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
) -> list[str]:
    """Archive claims that are expired beyond the retention window, or L0 claims promoted to L1.

    1. Claims with valid_until set and older than archive_after_days.
    2. L0 claims where an L1 claim with the same text exists (promoted duplicate).
    """
    actions: list[str] = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=config.archive_after_days)

    # 1. Expired claims past retention window
    all_claims = store.query_claims(limit=10000)
    for claim in all_claims:
        if claim.valid_until is not None and claim.valid_until < cutoff:
            store.archive_claim(claim.id, reason="expired_past_retention")
            action = f"archived:{claim.id}:expired"
            actions.append(action)
            audit.record(
                phase="archive",
                action="archive",
                claim_id=str(claim.id),
                reason=f"Expired claim past {config.archive_after_days}-day retention",
                details={"valid_until": claim.valid_until.isoformat()},
            )

    # 2. L0 claims that have been promoted (L1 with same text exists)
    l0_claims = store.query_claims(level=ClaimLevel.L0, limit=10000)
    l1_claims = store.query_claims(level=ClaimLevel.L1, limit=10000)
    l1_texts = {c.text for c in l1_claims}

    for claim in l0_claims:
        if claim.text in l1_texts:
            store.archive_claim(claim.id, reason="promoted_to_l1")
            action = f"archived:{claim.id}:promoted"
            actions.append(action)
            audit.record(
                phase="archive",
                action="archive",
                claim_id=str(claim.id),
                reason="L0 claim has been promoted to L1",
            )

    return actions
