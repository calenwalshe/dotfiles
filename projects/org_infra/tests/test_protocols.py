"""Tests for the six core protocols and SQLite store.

Each protocol is tested independently. Store is tested through its API.
No component-to-component coupling tested here — that's the point.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

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
from src.protocols.sqlite_store import SQLiteStore
from src.protocols.store import RejectedClaim, ValidatedClaim


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> SQLiteStore:
    s = SQLiteStore(db_path=tmp_path / "test.db")
    yield s
    s.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Protocol 1: Claim
# ---------------------------------------------------------------------------


class TestClaim:
    def test_create_minimal(self):
        c = Claim(text="Feature X causes regression in segment Y")
        assert c.text == "Feature X causes regression in segment Y"
        assert c.level == ClaimLevel.L0
        assert c.confidence == 0.5
        assert c.id is not None

    def test_create_full(self):
        c = Claim(
            text="Pressure Testing specificity is 60%",
            level=ClaimLevel.L2,
            confidence=0.85,
            domain=Domain.codebase,
            topic="pressure-testing",
            entity="pressure_test.py",
            source_type=SourceType.experiment,
            source_ref="abc123",
            tags=["problem", "agent-quality"],
        )
        assert c.level == ClaimLevel.L2
        assert c.confidence == 0.85
        assert c.domain == Domain.codebase
        assert "problem" in c.tags

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            Claim(text="test", confidence=1.5)
        with pytest.raises(Exception):
            Claim(text="test", confidence=-0.1)

    def test_text_required(self):
        with pytest.raises(Exception):
            Claim(text="")


# ---------------------------------------------------------------------------
# Protocol 2: Evidence
# ---------------------------------------------------------------------------


class TestEvidence:
    def test_create(self):
        claim_id = uuid4()
        e = Evidence(
            claim_id=claim_id,
            content="A/B test showed 12% drop",
            strength=EvidenceStrength.supports,
        )
        assert e.claim_id == claim_id
        assert e.strength == EvidenceStrength.supports

    def test_contradicting_evidence(self):
        e = Evidence(
            claim_id=uuid4(),
            content="Follow-up test showed no effect",
            strength=EvidenceStrength.contradicts,
        )
        assert e.strength == EvidenceStrength.contradicts


# ---------------------------------------------------------------------------
# Protocol 3: Decision
# ---------------------------------------------------------------------------


class TestDecision:
    def test_create_with_alternatives(self):
        d = Decision(
            topic="memory store backend",
            chosen_option="SQLite",
            reasoning="MVP needs zero external dependencies",
            alternatives_rejected=[
                RejectedAlternative(option="Postgres", reason="Premature for Phase 1"),
                RejectedAlternative(option="Flat files", reason="No query capability"),
            ],
            confidence=0.8,
        )
        assert d.chosen_option == "SQLite"
        assert len(d.alternatives_rejected) == 2
        assert d.alternatives_rejected[0].option == "Postgres"


# ---------------------------------------------------------------------------
# Protocol 4: Experiment
# ---------------------------------------------------------------------------


class TestExperiment:
    def test_create(self):
        e = Experiment(
            hypothesis="Few-shot examples improve specificity",
            method="Edit prompt, run eval suite",
            metric_name="specificity_score",
            metric_value=0.71,
            baseline_value=0.60,
            kept=True,
            commit_sha="abc1234",
            duration_seconds=300.0,
        )
        assert e.kept is True
        assert e.metric_value > e.baseline_value


# ---------------------------------------------------------------------------
# Protocol 5: Problem
# ---------------------------------------------------------------------------


class TestProblem:
    def test_score_calculation(self):
        p = Problem(
            description="Pressure Testing specificity below target",
            impact=0.8,
            confidence=0.9,
            actionability=0.7,
        )
        assert p.score == pytest.approx(0.8 * 0.9 * 0.7)

    def test_default_unclassified(self):
        p = Problem(description="Something is wrong")
        assert p.classification == ProblemClassification.unclassified
        assert p.status == ProblemStatus.discovered


# ---------------------------------------------------------------------------
# Protocol 6: Artifact
# ---------------------------------------------------------------------------


class TestArtifact:
    def test_create(self):
        a = Artifact(
            type=ArtifactType.spec,
            path="docs/cortex/specs/foo/spec.md",
            produced_by="executor-pipeline",
            metadata={"run_id": "run-001"},
        )
        assert a.type == ArtifactType.spec
        assert a.produced_by == "executor-pipeline"


# ---------------------------------------------------------------------------
# Store: CRUD
# ---------------------------------------------------------------------------


class TestStoreCRUD:
    def test_write_and_read_claim(self, store: SQLiteStore):
        c = Claim(text="Test claim", level=ClaimLevel.L1, confidence=0.7)
        cid = store.write_claim(c)
        retrieved = store.get_claim(cid)
        assert retrieved is not None
        assert retrieved.text == "Test claim"
        assert retrieved.level == ClaimLevel.L1
        assert retrieved.confidence == 0.7

    def test_write_and_read_evidence(self, store: SQLiteStore):
        c = Claim(text="Parent claim")
        store.write_claim(c)
        e = Evidence(claim_id=c.id, content="Supporting data")
        store.write_evidence(e)
        results = store.query_evidence(claim_id=c.id)
        assert len(results) == 1
        assert results[0].content == "Supporting data"

    def test_write_and_read_decision(self, store: SQLiteStore):
        d = Decision(
            topic="architecture",
            chosen_option="composable",
            reasoning="Monoliths rot",
        )
        store.write_decision(d)
        results = store.query_decisions(topic="architecture")
        assert len(results) == 1
        assert results[0].chosen_option == "composable"

    def test_write_and_read_experiment(self, store: SQLiteStore):
        e = Experiment(hypothesis="Test hypothesis", kept=True, metric_name="accuracy")
        store.write_experiment(e)
        results = store.query_experiments(kept=True)
        assert len(results) == 1
        assert results[0].hypothesis == "Test hypothesis"

    def test_write_and_read_problem(self, store: SQLiteStore):
        p = Problem(description="Something broken", impact=0.9, confidence=0.8, actionability=0.7)
        store.write_problem(p)
        results = store.query_problems()
        assert len(results) == 1
        assert results[0].description == "Something broken"

    def test_write_and_read_artifact(self, store: SQLiteStore):
        a = Artifact(type=ArtifactType.report, path="/tmp/report.md", produced_by="test")
        store.write_artifact(a)
        # Artifacts don't have a query method yet — just verify no crash

    def test_write_and_read_contradiction(self, store: SQLiteStore):
        c1 = Claim(text="X is true")
        c2 = Claim(text="X is false")
        store.write_claim(c1)
        store.write_claim(c2)
        contradiction = Contradiction(claim_a_id=c1.id, claim_b_id=c2.id)
        store.write_contradiction(contradiction)
        results = store.query_contradictions(unresolved_only=True)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Store: Query filtering
# ---------------------------------------------------------------------------


class TestStoreQueries:
    def test_filter_by_level(self, store: SQLiteStore):
        store.write_claim(Claim(text="L0 claim", level=ClaimLevel.L0))
        store.write_claim(Claim(text="L2 claim", level=ClaimLevel.L2))
        store.write_claim(Claim(text="L3 claim", level=ClaimLevel.L3))
        results = store.query_claims(level=ClaimLevel.L2)
        assert len(results) == 1
        assert results[0].text == "L2 claim"

    def test_filter_by_domain(self, store: SQLiteStore):
        store.write_claim(Claim(text="Code thing", domain=Domain.codebase))
        store.write_claim(Claim(text="Product thing", domain=Domain.product))
        results = store.query_claims(domain=Domain.codebase)
        assert len(results) == 1

    def test_filter_by_min_confidence(self, store: SQLiteStore):
        store.write_claim(Claim(text="Low conf", confidence=0.3))
        store.write_claim(Claim(text="High conf", confidence=0.9))
        results = store.query_claims(min_confidence=0.7)
        assert len(results) == 1
        assert results[0].text == "High conf"

    def test_filter_by_temporal_validity(self, store: SQLiteStore):
        now = _now()
        store.write_claim(Claim(
            text="Current claim",
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=30),
        ))
        store.write_claim(Claim(
            text="Expired claim",
            valid_from=now - timedelta(days=60),
            valid_until=now - timedelta(days=1),
        ))
        results = store.query_claims(valid_at=now)
        assert len(results) == 1
        assert results[0].text == "Current claim"

    def test_filter_by_entity(self, store: SQLiteStore):
        store.write_claim(Claim(text="About Calen", entity="Calen"))
        store.write_claim(Claim(text="About system", entity=None))
        results = store.query_claims(entity="Calen")
        assert len(results) == 1
        assert results[0].text == "About Calen"

    def test_filter_problems_by_score(self, store: SQLiteStore):
        store.write_problem(Problem(description="Low priority", impact=0.2, confidence=0.2, actionability=0.2))
        store.write_problem(Problem(description="High priority", impact=0.9, confidence=0.9, actionability=0.9))
        results = store.query_problems(min_score=0.5)
        assert len(results) == 1
        assert results[0].description == "High priority"

    def test_filter_experiments_by_kept(self, store: SQLiteStore):
        store.write_experiment(Experiment(hypothesis="Winner", kept=True))
        store.write_experiment(Experiment(hypothesis="Loser", kept=False))
        kept = store.query_experiments(kept=True)
        assert len(kept) == 1
        assert kept[0].hypothesis == "Winner"


# ---------------------------------------------------------------------------
# Store: Search
# ---------------------------------------------------------------------------


class TestStoreSearch:
    def test_lexical_search_claims(self, store: SQLiteStore):
        store.write_claim(Claim(text="Pressure Testing specificity is low"))
        store.write_claim(Claim(text="Deployment pipeline is stable"))
        results = store.search_lexical("Pressure Testing")
        assert any("Pressure Testing" in r.text for r in results if isinstance(r, Claim))

    def test_semantic_search_falls_back_to_lexical(self, store: SQLiteStore):
        store.write_claim(Claim(text="The ratchet pattern improves quality"))
        results = store.search_semantic("ratchet")
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Store: Retrieval-as-Proposal Gate
# ---------------------------------------------------------------------------


class TestRetrievalGate:
    def test_valid_claim_passes(self, store: SQLiteStore):
        c = Claim(text="Valid claim", level=ClaimLevel.L1, confidence=0.5)
        store.write_claim(c)
        result = store.validate_recall(c)
        assert isinstance(result, ValidatedClaim)
        assert result.validation_passed is True

    def test_expired_claim_rejected(self, store: SQLiteStore):
        c = Claim(
            text="Old claim",
            valid_until=_now() - timedelta(days=1),
        )
        store.write_claim(c)
        result = store.validate_recall(c)
        assert isinstance(result, RejectedClaim)
        assert "expired" in result.rejection_reason.lower()

    def test_contradicted_claim_rejected(self, store: SQLiteStore):
        c1 = Claim(text="X is true")
        c2 = Claim(text="X is false")
        store.write_claim(c1)
        store.write_claim(c2)
        store.write_contradiction(Contradiction(claim_a_id=c1.id, claim_b_id=c2.id))
        result = store.validate_recall(c1)
        assert isinstance(result, RejectedClaim)
        assert "contradiction" in result.rejection_reason.lower()

    def test_low_confidence_for_level_rejected(self, store: SQLiteStore):
        c = Claim(text="Shaky claim", level=ClaimLevel.L3, confidence=0.5)
        store.write_claim(c)
        result = store.validate_recall(c)
        assert isinstance(result, RejectedClaim)
        assert "confidence" in result.rejection_reason.lower()

    def test_missing_source_file_rejected(self, store: SQLiteStore):
        c = Claim(
            text="File-based claim",
            source_type=SourceType.file,
            source_ref="/nonexistent/path/that/does/not/exist.py",
        )
        store.write_claim(c)
        result = store.validate_recall(c)
        assert isinstance(result, RejectedClaim)
        assert "no longer exists" in result.rejection_reason.lower()

    def test_existing_source_file_passes(self, store: SQLiteStore, tmp_path: Path):
        test_file = tmp_path / "real_file.py"
        test_file.write_text("# exists")
        c = Claim(
            text="File-based claim",
            source_type=SourceType.file,
            source_ref=str(test_file),
            level=ClaimLevel.L1,
            confidence=0.5,
        )
        store.write_claim(c)
        result = store.validate_recall(c)
        assert isinstance(result, ValidatedClaim)


# ---------------------------------------------------------------------------
# Store: Update
# ---------------------------------------------------------------------------


class TestStoreUpdate:
    def test_update_claim_level(self, store: SQLiteStore):
        c = Claim(text="Promote me", level=ClaimLevel.L0)
        store.write_claim(c)
        updated = store.update_claim(c.id, level=ClaimLevel.L1, promoted_at=_now())
        assert updated.level == ClaimLevel.L1
        assert updated.promoted_at is not None
        retrieved = store.get_claim(c.id)
        assert retrieved.level == ClaimLevel.L1

    def test_update_problem_status(self, store: SQLiteStore):
        p = Problem(description="Fix this")
        store.write_problem(p)
        updated = store.update_problem(p.id, status=ProblemStatus.approved)
        assert updated.status == ProblemStatus.approved


# ---------------------------------------------------------------------------
# Pressure-test queries (the five acceptance criteria)
# ---------------------------------------------------------------------------


class TestPressureTestQueries:
    """The system is working when these all return correct, sourced answers."""

    def test_q1_what_did_we_decide_and_why(self, store: SQLiteStore):
        """Q1: What did we decide about X, and what evidence supported it?"""
        c = Claim(text="SQLite is sufficient for MVP")
        store.write_claim(c)
        e = Evidence(claim_id=c.id, content="Benchmarks show <10ms reads", strength=EvidenceStrength.supports)
        store.write_evidence(e)
        d = Decision(
            topic="memory store backend",
            chosen_option="SQLite",
            reasoning="Zero external dependencies for Phase 1",
            evidence_ids=[e.id],
        )
        store.write_decision(d)

        decisions = store.query_decisions(topic="memory store backend")
        assert len(decisions) == 1
        assert decisions[0].chosen_option == "SQLite"
        evidence = store.query_evidence(claim_id=c.id)
        assert len(evidence) == 1
        assert "Benchmarks" in evidence[0].content

    def test_q2_what_was_true_last_month(self, store: SQLiteStore):
        """Q2: What was true about X last month?"""
        now = _now()
        last_month = now - timedelta(days=30)
        store.write_claim(Claim(
            text="Feature Y was deployed",
            topic="feature-y",
            valid_from=last_month - timedelta(days=5),
            valid_until=last_month + timedelta(days=5),
        ))
        store.write_claim(Claim(
            text="Feature Y was rolled back",
            topic="feature-y",
            valid_from=now - timedelta(days=2),
        ))
        results = store.query_claims(topic="feature-y", valid_at=last_month)
        assert len(results) == 1
        assert "deployed" in results[0].text

    def test_q3_what_do_we_know_about_entity(self, store: SQLiteStore):
        """Q3: What does the system think it knows about Calen?"""
        store.write_claim(Claim(text="Calen prefers terse output", entity="Calen", confidence=0.9))
        store.write_claim(Claim(text="Calen uses GSD workflow", entity="Calen", confidence=0.95))
        store.write_claim(Claim(text="Unrelated system fact", entity=None, confidence=1.0))
        results = store.query_claims(entity="Calen")
        assert len(results) == 2
        assert all(r.entity == "Calen" for r in results)
        assert results[0].confidence >= results[1].confidence  # ordered by confidence

    def test_q4_stale_memories(self, store: SQLiteStore):
        """Q4: Which memories are stale because the source changed?"""
        c = Claim(
            text="Config file sets timeout to 30s",
            source_type=SourceType.file,
            source_ref="/nonexistent/config.yaml",
        )
        store.write_claim(c)
        result = store.validate_recall(c)
        assert isinstance(result, RejectedClaim)
        assert "no longer exists" in result.rejection_reason.lower()

    def test_q5_why_path_a_not_b(self, store: SQLiteStore):
        """Q5: Why did the agent recommend building path A instead of path B?"""
        d = Decision(
            topic="execution mode",
            chosen_option="autoresearch ratchet",
            reasoning="Problem has clear metric and constrained scope",
            alternatives_rejected=[
                RejectedAlternative(option="full pipeline", reason="Overkill for bounded optimization"),
                RejectedAlternative(option="manual fix", reason="Not reproducible"),
            ],
        )
        store.write_decision(d)
        decisions = store.query_decisions(topic="execution mode")
        assert len(decisions) == 1
        assert decisions[0].chosen_option == "autoresearch ratchet"
        assert len(decisions[0].alternatives_rejected) == 2
        assert decisions[0].alternatives_rejected[0].option == "full pipeline"
