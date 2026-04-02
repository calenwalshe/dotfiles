"""Tests for consolidator phases: decay, archive, promote, embed, corroborate, contradict,
LLM promotion, budget tracking, integration, dry-run, and audit logging."""

from __future__ import annotations

import json
import math
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest

from src.consolidator import Consolidator, ConsolidatorLockError
from src.consolidator.audit import AuditLog
from src.consolidator.budget import BudgetTracker
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.phases.archive import run_archive
from src.consolidator.phases.contradict import AmbiguousPair, run_contradict
from src.consolidator.phases.corroborate import CorroborationResult, run_corroborate
from src.consolidator.phases.decay import run_decay
from src.consolidator.phases.embed import run_embed
from src.consolidator.phases.promote import (
    run_promote,
    run_promote_l1_to_l2,
    run_promote_l2_to_l3,
    run_review_ambiguous,
)
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import Claim, ClaimLevel, Domain, SourceType
from src.protocols.sqlite_store import SQLiteStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
# Embedding helpers for tests
# ---------------------------------------------------------------------------


def _fake_embed_fn(texts: list[str]) -> np.ndarray:
    """Deterministic fake embedder: hash text to produce 384-dim vector."""
    embeddings = []
    for text in texts:
        rng = np.random.RandomState(hash(text) % (2**31))
        vec = rng.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec)
    return np.array(embeddings)


def _similar_embed_fn(texts: list[str]) -> np.ndarray:
    """Returns very similar embeddings for all texts (cosine > 0.95)."""
    base = np.ones(384, dtype=np.float32)
    base = base / np.linalg.norm(base)
    embeddings = []
    for i, text in enumerate(texts):
        noise = np.random.RandomState(i).randn(384).astype(np.float32) * 0.01
        vec = base + noise
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec)
    return np.array(embeddings)


def _dissimilar_embed_fn(texts: list[str]) -> np.ndarray:
    """Returns orthogonal embeddings for each text."""
    embeddings = []
    for i, text in enumerate(texts):
        vec = np.zeros(384, dtype=np.float32)
        vec[i % 384] = 1.0
        embeddings.append(vec)
    return np.array(embeddings)


# ---------------------------------------------------------------------------
# Mock LLM helpers
# ---------------------------------------------------------------------------


def _make_mock_llm(responses: list[dict]) -> MagicMock:
    """Create a mock anthropic client that returns canned responses."""
    client = MagicMock()
    call_count = [0]

    def create(**kwargs):
        idx = min(call_count[0], len(responses) - 1)
        resp = responses[idx]
        call_count[0] += 1

        content_block = SimpleNamespace(text=json.dumps(resp))
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        return SimpleNamespace(content=[content_block], usage=usage)

    client.messages.create = create
    return client


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


# ---------------------------------------------------------------------------
# B3: test_embed
# ---------------------------------------------------------------------------


class TestEmbed:
    """Phase 1 — embedding generation tests."""

    def test_embed_generates_embeddings(self, store, config, audit):
        """Claims without embeddings get embedded."""
        claims = []
        for i in range(5):
            c = _make_claim(
                text=f"embed test claim {i}",
                level=ClaimLevel.L1,
                source_type=SourceType.conversation,
                source_ref="session-1",
            )
            store.write_claim(c)
            claims.append(c)

        actions = run_embed(store, config, audit, embed_fn=_fake_embed_fn)

        assert len(actions) == 5
        for c in claims:
            assert store.has_embedding(c.id)
            raw = store.get_embedding(c.id)
            vec = np.frombuffer(raw, dtype=np.float32)
            assert vec.shape == (384,)

    def test_embed_idempotent(self, store, config, audit):
        """Re-running embed doesn't re-embed claims that already have embeddings."""
        claim = _make_claim(
            text="idempotent embed test",
            level=ClaimLevel.L1,
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        store.write_claim(claim)

        # First run
        actions1 = run_embed(store, config, audit, embed_fn=_fake_embed_fn)
        assert len(actions1) == 1

        # Second run
        audit2 = AuditLog()
        actions2 = run_embed(store, config, audit2, embed_fn=_fake_embed_fn)
        assert len(actions2) == 0
        assert len(audit2.entries) == 0

    def test_embed_correct_dimension(self, store, config, audit):
        """Embedding vectors have correct dimension (384)."""
        claim = _make_claim(
            text="dimension test",
            level=ClaimLevel.L1,
            source_type=SourceType.conversation,
            source_ref="session-1",
        )
        store.write_claim(claim)

        run_embed(store, config, audit, embed_fn=_fake_embed_fn)

        raw = store.get_embedding(claim.id)
        vec = np.frombuffer(raw, dtype=np.float32)
        assert vec.shape == (384,)


# ---------------------------------------------------------------------------
# B4: test_corroborate
# ---------------------------------------------------------------------------


class TestCorroborate:
    """Phase 3 — corroboration detection tests."""

    def test_similar_claims_different_sources_corroborated(self, store, config, audit):
        """Two L1 claims with similar text from different sources are corroborated."""
        # Create 3 similar claims from different sources
        claims = []
        for i in range(3):
            c = _make_claim(
                text=f"the sky is blue {i}",
                level=ClaimLevel.L1,
                source_type=[SourceType.file, SourceType.url, SourceType.conversation][i],
                source_ref=f"source-{i}",
            )
            store.write_claim(c)
            claims.append(c)

        # Embed with similar vectors
        embeddings = _similar_embed_fn([c.text for c in claims])
        for i, c in enumerate(claims):
            store.write_embedding(c.id, embeddings[i].tobytes(), "test-model")

        results = run_corroborate(store, config, audit)

        # Each claim should be corroborated by the other two
        assert len(results) > 0
        for r in results:
            assert r.corroboration_count >= 2

    def test_similar_claims_same_source_not_corroborated(self, store, config, audit):
        """Two L1 claims with similar text from the same source are NOT corroborated."""
        claims = []
        for i in range(3):
            c = _make_claim(
                text=f"same source claim {i}",
                level=ClaimLevel.L1,
                source_type=SourceType.file,
                source_ref="/same/source.py",  # same source
            )
            store.write_claim(c)
            claims.append(c)

        # Embed with similar vectors
        embeddings = _similar_embed_fn([c.text for c in claims])
        for i, c in enumerate(claims):
            store.write_embedding(c.id, embeddings[i].tobytes(), "test-model")

        results = run_corroborate(store, config, audit)

        # Should be empty — same source doesn't count as corroboration
        assert len(results) == 0

    def test_dissimilar_claims_not_corroborated(self, store, config, audit):
        """Two L1 claims with dissimilar text are NOT corroborated."""
        claims = []
        for i in range(3):
            c = _make_claim(
                text=f"dissimilar claim {i}",
                level=ClaimLevel.L1,
                source_type=[SourceType.file, SourceType.url, SourceType.conversation][i],
                source_ref=f"source-{i}",
            )
            store.write_claim(c)
            claims.append(c)

        # Embed with dissimilar (orthogonal) vectors
        embeddings = _dissimilar_embed_fn([c.text for c in claims])
        for i, c in enumerate(claims):
            store.write_embedding(c.id, embeddings[i].tobytes(), "test-model")

        results = run_corroborate(store, config, audit)

        assert len(results) == 0


# ---------------------------------------------------------------------------
# C3: test_contradict
# ---------------------------------------------------------------------------


class TestContradict:
    """Phase 2 — contradiction detection tests."""

    def test_contradictory_pair_detected(self, store, config, audit):
        """NLI score > 0.7 creates a Contradiction record."""
        c1 = _make_claim(text="The API uses REST", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/a.py")
        c2 = _make_claim(text="The API uses GraphQL", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/b.py")
        store.write_claim(c1)
        store.write_claim(c2)

        # Give them embeddings
        for c in [c1, c2]:
            vec = np.random.randn(384).astype(np.float32)
            store.write_embedding(c.id, vec.tobytes(), "test-model")

        # NLI always returns 0.8 (contradiction)
        def mock_nli(a: str, b: str) -> float:
            return 0.8

        ambiguous = run_contradict(store, config, audit, nli_fn=mock_nli)

        # Should have created a contradiction, not ambiguous
        assert len(ambiguous) == 0
        contradictions = store.query_contradictions(unresolved_only=True)
        assert len(contradictions) == 1

    def test_non_contradictory_pair_ignored(self, store, config, audit):
        """NLI score < 0.4 creates no records."""
        c1 = _make_claim(text="claim A", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/a.py")
        c2 = _make_claim(text="claim B", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/b.py")
        store.write_claim(c1)
        store.write_claim(c2)

        for c in [c1, c2]:
            vec = np.random.randn(384).astype(np.float32)
            store.write_embedding(c.id, vec.tobytes(), "test-model")

        def mock_nli(a: str, b: str) -> float:
            return 0.1

        ambiguous = run_contradict(store, config, audit, nli_fn=mock_nli)

        assert len(ambiguous) == 0
        contradictions = store.query_contradictions(unresolved_only=True)
        assert len(contradictions) == 0

    def test_ambiguous_pair_queued(self, store, config, audit):
        """NLI score 0.5 (in ambiguous range) returned for Claude review."""
        c1 = _make_claim(text="claim X", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/a.py")
        c2 = _make_claim(text="claim Y", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/b.py")
        store.write_claim(c1)
        store.write_claim(c2)

        for c in [c1, c2]:
            vec = np.random.randn(384).astype(np.float32)
            store.write_embedding(c.id, vec.tobytes(), "test-model")

        def mock_nli(a: str, b: str) -> float:
            return 0.5

        ambiguous = run_contradict(store, config, audit, nli_fn=mock_nli)

        assert len(ambiguous) == 1
        assert ambiguous[0].score == 0.5
        # No hard contradiction stored
        contradictions = store.query_contradictions(unresolved_only=True)
        assert len(contradictions) == 0


# ---------------------------------------------------------------------------
# C4: Cold-start test
# ---------------------------------------------------------------------------


class TestColdStart:
    """Cold start (<50 claims) uses pairwise without clustering."""

    def test_cold_start_pairwise(self, store, config, audit):
        """<50 claims → pairwise NLI, no clustering needed."""
        # Create 5 claims
        claims = []
        for i in range(5):
            c = _make_claim(
                text=f"cold start claim {i}",
                level=ClaimLevel.L1,
                source_type=SourceType.file,
                source_ref=f"/src/{i}.py",
            )
            store.write_claim(c)
            claims.append(c)
            vec = np.random.randn(384).astype(np.float32)
            store.write_embedding(c.id, vec.tobytes(), "test-model")

        call_count = [0]

        def mock_nli(a: str, b: str) -> float:
            call_count[0] += 1
            return 0.1  # no contradictions

        # cluster_fn should NOT be called for <50 claims
        def failing_cluster(embeddings):
            raise RuntimeError("Cluster should not be called for cold start")

        ambiguous = run_contradict(
            store, config, audit,
            nli_fn=mock_nli,
            cluster_fn=failing_cluster,
        )

        # 5 claims → C(5,2) = 10 pairs
        assert call_count[0] == 10
        assert len(ambiguous) == 0


# ---------------------------------------------------------------------------
# D4: test_l1_to_l2 promotion
# ---------------------------------------------------------------------------


class TestL1ToL2Promote:
    """Phase 4b — L1->L2 LLM-validated promotion."""

    def test_l1_to_l2_approved(self, store, config, audit):
        """Claim with 2 corroborations + Haiku approves → promoted to L2."""
        claim = _make_claim(
            text="Python 3.12 added f-string improvements",
            level=ClaimLevel.L1,
            confidence=0.7,
            source_type=SourceType.url,
            source_ref="https://docs.python.org",
        )
        corr1 = _make_claim(
            text="Python 3.12 f-string enhancements",
            level=ClaimLevel.L1,
            source_type=SourceType.file,
            source_ref="/notes.md",
        )
        corr2 = _make_claim(
            text="New f-string features in Python 3.12",
            level=ClaimLevel.L1,
            source_type=SourceType.conversation,
            source_ref="session-5",
        )
        store.write_claim(claim)
        store.write_claim(corr1)
        store.write_claim(corr2)

        corr_result = CorroborationResult(
            claim_id=claim.id,
            corroboration_count=2,
            corroborating_claim_ids=[corr1.id, corr2.id],
        )

        mock_client = _make_mock_llm([{"validated": True, "reasoning": "Multiple independent sources confirm"}])
        budget = BudgetTracker(budget_cap=1.0)

        actions = run_promote_l1_to_l2(
            store, config, audit,
            [corr_result],
            budget,
            llm_client=mock_client,
        )

        updated = store.get_claim(claim.id)
        assert updated.level == ClaimLevel.L2
        assert updated.promoted_at is not None
        assert len(actions) == 1
        assert "promoted_l2" in actions[0]

    def test_l1_to_l2_rejected(self, store, config, audit):
        """Haiku rejects → stays L1."""
        claim = _make_claim(
            text="dubious claim",
            level=ClaimLevel.L1,
            confidence=0.6,
            source_type=SourceType.url,
            source_ref="https://example.com",
        )
        corr1 = _make_claim(text="corr 1", level=ClaimLevel.L1,
                            source_type=SourceType.file, source_ref="/a.py")
        corr2 = _make_claim(text="corr 2", level=ClaimLevel.L1,
                            source_type=SourceType.conversation, source_ref="s-1")
        store.write_claim(claim)
        store.write_claim(corr1)
        store.write_claim(corr2)

        corr_result = CorroborationResult(
            claim_id=claim.id,
            corroboration_count=2,
            corroborating_claim_ids=[corr1.id, corr2.id],
        )

        mock_client = _make_mock_llm([{"validated": False, "reasoning": "Sources don't actually support this"}])
        budget = BudgetTracker(budget_cap=1.0)

        actions = run_promote_l1_to_l2(
            store, config, audit,
            [corr_result],
            budget,
            llm_client=mock_client,
        )

        updated = store.get_claim(claim.id)
        assert updated.level == ClaimLevel.L1
        assert "rejected_l2" in actions[0]


# ---------------------------------------------------------------------------
# D5: test_l2_to_l3 promotion
# ---------------------------------------------------------------------------


class TestL2ToL3Promote:
    """Phase 4c — L2->L3 Sonnet review (human approval gate)."""

    def test_l2_to_l3_proposed(self, store, config, audit):
        """Sonnet proposes → returned as candidate, NOT auto-promoted."""
        claim = _make_claim(
            text="Deployments should use blue-green strategy",
            level=ClaimLevel.L2,
            confidence=0.9,
            source_type=SourceType.file,
            source_ref="/deploy.md",
        )
        store.write_claim(claim)

        mock_client = _make_mock_llm([{"promote": True, "reasoning": "Specific and actionable"}])
        budget = BudgetTracker(budget_cap=1.0)

        candidates = run_promote_l2_to_l3(
            store, config, audit, budget,
            llm_client=mock_client,
        )

        # Should be proposed, not promoted
        assert len(candidates) == 1
        assert candidates[0].claim_id == claim.id
        assert "Specific and actionable" in candidates[0].reasoning

        # Claim stays L2
        updated = store.get_claim(claim.id)
        assert updated.level == ClaimLevel.L2

    def test_l2_below_confidence_not_considered(self, store, config, audit):
        """L2 claims with confidence < 0.8 are not considered for L3."""
        claim = _make_claim(
            text="Low confidence L2",
            level=ClaimLevel.L2,
            confidence=0.6,  # below 0.8 threshold
            source_type=SourceType.file,
            source_ref="/src.py",
        )
        store.write_claim(claim)

        mock_client = _make_mock_llm([{"promote": True, "reasoning": "yes"}])
        budget = BudgetTracker(budget_cap=1.0)

        candidates = run_promote_l2_to_l3(
            store, config, audit, budget,
            llm_client=mock_client,
        )

        assert len(candidates) == 0


# ---------------------------------------------------------------------------
# D6: test_budget
# ---------------------------------------------------------------------------


class TestBudget:
    """Budget tracking and enforcement."""

    def test_budget_tracking(self):
        """BudgetTracker tracks cumulative cost correctly."""
        budget = BudgetTracker(budget_cap=0.50)

        cost = budget.record_call("haiku", input_tokens=1000, output_tokens=500)
        assert cost > 0
        assert budget.cumulative_cost > 0
        assert not budget.budget_exceeded

    def test_budget_cap_stops_calls(self, store, config, audit):
        """When budget is exceeded, remaining candidates are queued."""
        # Create 3 claims that are candidates for L1->L2
        claims = []
        corr_results = []
        for i in range(3):
            c = _make_claim(
                text=f"budget test claim {i}",
                level=ClaimLevel.L1,
                confidence=0.7,
                source_type=SourceType.url,
                source_ref=f"https://src-{i}.com",
            )
            store.write_claim(c)
            claims.append(c)

            # Create corroborators
            c1 = _make_claim(text=f"corr a {i}", level=ClaimLevel.L1,
                             source_type=SourceType.file, source_ref=f"/a{i}.py")
            c2 = _make_claim(text=f"corr b {i}", level=ClaimLevel.L1,
                             source_type=SourceType.conversation, source_ref=f"s-{i}")
            store.write_claim(c1)
            store.write_claim(c2)

            corr_results.append(CorroborationResult(
                claim_id=c.id,
                corroboration_count=2,
                corroborating_claim_ids=[c1.id, c2.id],
            ))

        # Budget so low that it can afford exactly 0 calls
        budget = BudgetTracker(budget_cap=0.0)
        mock_client = _make_mock_llm([{"validated": True, "reasoning": "ok"}])

        actions = run_promote_l1_to_l2(
            store, config, audit,
            corr_results,
            budget,
            llm_client=mock_client,
        )

        # No promotions should have happened
        for c in claims:
            updated = store.get_claim(c.id)
            assert updated.level == ClaimLevel.L1

        # Budget should record queued
        assert budget.queued_count > 0

    def test_budget_summary(self):
        """Budget summary contains expected fields."""
        budget = BudgetTracker(budget_cap=1.0)
        budget.record_call("haiku", input_tokens=5000, output_tokens=1000)
        budget.record_call("sonnet", input_tokens=2000, output_tokens=500)

        summary = budget.summary()
        assert summary["total_calls"] == 2
        assert summary["budget_cap_usd"] == 1.0
        assert summary["cumulative_cost_usd"] > 0
        assert "haiku" in summary["calls_by_model"]
        assert "sonnet" in summary["calls_by_model"]


# ---------------------------------------------------------------------------
# D6: test_ambiguous_routing
# ---------------------------------------------------------------------------


class TestAmbiguousRouting:
    """Ambiguous NLI pairs are sent to Claude for review."""

    def test_ambiguous_confirmed_as_contradiction(self, store, config, audit):
        """Sonnet confirms ambiguous pair as contradiction → Contradiction record created."""
        c1 = _make_claim(text="API uses REST", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/a.py")
        c2 = _make_claim(text="API uses GraphQL", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/b.py")
        store.write_claim(c1)
        store.write_claim(c2)

        pair = AmbiguousPair(
            claim_a_id=c1.id, claim_b_id=c2.id, score=0.5,
            claim_a_text=c1.text, claim_b_text=c2.text,
        )

        mock_client = _make_mock_llm([{"contradicts": True, "reasoning": "Mutually exclusive"}])
        budget = BudgetTracker(budget_cap=1.0)

        actions = run_review_ambiguous(
            store, audit, [pair], budget, llm_client=mock_client,
        )

        assert any("confirmed" in a for a in actions)
        contradictions = store.query_contradictions(unresolved_only=True)
        assert len(contradictions) == 1

    def test_ambiguous_dismissed(self, store, config, audit):
        """Sonnet dismisses ambiguous pair → no Contradiction."""
        c1 = _make_claim(text="uses Python 3.12", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/a.py")
        c2 = _make_claim(text="supports Python 3.12+", level=ClaimLevel.L1,
                         source_type=SourceType.file, source_ref="/b.py")
        store.write_claim(c1)
        store.write_claim(c2)

        pair = AmbiguousPair(
            claim_a_id=c1.id, claim_b_id=c2.id, score=0.45,
            claim_a_text=c1.text, claim_b_text=c2.text,
        )

        mock_client = _make_mock_llm([{"contradicts": False, "reasoning": "Compatible statements"}])
        budget = BudgetTracker(budget_cap=1.0)

        actions = run_review_ambiguous(
            store, audit, [pair], budget, llm_client=mock_client,
        )

        assert any("dismissed" in a for a in actions)
        contradictions = store.query_contradictions(unresolved_only=True)
        assert len(contradictions) == 0


# ---------------------------------------------------------------------------
# E2: End-to-end integration test
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full 7-phase consolidator with mocked ML + LLM."""

    def test_full_cycle(self, tmp_path):
        """Run complete consolidator on synthetic store, verify all phases execute."""
        db_path = tmp_path / "e2e.db"
        sqlite = SQLiteStore(db_path)
        store = ConsolidatorStore(sqlite)
        config = ConsolidatorConfig()
        audit = AuditLog()
        output_dir = tmp_path / "projections"

        # Create 100+ claims across all levels and domains
        now = datetime.now(timezone.utc)

        # 50 L0 claims (some will promote to L1)
        for i in range(50):
            c = _make_claim(
                text=f"L0 fact number {i}",
                level=ClaimLevel.L0,
                confidence=0.7,
                domain=list(Domain)[i % 5],
                source_type=SourceType.file,
                source_ref=f"/src/file_{i}.py",
                valid_from=now - timedelta(days=i),
            )
            store.write_claim(c)

        # 30 L1 claims (some will be corroborated)
        l1_claims = []
        for i in range(30):
            c = _make_claim(
                text=f"L1 validated fact {i}",
                level=ClaimLevel.L1,
                confidence=0.75,
                domain=list(Domain)[i % 5],
                source_type=[SourceType.file, SourceType.url, SourceType.conversation][i % 3],
                source_ref=f"source-{i}",
                valid_from=now - timedelta(days=i + 10),
            )
            store.write_claim(c)
            l1_claims.append(c)

        # 10 L2 claims (some eligible for L3 review)
        for i in range(10):
            c = _make_claim(
                text=f"L2 corroborated fact {i}",
                level=ClaimLevel.L2,
                confidence=0.85,
                domain=list(Domain)[i % 5],
                source_type=SourceType.file,
                source_ref=f"/validated/{i}.md",
                valid_from=now - timedelta(days=i + 20),
            )
            store.write_claim(c)

        # 10 L0 duplicates of L1 claims — these have NO provenance so they stay L0
        # after promote, then archive finds them matching L1 text
        for i in range(10):
            c = _make_claim(
                text=f"L1 validated fact {i}",  # matches L1 claim text
                level=ClaimLevel.L0,
                confidence=0.5,
                valid_from=now - timedelta(days=5),
                source_type=SourceType.file,
                source_ref="",  # empty — fails provenance gate, stays L0
            )
            store.write_claim(c)

        # Mock functions
        call_counter = {"nli": 0, "embed": 0}

        def mock_embed(texts):
            call_counter["embed"] += len(texts)
            return _fake_embed_fn(texts)

        def mock_nli(a, b):
            call_counter["nli"] += 1
            return 0.1  # no contradictions for simplicity

        def mock_cluster(embeddings):
            # Put everything in one cluster
            return [0] * len(embeddings)

        mock_llm = _make_mock_llm([
            {"validated": True, "reasoning": "confirmed"},
            {"promote": True, "reasoning": "actionable"},
        ] * 50)  # enough responses for all calls

        consolidator = Consolidator(
            store=store,
            config=config,
            audit_log=audit,
            embed_fn=mock_embed,
            nli_fn=mock_nli,
            cluster_fn=mock_cluster,
            llm_client=mock_llm,
            output_dir=output_dir,
        )

        result = consolidator.run()

        # Verify: embeddings were generated
        assert call_counter["embed"] > 0

        # Verify: L0 claims promoted to L1
        promote_entries = [e for e in result.entries if e["phase"] == "promote" and e["action"] == "promote"]
        assert len(promote_entries) > 0

        # Verify: Decay applied
        decay_entries = [e for e in result.entries if e["phase"] == "decay"]
        assert len(decay_entries) > 0

        # Verify: Archive phase ran — L0 duplicates of L1 text get archived
        archive_entries = [e for e in result.entries if e["phase"] == "archive"]
        assert len(archive_entries) > 0
        archived = store.query_archive(limit=200)
        assert len(archived) > 0

        # Verify: Projections generated
        assert output_dir.exists()
        assert (output_dir / "MEMORY.md").exists()

        # Verify: Audit log complete
        assert len(result.entries) > 0
        phases_seen = {e["phase"] for e in result.entries}
        assert "embed" in phases_seen
        assert "promote" in phases_seen
        assert "decay" in phases_seen
        assert "archive" in phases_seen
        assert "project" in phases_seen

        store.close()


# ---------------------------------------------------------------------------
# E3: Concurrency guard test
# ---------------------------------------------------------------------------


class TestConcurrencyGuard:
    """File lock prevents concurrent consolidation."""

    def test_lock_prevents_concurrent_run(self, tmp_path):
        """Second consolidator instance fails with lock error."""
        db_path = tmp_path / "lock_test.db"
        sqlite = SQLiteStore(db_path)
        store = ConsolidatorStore(sqlite)

        c1 = Consolidator(
            store=store,
            embed_fn=_fake_embed_fn,
            nli_fn=lambda a, b: 0.1,
        )

        # Acquire lock manually
        c1._acquire_lock()

        try:
            c2 = Consolidator(
                store=store,
                embed_fn=_fake_embed_fn,
                nli_fn=lambda a, b: 0.1,
            )

            with pytest.raises(ConsolidatorLockError):
                c2.run()
        finally:
            c1._release_lock()
            store.close()


# ---------------------------------------------------------------------------
# E5: Dry-run test
# ---------------------------------------------------------------------------


class TestDryRun:
    """--dry-run doesn't modify store."""

    def test_dry_run_no_modifications(self, tmp_path):
        """Dry run executes phases but rolls back all changes."""
        db_path = tmp_path / "dryrun.db"
        sqlite = SQLiteStore(db_path)
        store = ConsolidatorStore(sqlite)
        output_dir = tmp_path / "projections"

        # Create an L0 claim that would normally be promoted
        claim = _make_claim(
            text="should not be promoted in dry run",
            level=ClaimLevel.L0,
            source_type=SourceType.file,
            source_ref="/src/main.py",
        )
        store.write_claim(claim)

        # Snapshot state before
        before_claim = store.get_claim(claim.id)
        assert before_claim.level == ClaimLevel.L0

        consolidator = Consolidator(
            store=store,
            embed_fn=_fake_embed_fn,
            nli_fn=lambda a, b: 0.1,
            cluster_fn=lambda emb: [0] * len(emb),
            output_dir=output_dir,
        )

        result = consolidator.run(dry_run=True)

        # Claim should still be L0 after dry run
        after_claim = store.get_claim(claim.id)
        assert after_claim.level == ClaimLevel.L0
        assert after_claim.promoted_at is None

        # But audit log should have entries (they were recorded in memory)
        assert len(result.entries) > 0

        store.close()
