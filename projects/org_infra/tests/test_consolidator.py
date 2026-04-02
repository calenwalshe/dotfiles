"""Tests for consolidator phases: decay, archive, promote, and audit logging."""

from __future__ import annotations

import math
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.phases.archive import run_archive
from src.consolidator.phases.decay import run_decay
from src.consolidator.phases.promote import run_promote
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import Claim, ClaimLevel, Domain, SourceType
from src.protocols.sqlite_store import SQLiteStore


@pytest.fixture
def store(tmp_path):
    """Create a fresh ConsolidatorStore backed by a temp SQLite DB."""
    db_path = tmp_path / "test.db"
    sqlite = SQLiteStore(db_path)
    return ConsolidatorStore(sqlite)


@pytest.fixture
def config():
    return ConsolidatorConfig()


@pytest.fixture
def audit():
    return AuditLog()


def _make_claim(
    text: str = "test claim",
    level: ClaimLevel = ClaimLevel.L0,
    confidence: float = 0.8,
    domain: Domain = Domain.codebase,
    source_type: SourceType = SourceType.file,
    source_ref: str = "/tmp/exists.py",
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> Claim:
    return Claim(
        text=text,
        level=level,
        confidence=confidence,
        domain=domain,
        source_type=source_type,
        source_ref=source_ref,
        valid_from=valid_from or datetime.now(timezone.utc),
        valid_until=valid_until,
    )


# ---------------------------------------------------------------------------
# A11: test_decay
# ---------------------------------------------------------------------------


class TestDecay:
    """Phase 5 — confidence decay tests."""

    def test_decay_rates_per_domain(self, store, config, audit):
        """Claims across all 5 domains decay at correct rates."""
        now = datetime.now(timezone.utc)
        age = timedelta(days=7)  # 7 days old

        claims = {}
        for domain in Domain:
            claim = _make_claim(
                text=f"claim for {domain.value}",
                domain=domain,
                confidence=1.0,
                valid_from=now - age,
                source_type=SourceType.conversation,
                source_ref="session-1",
            )
            store.write_claim(claim)
            claims[domain] = claim

        run_decay(store, config, audit)

        for domain, claim in claims.items():
            half_life = config.domain_half_lives[domain]
            expected = 1.0 * math.exp(-0.693 * 7.0 / half_life)
            updated = store.get_claim(claim.id)

            if expected < config.confidence_expiry_threshold:
                # Should have been expired
                assert updated.valid_until is not None
            else:
                assert updated.confidence == pytest.approx(expected, abs=0.01)

    def test_half_life_boundary(self, store, config, audit):
        """Claim at exactly its half-life has ~50% of original confidence."""
        now = datetime.now(timezone.utc)
        half_life = config.domain_half_lives[Domain.operational]  # 30 days

        claim = _make_claim(
            text="boundary test",
            domain=Domain.operational,
            confidence=1.0,
            valid_from=now - timedelta(days=half_life),
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        store.write_claim(claim)

        run_decay(store, config, audit)

        updated = store.get_claim(claim.id)
        # exp(-0.693 * 1) = ~0.5
        assert updated.confidence == pytest.approx(0.5, abs=0.01)

    def test_file_backed_missing_source_expires(self, store, config, audit):
        """File-backed claim with missing source expires immediately."""
        claim = _make_claim(
            text="file backed claim",
            source_type=SourceType.file,
            source_ref="/nonexistent/path/that/does/not/exist.py",
            confidence=0.9,
        )
        store.write_claim(claim)

        run_decay(store, config, audit)

        updated = store.get_claim(claim.id)
        assert updated.valid_until is not None
        assert updated.confidence == 0.0

    def test_file_backed_existing_source_decays_normally(self, store, config, audit, tmp_path):
        """File-backed claim with existing source decays normally, not expired."""
        # Create a real file
        real_file = tmp_path / "real.py"
        real_file.write_text("pass")

        now = datetime.now(timezone.utc)
        claim = _make_claim(
            text="file exists claim",
            source_type=SourceType.file,
            source_ref=str(real_file),
            confidence=0.9,
            domain=Domain.operational,
            valid_from=now - timedelta(days=1),
        )
        store.write_claim(claim)

        run_decay(store, config, audit)

        updated = store.get_claim(claim.id)
        # Should not be expired
        assert updated.valid_until is None
        # Confidence should be slightly decayed but still high
        assert updated.confidence < 0.9
        assert updated.confidence > 0.8


# ---------------------------------------------------------------------------
# A12: test_archive
# ---------------------------------------------------------------------------


class TestArchive:
    """Phase 6 — archive tests."""

    def test_expired_claims_past_retention_archived(self, store, config, audit):
        """Claims expired >90 days ago move to archive."""
        now = datetime.now(timezone.utc)
        old_expiry = now - timedelta(days=config.archive_after_days + 1)

        claim = _make_claim(
            text="old expired claim",
            valid_until=old_expiry,
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        store.write_claim(claim)

        run_archive(store, config, audit)

        # Claim should be gone from main table
        assert store.get_claim(claim.id) is None
        # Should be in archive
        archived = store.query_archive()
        assert len(archived) == 1
        assert archived[0]["claim"].text == "old expired claim"

    def test_non_expired_claims_stay(self, store, config, audit):
        """Claims without valid_until or recently expired stay in main table."""
        now = datetime.now(timezone.utc)

        # Not expired at all
        claim1 = _make_claim(
            text="active claim",
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        store.write_claim(claim1)

        # Expired recently (within retention window)
        claim2 = _make_claim(
            text="recently expired",
            valid_until=now - timedelta(days=10),
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        store.write_claim(claim2)

        run_archive(store, config, audit)

        assert store.get_claim(claim1.id) is not None
        assert store.get_claim(claim2.id) is not None
        assert len(store.query_archive()) == 0

    def test_promoted_l0_archived(self, store, config, audit):
        """L0 claim with matching L1 text gets archived."""
        claim_l0 = _make_claim(
            text="promoted fact",
            level=ClaimLevel.L0,
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        claim_l1 = _make_claim(
            text="promoted fact",
            level=ClaimLevel.L1,
            source_type=SourceType.file,
            source_ref="/some/file.py",
        )
        store.write_claim(claim_l0)
        store.write_claim(claim_l1)

        run_archive(store, config, audit)

        # L0 should be archived
        assert store.get_claim(claim_l0.id) is None
        # L1 should remain
        assert store.get_claim(claim_l1.id) is not None
        archived = store.query_archive()
        assert len(archived) == 1
        assert archived[0]["archive_reason"] == "promoted_to_l1"

    def test_archived_claims_queryable(self, store, config, audit):
        """Archived claims are queryable via query_archive."""
        now = datetime.now(timezone.utc)
        old_expiry = now - timedelta(days=config.archive_after_days + 10)

        for i in range(3):
            claim = _make_claim(
                text=f"archive test {i}",
                valid_until=old_expiry,
                source_type=SourceType.conversation,
                source_ref="session-1",
            )
            store.write_claim(claim)

        run_archive(store, config, audit)

        archived = store.query_archive(limit=10)
        assert len(archived) == 3


# ---------------------------------------------------------------------------
# A13: test_l0_to_l1
# ---------------------------------------------------------------------------


class TestL0ToL1Promote:
    """Phase 4a — L0 -> L1 promotion tests."""

    def test_promote_with_provenance_timestamp_short_text(self, store, config, audit):
        """L0 claim with provenance, timestamp, and short text promotes to L1."""
        claim = _make_claim(
            text="short atomic fact",
            level=ClaimLevel.L0,
            source_type=SourceType.file,
            source_ref="/src/main.py",
        )
        store.write_claim(claim)

        run_promote(store, config, audit)

        updated = store.get_claim(claim.id)
        assert updated.level == ClaimLevel.L1
        assert updated.promoted_at is not None

    def test_no_promote_without_provenance(self, store, config, audit):
        """L0 claim without source_ref stays L0."""
        claim = _make_claim(
            text="no provenance claim",
            level=ClaimLevel.L0,
            source_type=SourceType.file,
            source_ref="",  # empty — no provenance
        )
        store.write_claim(claim)

        run_promote(store, config, audit)

        updated = store.get_claim(claim.id)
        assert updated.level == ClaimLevel.L0

    def test_no_promote_text_too_long(self, store, config, audit):
        """L0 claim with text >500 chars stays L0."""
        long_text = "x" * 501
        claim = _make_claim(
            text=long_text,
            level=ClaimLevel.L0,
            source_type=SourceType.file,
            source_ref="/src/main.py",
        )
        store.write_claim(claim)

        run_promote(store, config, audit)

        updated = store.get_claim(claim.id)
        assert updated.level == ClaimLevel.L0

    def test_already_l1_not_touched(self, store, config, audit):
        """L1 claims are not re-processed by promote phase."""
        claim = _make_claim(
            text="already promoted",
            level=ClaimLevel.L1,
            source_type=SourceType.file,
            source_ref="/src/main.py",
        )
        store.write_claim(claim)

        run_promote(store, config, audit)

        # No audit entries for this claim (promote only queries L0)
        claim_entries = [e for e in audit.entries if e["claim_id"] == str(claim.id)]
        assert len(claim_entries) == 0


# ---------------------------------------------------------------------------
# A13 continued: test_audit
# ---------------------------------------------------------------------------


class TestAudit:
    """Every phase action produces a structured audit entry."""

    def test_decay_produces_audit_entries(self, store, config, audit):
        """Decay phase logs every action."""
        claim = _make_claim(
            text="decay audit test",
            source_type=SourceType.file,
            source_ref="/nonexistent/audit_test.py",
            confidence=0.9,
        )
        store.write_claim(claim)

        run_decay(store, config, audit)

        assert len(audit.entries) >= 1
        entry = audit.entries[0]
        assert entry["phase"] == "decay"
        assert entry["action"] in ("expire", "decay")
        assert entry["claim_id"] == str(claim.id)
        assert "reason" in entry
        assert "timestamp" in entry

    def test_archive_produces_audit_entries(self, store, config, audit):
        """Archive phase logs every action."""
        now = datetime.now(timezone.utc)
        old_expiry = now - timedelta(days=config.archive_after_days + 5)
        claim = _make_claim(
            text="archive audit test",
            valid_until=old_expiry,
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        store.write_claim(claim)

        run_archive(store, config, audit)

        assert len(audit.entries) >= 1
        entry = audit.entries[0]
        assert entry["phase"] == "archive"
        assert entry["action"] == "archive"
        assert entry["claim_id"] == str(claim.id)
        assert "reason" in entry
        assert "timestamp" in entry

    def test_promote_produces_audit_entries(self, store, config, audit):
        """Promote phase logs every action (both promotes and skips)."""
        # One that will promote
        good = _make_claim(
            text="good claim",
            level=ClaimLevel.L0,
            source_type=SourceType.file,
            source_ref="/src/main.py",
        )
        # One that will fail (no provenance)
        bad = _make_claim(
            text="bad claim",
            level=ClaimLevel.L0,
            source_type=SourceType.file,
            source_ref="",
        )
        store.write_claim(good)
        store.write_claim(bad)

        run_promote(store, config, audit)

        assert len(audit.entries) == 2
        phases = {e["action"] for e in audit.entries}
        assert "promote" in phases
        assert "skip" in phases

        for entry in audit.entries:
            assert entry["phase"] == "promote"
            assert entry["claim_id"] in (str(good.id), str(bad.id))
            assert "reason" in entry
            assert "timestamp" in entry

    def test_audit_jsonl_output(self, tmp_path, store, config):
        """Audit log writes to JSONL file when output_path is set."""
        import json

        audit_path = tmp_path / "audit.jsonl"
        audit = AuditLog(output_path=audit_path)

        claim = _make_claim(
            text="jsonl test",
            source_type=SourceType.file,
            source_ref="/nonexistent/jsonl.py",
        )
        store.write_claim(claim)

        run_decay(store, config, audit)
        audit.close()

        lines = audit_path.read_text().strip().split("\n")
        assert len(lines) >= 1
        parsed = json.loads(lines[0])
        assert "phase" in parsed
        assert "action" in parsed
        assert "claim_id" in parsed
