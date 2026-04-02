"""SQLite adapter for the Store protocol.

MVP backend: single-file database, no external dependencies.
Swap to Postgres by implementing StoreProtocol against psycopg + pgvector.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import UUID

from src.protocols.schemas import (
    Artifact,
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
    SourceType,
)
from src.protocols.store import (
    RejectedClaim,
    StoreProtocol,
    ValidatedClaim,
)


def _uuid_str(u: UUID) -> str:
    return str(u)


def _parse_uuid(s: str) -> UUID:
    return UUID(s)


def _dt_str(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _parse_dt(s: str | None) -> datetime | None:
    if s is None:
        return None
    return datetime.fromisoformat(s)


def _json_str(obj: object) -> str:
    if isinstance(obj, list):
        return json.dumps([item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in obj])
    return json.dumps(obj, default=str)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'L0',
    confidence REAL NOT NULL DEFAULT 0.5,
    domain TEXT NOT NULL DEFAULT 'operational',
    topic TEXT NOT NULL DEFAULT '',
    entity TEXT,
    source_type TEXT NOT NULL DEFAULT 'conversation',
    source_ref TEXT NOT NULL DEFAULT '',
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    created_at TEXT NOT NULL,
    promoted_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(id),
    content TEXT NOT NULL,
    strength TEXT NOT NULL DEFAULT 'supports',
    source_type TEXT NOT NULL DEFAULT 'conversation',
    source_ref TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    chosen_option TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    alternatives_rejected TEXT NOT NULL DEFAULT '[]',
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.5,
    timestamp TEXT NOT NULL,
    outcome TEXT
);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    hypothesis TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT '',
    inputs TEXT NOT NULL DEFAULT '{}',
    outputs TEXT NOT NULL DEFAULT '{}',
    metric_name TEXT NOT NULL DEFAULT '',
    metric_value REAL,
    baseline_value REAL,
    kept INTEGER NOT NULL DEFAULT 0,
    commit_sha TEXT,
    duration_seconds REAL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    source_claim_ids TEXT NOT NULL DEFAULT '[]',
    impact REAL NOT NULL DEFAULT 0.5,
    confidence REAL NOT NULL DEFAULT 0.5,
    actionability REAL NOT NULL DEFAULT 0.5,
    classification TEXT NOT NULL DEFAULT 'unclassified',
    status TEXT NOT NULL DEFAULT 'discovered',
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL DEFAULT 'report',
    path TEXT NOT NULL,
    produced_by TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS contradictions (
    id TEXT PRIMARY KEY,
    claim_a_id TEXT NOT NULL REFERENCES claims(id),
    claim_b_id TEXT NOT NULL REFERENCES claims(id),
    detected_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution TEXT
);

CREATE INDEX IF NOT EXISTS idx_claims_level ON claims(level);
CREATE INDEX IF NOT EXISTS idx_claims_domain ON claims(domain);
CREATE INDEX IF NOT EXISTS idx_claims_topic ON claims(topic);
CREATE INDEX IF NOT EXISTS idx_claims_entity ON claims(entity);
CREATE INDEX IF NOT EXISTS idx_evidence_claim_id ON evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_decisions_topic ON decisions(topic);
CREATE INDEX IF NOT EXISTS idx_experiments_kept ON experiments(kept);
CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status);
CREATE INDEX IF NOT EXISTS idx_problems_classification ON problems(classification);

CREATE TABLE IF NOT EXISTS claim_embeddings (
    claim_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims_archive (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'L0',
    confidence REAL NOT NULL DEFAULT 0.5,
    domain TEXT NOT NULL DEFAULT 'operational',
    topic TEXT NOT NULL DEFAULT '',
    entity TEXT,
    source_type TEXT NOT NULL DEFAULT 'conversation',
    source_ref TEXT NOT NULL DEFAULT '',
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    created_at TEXT NOT NULL,
    promoted_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    archived_at TEXT NOT NULL,
    archive_reason TEXT NOT NULL DEFAULT ''
);
"""


class SQLiteStore(StoreProtocol):
    """SQLite implementation of the Store protocol."""

    def __init__(self, db_path: str | Path = "knowledge.db") -> None:
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # --- Write ---

    def write_claim(self, claim: Claim) -> UUID:
        self.conn.execute(
            "INSERT INTO claims (id, text, level, confidence, domain, topic, entity, "
            "source_type, source_ref, valid_from, valid_until, created_at, promoted_at, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(claim.id), claim.text, claim.level.value, claim.confidence,
                claim.domain.value, claim.topic, claim.entity, claim.source_type.value,
                claim.source_ref, _dt_str(claim.valid_from), _dt_str(claim.valid_until),
                _dt_str(claim.created_at), _dt_str(claim.promoted_at),
                json.dumps(claim.tags),
            ),
        )
        self.conn.commit()
        return claim.id

    def write_evidence(self, evidence: Evidence) -> UUID:
        self.conn.execute(
            "INSERT INTO evidence (id, claim_id, content, strength, source_type, source_ref, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(evidence.id), _uuid_str(evidence.claim_id), evidence.content,
                evidence.strength.value, evidence.source_type.value, evidence.source_ref,
                _dt_str(evidence.timestamp),
            ),
        )
        self.conn.commit()
        return evidence.id

    def write_decision(self, decision: Decision) -> UUID:
        self.conn.execute(
            "INSERT INTO decisions (id, topic, chosen_option, reasoning, alternatives_rejected, "
            "evidence_ids, confidence, timestamp, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(decision.id), decision.topic, decision.chosen_option,
                decision.reasoning, _json_str(decision.alternatives_rejected),
                json.dumps([str(eid) for eid in decision.evidence_ids]),
                decision.confidence, _dt_str(decision.timestamp), decision.outcome,
            ),
        )
        self.conn.commit()
        return decision.id

    def write_experiment(self, experiment: Experiment) -> UUID:
        self.conn.execute(
            "INSERT INTO experiments (id, hypothesis, method, inputs, outputs, metric_name, "
            "metric_value, baseline_value, kept, commit_sha, duration_seconds, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(experiment.id), experiment.hypothesis, experiment.method,
                json.dumps(experiment.inputs, default=str),
                json.dumps(experiment.outputs, default=str),
                experiment.metric_name, experiment.metric_value, experiment.baseline_value,
                int(experiment.kept), experiment.commit_sha, experiment.duration_seconds,
                _dt_str(experiment.timestamp),
            ),
        )
        self.conn.commit()
        return experiment.id

    def write_problem(self, problem: Problem) -> UUID:
        self.conn.execute(
            "INSERT INTO problems (id, description, source_claim_ids, impact, confidence, "
            "actionability, classification, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(problem.id), problem.description,
                json.dumps([str(cid) for cid in problem.source_claim_ids]),
                problem.impact, problem.confidence, problem.actionability,
                problem.classification.value, problem.status.value,
                _dt_str(problem.timestamp),
            ),
        )
        self.conn.commit()
        return problem.id

    def write_artifact(self, artifact: Artifact) -> UUID:
        self.conn.execute(
            "INSERT INTO artifacts (id, type, path, produced_by, timestamp, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(artifact.id), artifact.type.value, artifact.path,
                artifact.produced_by, _dt_str(artifact.timestamp),
                json.dumps(artifact.metadata, default=str),
            ),
        )
        self.conn.commit()
        return artifact.id

    def write_contradiction(self, contradiction: Contradiction) -> UUID:
        self.conn.execute(
            "INSERT INTO contradictions (id, claim_a_id, claim_b_id, detected_at, resolved_at, resolution) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(contradiction.id), _uuid_str(contradiction.claim_a_id),
                _uuid_str(contradiction.claim_b_id), _dt_str(contradiction.detected_at),
                _dt_str(contradiction.resolved_at), contradiction.resolution,
            ),
        )
        self.conn.commit()
        return contradiction.id

    # --- Read by ID ---

    def get_claim(self, claim_id: UUID) -> Claim | None:
        row = self.conn.execute("SELECT * FROM claims WHERE id = ?", (_uuid_str(claim_id),)).fetchone()
        if row is None:
            return None
        return _row_to_claim(row)

    def get_decision(self, decision_id: UUID) -> Decision | None:
        row = self.conn.execute("SELECT * FROM decisions WHERE id = ?", (_uuid_str(decision_id),)).fetchone()
        if row is None:
            return None
        return _row_to_decision(row)

    def get_experiment(self, experiment_id: UUID) -> Experiment | None:
        row = self.conn.execute("SELECT * FROM experiments WHERE id = ?", (_uuid_str(experiment_id),)).fetchone()
        if row is None:
            return None
        return _row_to_experiment(row)

    def get_problem(self, problem_id: UUID) -> Problem | None:
        row = self.conn.execute("SELECT * FROM problems WHERE id = ?", (_uuid_str(problem_id),)).fetchone()
        if row is None:
            return None
        return _row_to_problem(row)

    # --- Query ---

    def query_claims(
        self,
        *,
        level: ClaimLevel | None = None,
        domain: Domain | None = None,
        topic: str | None = None,
        entity: str | None = None,
        min_confidence: float | None = None,
        valid_at: datetime | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[Claim]:
        conditions: list[str] = []
        params: list[object] = []

        if level is not None:
            conditions.append("level = ?")
            params.append(level.value)
        if domain is not None:
            conditions.append("domain = ?")
            params.append(domain.value)
        if topic is not None:
            conditions.append("topic = ?")
            params.append(topic)
        if entity is not None:
            conditions.append("entity = ?")
            params.append(entity)
        if min_confidence is not None:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        if valid_at is not None:
            dt_str = _dt_str(valid_at)
            conditions.append("valid_from <= ?")
            params.append(dt_str)
            conditions.append("(valid_until IS NULL OR valid_until >= ?)")
            params.append(dt_str)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM claims WHERE {where} ORDER BY confidence DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        claims = [_row_to_claim(r) for r in rows]

        if tags:
            claims = [c for c in claims if set(tags) <= set(c.tags)]

        return claims

    def query_evidence(self, *, claim_id: UUID | None = None, limit: int = 100) -> list[Evidence]:
        if claim_id is not None:
            rows = self.conn.execute(
                "SELECT * FROM evidence WHERE claim_id = ? ORDER BY timestamp DESC LIMIT ?",
                (_uuid_str(claim_id), limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM evidence ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_evidence(r) for r in rows]

    def query_decisions(self, *, topic: str | None = None, limit: int = 100) -> list[Decision]:
        if topic is not None:
            rows = self.conn.execute(
                "SELECT * FROM decisions WHERE topic = ? ORDER BY timestamp DESC LIMIT ?",
                (topic, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_decision(r) for r in rows]

    def query_experiments(
        self, *, kept: bool | None = None, metric_name: str | None = None, limit: int = 100
    ) -> list[Experiment]:
        conditions: list[str] = []
        params: list[object] = []
        if kept is not None:
            conditions.append("kept = ?")
            params.append(int(kept))
        if metric_name is not None:
            conditions.append("metric_name = ?")
            params.append(metric_name)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self.conn.execute(
            f"SELECT * FROM experiments WHERE {where} ORDER BY timestamp DESC LIMIT ?", params
        ).fetchall()
        return [_row_to_experiment(r) for r in rows]

    def query_problems(
        self,
        *,
        status: ProblemStatus | None = None,
        classification: ProblemClassification | None = None,
        min_score: float | None = None,
        limit: int = 100,
    ) -> list[Problem]:
        conditions: list[str] = []
        params: list[object] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status.value)
        if classification is not None:
            conditions.append("classification = ?")
            params.append(classification.value)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self.conn.execute(
            f"SELECT * FROM problems WHERE {where} ORDER BY timestamp DESC LIMIT ?", params
        ).fetchall()
        problems = [_row_to_problem(r) for r in rows]
        if min_score is not None:
            problems = [p for p in problems if p.score >= min_score]
        return problems

    def query_contradictions(self, *, unresolved_only: bool = True, limit: int = 100) -> list[Contradiction]:
        if unresolved_only:
            rows = self.conn.execute(
                "SELECT * FROM contradictions WHERE resolved_at IS NULL ORDER BY detected_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM contradictions ORDER BY detected_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_contradiction(r) for r in rows]

    # --- Search (lexical for SQLite; semantic is a stub until vector DB) ---

    def search_semantic(self, text: str, top_k: int = 10) -> list[Claim | Evidence]:
        # Stub: falls back to lexical until vector extension is added
        return self.search_lexical(text, top_k)

    def search_lexical(self, text: str, top_k: int = 10) -> list[Claim | Evidence]:
        pattern = f"%{text}%"
        claim_rows = self.conn.execute(
            "SELECT * FROM claims WHERE text LIKE ? ORDER BY confidence DESC LIMIT ?",
            (pattern, top_k),
        ).fetchall()
        evidence_rows = self.conn.execute(
            "SELECT * FROM evidence WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (pattern, top_k),
        ).fetchall()
        results: list[Claim | Evidence] = [_row_to_claim(r) for r in claim_rows]
        results.extend(_row_to_evidence(r) for r in evidence_rows)
        return results[:top_k]

    # --- Retrieval-as-Proposal Gate ---

    def validate_recall(self, claim: Claim) -> ValidatedClaim | RejectedClaim:
        # Check 1: Source freshness (file sources must still exist)
        if claim.source_type == SourceType.file and claim.source_ref:
            from pathlib import Path as _Path

            if not _Path(claim.source_ref).exists():
                return RejectedClaim(
                    **claim.model_dump(),
                    rejection_reason=f"Source file no longer exists: {claim.source_ref}",
                )

        # Check 2: Temporal validity
        now = datetime.now(timezone.utc)
        if claim.valid_until and claim.valid_until < now:
            return RejectedClaim(
                **claim.model_dump(),
                rejection_reason=f"Claim expired: valid_until={claim.valid_until.isoformat()}",
            )

        # Check 3: Contradictions
        contradictions = self.conn.execute(
            "SELECT * FROM contradictions WHERE (claim_a_id = ? OR claim_b_id = ?) AND resolved_at IS NULL",
            (_uuid_str(claim.id), _uuid_str(claim.id)),
        ).fetchall()
        if contradictions:
            return RejectedClaim(
                **claim.model_dump(),
                rejection_reason=f"Claim has {len(contradictions)} unresolved contradiction(s)",
            )

        # Check 4: Minimum confidence for level
        level_thresholds = {ClaimLevel.L0: 0.0, ClaimLevel.L1: 0.3, ClaimLevel.L2: 0.6, ClaimLevel.L3: 0.8}
        min_conf = level_thresholds.get(claim.level, 0.0)
        if claim.confidence < min_conf:
            return RejectedClaim(
                **claim.model_dump(),
                rejection_reason=f"Confidence {claim.confidence} below threshold {min_conf} for {claim.level.value}",
            )

        return ValidatedClaim(**claim.model_dump(), validation_note="All checks passed")

    # --- Update ---

    def update_claim(self, claim_id: UUID, **fields) -> Claim:
        claim = self.get_claim(claim_id)
        if claim is None:
            raise ValueError(f"Claim {claim_id} not found")
        updated = claim.model_copy(update=fields)
        set_clauses = []
        params: list[object] = []
        for field_name, value in fields.items():
            col = field_name
            if isinstance(value, datetime):
                params.append(_dt_str(value))
            elif isinstance(value, Enum):
                params.append(value.value)
            elif isinstance(value, list):
                params.append(json.dumps(value))
            else:
                params.append(value)
            set_clauses.append(f"{col} = ?")
        params.append(_uuid_str(claim_id))
        self.conn.execute(f"UPDATE claims SET {', '.join(set_clauses)} WHERE id = ?", params)
        self.conn.commit()
        return updated

    def update_problem(self, problem_id: UUID, **fields) -> Problem:
        problem = self.get_problem(problem_id)
        if problem is None:
            raise ValueError(f"Problem {problem_id} not found")
        updated = problem.model_copy(update=fields)
        set_clauses = []
        params: list[object] = []
        for field_name, value in fields.items():
            if isinstance(value, datetime):
                params.append(_dt_str(value))
            elif isinstance(value, Enum):
                params.append(value.value)
            elif isinstance(value, list):
                params.append(json.dumps([str(v) for v in value]))
            else:
                params.append(value)
            set_clauses.append(f"{field_name} = ?")
        params.append(_uuid_str(problem_id))
        self.conn.execute(f"UPDATE problems SET {', '.join(set_clauses)} WHERE id = ?", params)
        self.conn.commit()
        return updated

    # --- Embeddings ---

    def write_embedding(self, claim_id: UUID, embedding: bytes, model: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO claim_embeddings (claim_id, embedding, model, created_at) "
            "VALUES (?, ?, ?, ?)",
            (_uuid_str(claim_id), embedding, model, now),
        )
        self.conn.commit()

    def get_embedding(self, claim_id: UUID) -> bytes | None:
        row = self.conn.execute(
            "SELECT embedding FROM claim_embeddings WHERE claim_id = ?",
            (_uuid_str(claim_id),),
        ).fetchone()
        if row is None:
            return None
        return row[0]

    def has_embedding(self, claim_id: UUID) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM claim_embeddings WHERE claim_id = ?",
            (_uuid_str(claim_id),),
        ).fetchone()
        return row is not None

    # --- Archive ---

    def archive_claim(self, claim_id: UUID, reason: str) -> None:
        claim = self.get_claim(claim_id)
        if claim is None:
            raise ValueError(f"Claim {claim_id} not found")
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO claims_archive (id, text, level, confidence, domain, topic, entity, "
            "source_type, source_ref, valid_from, valid_until, created_at, promoted_at, tags, "
            "archived_at, archive_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid_str(claim.id), claim.text, claim.level.value, claim.confidence,
                claim.domain.value, claim.topic, claim.entity, claim.source_type.value,
                claim.source_ref, _dt_str(claim.valid_from), _dt_str(claim.valid_until),
                _dt_str(claim.created_at), _dt_str(claim.promoted_at),
                json.dumps(claim.tags), now, reason,
            ),
        )
        self.conn.execute("DELETE FROM claims WHERE id = ?", (_uuid_str(claim_id),))
        self.conn.commit()

    def query_archive(self, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM claims_archive ORDER BY archived_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            claim = _row_to_claim_from_archive(row)
            results.append({
                "claim": claim,
                "archived_at": row["archived_at"],
                "archive_reason": row["archive_reason"],
            })
        return results

    # --- Lifecycle ---

    def close(self) -> None:
        self.conn.close()


# ---------------------------------------------------------------------------
# Row → Model helpers
# ---------------------------------------------------------------------------


def _row_to_claim(row: sqlite3.Row) -> Claim:
    return Claim(
        id=_parse_uuid(row["id"]),
        text=row["text"],
        level=ClaimLevel(row["level"]),
        confidence=row["confidence"],
        domain=Domain(row["domain"]),
        topic=row["topic"],
        entity=row["entity"],
        source_type=SourceType(row["source_type"]),
        source_ref=row["source_ref"],
        valid_from=_parse_dt(row["valid_from"]),
        valid_until=_parse_dt(row["valid_until"]),
        created_at=_parse_dt(row["created_at"]),
        promoted_at=_parse_dt(row["promoted_at"]),
        tags=json.loads(row["tags"]),
    )


def _row_to_evidence(row: sqlite3.Row) -> Evidence:
    return Evidence(
        id=_parse_uuid(row["id"]),
        claim_id=_parse_uuid(row["claim_id"]),
        content=row["content"],
        strength=EvidenceStrength(row["strength"]),
        source_type=SourceType(row["source_type"]),
        source_ref=row["source_ref"],
        timestamp=_parse_dt(row["timestamp"]),
    )


def _row_to_decision(row: sqlite3.Row) -> Decision:
    alts_raw = json.loads(row["alternatives_rejected"])
    from src.protocols.schemas import RejectedAlternative

    alts = [RejectedAlternative(**a) if isinstance(a, dict) else a for a in alts_raw]
    return Decision(
        id=_parse_uuid(row["id"]),
        topic=row["topic"],
        chosen_option=row["chosen_option"],
        reasoning=row["reasoning"],
        alternatives_rejected=alts,
        evidence_ids=[_parse_uuid(eid) for eid in json.loads(row["evidence_ids"])],
        confidence=row["confidence"],
        timestamp=_parse_dt(row["timestamp"]),
        outcome=row["outcome"],
    )


def _row_to_experiment(row: sqlite3.Row) -> Experiment:
    return Experiment(
        id=_parse_uuid(row["id"]),
        hypothesis=row["hypothesis"],
        method=row["method"],
        inputs=json.loads(row["inputs"]),
        outputs=json.loads(row["outputs"]),
        metric_name=row["metric_name"],
        metric_value=row["metric_value"],
        baseline_value=row["baseline_value"],
        kept=bool(row["kept"]),
        commit_sha=row["commit_sha"],
        duration_seconds=row["duration_seconds"],
        timestamp=_parse_dt(row["timestamp"]),
    )


def _row_to_problem(row: sqlite3.Row) -> Problem:
    return Problem(
        id=_parse_uuid(row["id"]),
        description=row["description"],
        source_claim_ids=[_parse_uuid(cid) for cid in json.loads(row["source_claim_ids"])],
        impact=row["impact"],
        confidence=row["confidence"],
        actionability=row["actionability"],
        classification=ProblemClassification(row["classification"]),
        status=ProblemStatus(row["status"]),
        timestamp=_parse_dt(row["timestamp"]),
    )


def _row_to_contradiction(row: sqlite3.Row) -> Contradiction:
    return Contradiction(
        id=_parse_uuid(row["id"]),
        claim_a_id=_parse_uuid(row["claim_a_id"]),
        claim_b_id=_parse_uuid(row["claim_b_id"]),
        detected_at=_parse_dt(row["detected_at"]),
        resolved_at=_parse_dt(row["resolved_at"]),
        resolution=row["resolution"],
    )


def _row_to_claim_from_archive(row: sqlite3.Row) -> Claim:
    return Claim(
        id=_parse_uuid(row["id"]),
        text=row["text"],
        level=ClaimLevel(row["level"]),
        confidence=row["confidence"],
        domain=Domain(row["domain"]),
        topic=row["topic"],
        entity=row["entity"],
        source_type=SourceType(row["source_type"]),
        source_ref=row["source_ref"],
        valid_from=_parse_dt(row["valid_from"]),
        valid_until=_parse_dt(row["valid_until"]),
        created_at=_parse_dt(row["created_at"]),
        promoted_at=_parse_dt(row["promoted_at"]),
        tags=json.loads(row["tags"]),
    )
