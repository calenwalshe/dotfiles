# Eval Plan -- knowledge-consolidation-engine

**Slug:** knowledge-consolidation-engine
**Status:** pending
**Timestamp:** 20260402T120000Z
**approval_required:** true

---

## 1. Eval Dimensions

Six dimensions, derived from the spec's acceptance criteria and the contract's done criteria. No generic padding -- each dimension targets a specific failure surface of the consolidation pipeline.

| ID | Dimension | Why it matters |
|----|-----------|----------------|
| D1 | Claim Lifecycle Correctness | The L0->L1->L2->L3 promotion chain is the pipeline's core value. Wrong promotions put unvalidated claims into MEMORY.md. Wrong blocks starve the knowledge base. |
| D2 | Contradiction/Corroboration Accuracy | NLI + cosine similarity are approximate. False negatives let contradictions into L2+. False corroboration inflates confidence. Both degrade downstream trust. |
| D3 | Cost Budget Adherence | The spec's economic model (<$0.10/cycle at 1K claims, hard cap $0.50) is a hard constraint. Budget overruns make the pipeline unusable for continuous operation. |
| D4 | Decay and Expiration Correctness | Wrong decay rates either expire valid knowledge or preserve stale facts. Domain-specific half-lives need to produce mathematically correct confidence curves. |
| D5 | Pipeline Integrity Under Scale | The 100-claim e2e test in the unit suite is necessary but not sufficient. Degradation patterns at 500, 1000, and 5000 claims reveal O(n^2) blowups, memory pressure, and HDBSCAN degeneration. |
| D6 | Dry-Run and Concurrency Safety | Dry-run must guarantee zero mutations. The file lock must prevent concurrent corruption. Both are safety rails for production use. |

---

## 2. Fixtures

### F1: Promotion Chain Fixture (D1)

A synthetic store with claims designed to exercise every promotion path and rejection reason.

```yaml
claims:
  # L0 -> L1: should promote (provenance + timestamp + short text)
  - text: "SQLite WAL mode improves concurrent reads"
    level: L0
    source_type: file
    source_ref: "/src/db.py"
    confidence: 0.8

  # L0 -> L1: should block (no provenance)
  - text: "Something about the database"
    level: L0
    source_type: file
    source_ref: ""
    confidence: 0.7

  # L0 -> L1: should block (text too long, >500 chars)
  - text: "<551 chars of compound claim text>"
    level: L0
    source_type: file
    source_ref: "/src/main.py"
    confidence: 0.8

  # L1 with 2 independent corroborations -> L2 candidate
  - text: "Python 3.12 added f-string improvements"
    level: L1
    source_type: url
    source_ref: "https://docs.python.org"
    corroborators:
      - { source_type: file, source_ref: "/notes.md" }
      - { source_type: conversation, source_ref: "session-5" }

  # L1 with corroboration from same source -> should NOT be L2 candidate
  - text: "Redis cache TTL is 300s"
    level: L1
    source_type: file
    source_ref: "/config.yaml"
    corroborators:
      - { source_type: file, source_ref: "/config.yaml" }
      - { source_type: file, source_ref: "/config.yaml" }

  # L2 with confidence >= 0.8 -> L3 candidate (Sonnet review)
  - text: "Deployments should use blue-green strategy"
    level: L2
    confidence: 0.9
    source_type: file
    source_ref: "/deploy.md"

  # L2 with confidence < 0.8 -> should NOT be L3 candidate
  - text: "Maybe use canary releases"
    level: L2
    confidence: 0.6
    source_type: conversation
    source_ref: "session-12"
```

### F2: Contradiction/Corroboration Fixture (D2)

Pairs with known ground truth for NLI and cosine similarity evaluation.

```yaml
contradiction_pairs:
  # Clear contradiction (expect NLI > 0.7)
  - a: "The API uses REST exclusively"
    b: "The API is built on GraphQL"
    expected: contradiction

  # Clear non-contradiction (expect NLI < 0.4)
  - a: "The server runs on port 8080"
    b: "The database uses PostgreSQL"
    expected: independent

  # Ambiguous (expect NLI 0.4-0.7, route to Claude)
  - a: "Python 3.12 is required"
    b: "Python 3.12+ is supported"
    expected: ambiguous

  # Subtle contradiction (same domain, conflicting specifics)
  - a: "Cache TTL is 300 seconds"
    b: "Cache TTL is 600 seconds"
    expected: contradiction

  # Paraphrase, not contradiction
  - a: "The API returns JSON"
    b: "Responses are in JSON format"
    expected: corroboration

corroboration_pairs:
  # Independent sources, similar claims -> corroborated
  - claims:
      - { text: "SQLite WAL mode is enabled", source: "file:/src/db.py" }
      - { text: "WAL mode active on SQLite", source: "url:https://wiki/db" }
      - { text: "Database uses WAL journaling", source: "conversation:session-3" }
    expected_count: 3

  # Same source, similar claims -> NOT corroborated
  - claims:
      - { text: "WAL mode enabled", source: "file:/src/db.py" }
      - { text: "WAL journal active", source: "file:/src/db.py" }
    expected_count: 0
```

### F3: Budget Stress Fixture (D3)

```yaml
scenarios:
  # Normal cycle: 1000 claims, expect <$0.10
  - claim_count: 1000
    l1_candidates: 50
    l2_candidates: 10
    ambiguous_pairs: 5
    expected_max_cost_usd: 0.10

  # Budget cap hit mid-cycle: 20 L1->L2 candidates but budget only allows 5
  - claim_count: 500
    l1_candidates: 20
    budget_cap: 0.01
    expected_queued: ">0"
    expected_promoted: "<20"

  # Zero budget: all LLM calls queued, pipeline still completes
  - claim_count: 100
    budget_cap: 0.00
    expected_queued: ">0"
    expected_exit_code: 0
```

### F4: Decay Matrix Fixture (D4)

```yaml
# One claim per domain, all starting at confidence 1.0
# Test at ages: 1 day, half-life, 2x half-life, 10x half-life
domains:
  codebase:    { half_life: 7,  ages: [1, 7, 14, 70] }
  competitive: { half_life: 14, ages: [1, 14, 28, 140] }
  operational: { half_life: 30, ages: [1, 30, 60, 300] }
  product:     { half_life: 60, ages: [1, 60, 120, 600] }
  user:        { half_life: 90, ages: [1, 90, 180, 900] }

# Expected: confidence = exp(-0.693 * age / half_life)
# At half_life: ~0.50
# At 2x half_life: ~0.25
# At 10x half_life: <0.001 (should be expired)

file_backed_claims:
  - source_ref: "/nonexistent/gone.py"
    expected: "immediate expiration (confidence 0.0)"
  - source_ref: "/tmp/exists.py"  # created during test
    expected: "normal decay"
```

### F5: Scale Fixture (D5)

```yaml
tiers:
  - claim_count: 100
    max_wall_time_seconds: 30
    max_memory_mb: 256

  - claim_count: 500
    max_wall_time_seconds: 120
    max_memory_mb: 512

  - claim_count: 1000
    max_wall_time_seconds: 300
    max_memory_mb: 1024

  - claim_count: 5000
    max_wall_time_seconds: 900
    max_memory_mb: 2048

# All tiers use mocked ML/LLM (no real model inference)
# Focus: O(n^2) detection, HDBSCAN cluster quality, memory usage
```

### F6: Safety Fixture (D6)

```yaml
dry_run:
  # Store snapshot before and after must be identical
  - claims: [10 L0, 5 L1, 2 L2]
    verify: "zero rows changed in claims table"
    verify: "zero rows in claims_archive"
    verify: "audit log has entries (in-memory only)"

concurrency:
  # Two Consolidator instances on same DB
  - action: "acquire lock, attempt second run"
    expected: "ConsolidatorLockError on second instance"
    verify: "first instance data integrity preserved"
```

---

## 3. Rubrics

### R1: Claim Lifecycle Correctness (D1)

| Criterion | Score | Definition |
|-----------|-------|------------|
| L0->L1 gate accuracy | Pass/Fail | All claims with valid provenance + timestamp + text <500 chars promote. All claims missing any gate stay L0. Zero false promotions, zero false blocks across fixture F1. |
| L1->L2 corroboration requirement | Pass/Fail | Only claims with >=2 independent corroborating sources become L2 candidates. Same-source corroboration is rejected. |
| L1->L2 LLM validation | Pass/Fail | Haiku approve -> L2. Haiku reject -> stays L1. No promotion without LLM call (when budget allows). |
| L2->L3 human gate | Pass/Fail | Sonnet proposes but does NOT auto-promote. Claim stays L2 until explicit approval. Low-confidence L2 (<0.8) not considered. |
| Audit completeness | Pass/Fail | Every promotion and skip produces an audit entry with phase, action, claim_id, reason, timestamp. Zero unlogged mutations. |

### R2: Contradiction/Corroboration Accuracy (D2)

| Criterion | Score | Definition |
|-----------|-------|------------|
| True positive rate (contradiction) | >= 0.80 | Of known contradictory pairs in F2, at least 80% produce a Contradiction record (NLI > 0.7) or route to Claude (NLI 0.4-0.7). |
| False positive rate (contradiction) | <= 0.10 | Of known non-contradictory pairs, at most 10% are flagged as contradictions or ambiguous. |
| Ambiguous routing | Pass/Fail | All pairs with NLI score in [0.4, 0.7] are returned as AmbiguousPair for Claude review. None are auto-resolved. |
| Corroboration source independence | Pass/Fail | Same-source pairs never count as corroboration regardless of cosine similarity. |
| Cold-start pairwise | Pass/Fail | <50 claims: pairwise NLI runs on all C(n,2) pairs. Cluster function is never called. |

### R3: Cost Budget Adherence (D3)

| Criterion | Score | Definition |
|-----------|-------|------------|
| Normal cycle cost | Pass/Fail | 1000-claim cycle with realistic promotion candidates costs <$0.50 (contract cap). Target <$0.10 (spec target). |
| Budget cap enforcement | Pass/Fail | When cumulative cost hits cap, remaining LLM calls are queued (not made). Pipeline exits 0. |
| Cost tracking accuracy | Pass/Fail | BudgetTracker.cumulative_cost matches sum of individual CallRecord costs within floating-point tolerance. |
| Queued carry-over | Pass/Fail | Budget.queued_count accurately reflects skipped calls. Summary includes all expected fields. |

### R4: Decay and Expiration Correctness (D4)

| Criterion | Score | Definition |
|-----------|-------|------------|
| Exponential decay formula | Pass/Fail | For every (domain, age) combination in F4, decayed confidence = original * exp(-0.693 * age_days / half_life_days), within tolerance of 0.01. |
| Half-life accuracy | Pass/Fail | A claim at exactly its half-life has confidence within [0.49, 0.51] of its original. |
| Expiration threshold | Pass/Fail | Claims decayed below 0.1 have valid_until set. Claims above 0.1 do not. |
| File-backed source check | Pass/Fail | Missing source_ref file -> immediate expiration (confidence 0.0, valid_until set). Existing file -> normal decay. |
| Archive trigger | Pass/Fail | Claims with valid_until older than 90 days move to claims_archive. Claims within 90 days stay. |

### R5: Pipeline Integrity Under Scale (D5)

| Criterion | Score | Definition |
|-----------|-------|------------|
| Wall time scaling | Warning/Fail | If 5000-claim tier takes >3x the time of 1000-claim tier (normalized per claim), flag O(n^2) regression. Fail if any tier exceeds its max_wall_time_seconds. |
| Memory scaling | Warning/Fail | If peak memory at 5000 claims exceeds 2048MB, fail. If it exceeds 1024MB, warn. |
| HDBSCAN stability | Pass/Fail | Cluster count at 1000 claims is between 5 and 200 (not 1 giant cluster, not 1000 singletons). Log actual distribution. |
| Phase ordering invariant | Pass/Fail | All 9 internal phases execute in order. No phase reads data that a prior phase has not yet written. Verified via audit log timestamps. |
| Projection output | Pass/Fail | MEMORY.md exists in output_dir after consolidation. File is non-empty. |

### R6: Dry-Run and Concurrency Safety (D6)

| Criterion | Score | Definition |
|-----------|-------|------------|
| Dry-run zero-mutation | Pass/Fail | After dry_run=True, every claim in the store has identical level, confidence, promoted_at, and valid_until as before the run. claims_archive is empty. claim_embeddings is empty (if dry-run covers embed phase). |
| Dry-run audit present | Pass/Fail | Audit log contains entries for all phases that would have executed. Entries are in-memory only (no JSONL file written). |
| Lock exclusion | Pass/Fail | Second Consolidator.run() raises ConsolidatorLockError while first holds lock. |
| Lock release on error | Pass/Fail | If a phase throws an exception, the lock is still released (finally block). Verified by acquiring lock after forced failure. |

---

## 4. Thresholds

| Dimension | Pass | Warn | Fail |
|-----------|------|------|------|
| D1: Lifecycle | All R1 criteria pass | N/A | Any R1 criterion fails |
| D2: Contradiction/Corroboration | TPR >= 0.80, FPR <= 0.10, all binary criteria pass | TPR 0.70-0.79 or FPR 0.11-0.15 | TPR < 0.70 or FPR > 0.15 or any binary criterion fails |
| D3: Budget | All R3 criteria pass, normal cycle < $0.10 | Normal cycle $0.10-$0.50 | Normal cycle > $0.50 or cap enforcement fails |
| D4: Decay | All R4 criteria pass within tolerance 0.01 | Any value off by 0.01-0.05 | Any value off by > 0.05 or expiration logic wrong |
| D5: Scale | All tiers within time/memory limits, no O(n^2) regression | 5000-claim tier within 1.5x of limit | Any tier exceeds limit or O(n^2) detected |
| D6: Safety | All R6 criteria pass | N/A | Any R6 criterion fails |

**Overall pass:** All six dimensions pass or warn. Zero fails.

**Overall warn:** One or more dimensions in warn state. Acceptable for merge with noted calibration debt.

**Overall fail:** Any dimension fails. Block merge.

---

## 5. Failure Taxonomy

Known failure modes to monitor, ordered by estimated likelihood (from spec risk table and implementation review).

### FT1: Cosine Threshold Miscalibration (High Likelihood)

**Symptom:** False corroboration (claims that are topically related but not actually saying the same thing score above 0.85) or missed corroboration (genuine paraphrases score below 0.85).

**Root cause:** MiniLM-L6-v2 embeddings may not separate claim-level semantic similarity from topic-level similarity at the 0.85 cosine threshold.

**Detection:** Run F2 corroboration pairs. If >20% of ground-truth corroborations are missed or >10% of non-corroborations are flagged, the threshold needs adjustment.

**Mitigation:** Lower to 0.80 (spec suggests this). Benchmark against mpnet-base-v2 as spec recommends.

### FT2: HDBSCAN Degeneration (Medium Likelihood)

**Symptom:** Either one giant cluster (all claims compared pairwise, O(n^2) blowup) or all singletons (no within-cluster NLI comparisons, contradictions missed).

**Root cause:** min_cluster_size default too low or too high for the claim embedding distribution. Claim embeddings from MiniLM-L6-v2 may not have sufficient variance for density-based clustering.

**Detection:** F5 scale fixture logs cluster count and sizes. One cluster or >80% singletons triggers this failure.

**Mitigation:** Cold-start path (<50 claims) already bypasses clustering. For larger stores, tune min_cluster_size or fall back to KMeans with fixed k.

### FT3: Domain Half-Life Defaults Wrong (High Likelihood, per spec)

**Symptom:** Codebase claims (7-day half-life) expire before developers can act on them. User claims (90-day half-life) persist long after user behavior has changed.

**Root cause:** All half-lives are CALIBRATE-flagged defaults with no empirical basis.

**Detection:** F4 decay matrix produces the mathematically correct decay curve, but the eval cannot validate whether the defaults are appropriate for real usage. This is a known limitation.

**Mitigation:** Log every decay action in audit trail. After 10 production cycles, compare expired claims against manual review to calibrate.

### FT4: LLM Response Parsing Failure (Medium Likelihood)

**Symptom:** Promotion phase crashes or silently skips claims when Claude returns unexpected JSON structure.

**Root cause:** Mock LLM in tests always returns well-formed `{"validated": true/false, "reasoning": "..."}`. Real Claude responses may include extra fields, different casing, or natural language instead of JSON.

**Detection:** Not directly testable in this eval (mocked LLM). Flag for live integration test with real Claude API.

**Mitigation:** Defensive parsing in promote.py. Wrap JSON decode in try/except, treat parse failure as rejection (not crash).

### FT5: Dry-Run Transaction Leak (Low Likelihood, High Impact)

**Symptom:** Dry-run modifies the store. Claims are promoted, archived, or decayed when they should not be.

**Root cause:** `_NoCommitConnection` wrapper fails to intercept a commit path, or SQLite autocommit behavior bypasses the wrapper.

**Detection:** F6 dry-run fixture with full before/after comparison of every row.

**Mitigation:** The current implementation wraps `conn.commit()` as a no-op and calls `conn.rollback()` in the finally block. Eval should verify both paths.

### FT6: Lock File Race Condition (Low Likelihood)

**Symptom:** Two consolidator instances run simultaneously, producing duplicate contradictions or double-promoting claims.

**Root cause:** fcntl.LOCK_EX | LOCK_NB should prevent this, but edge cases exist (NFS, container restarts, stale lock files).

**Detection:** F6 concurrency fixture. Stress test: rapid sequential acquire/release cycles to check for leaks.

**Mitigation:** Lock file is at `/tmp/consolidator.lock`. If lock is stale (process dead), manual removal is required. No automatic stale-lock detection in current implementation.

### FT7: Budget Tracker Floating-Point Drift (Low Likelihood)

**Symptom:** After many small LLM calls, cumulative_cost drifts from the true sum of individual call costs. Budget cap triggers too early or too late.

**Root cause:** Repeated floating-point addition of small USD amounts.

**Detection:** After 100+ mock LLM calls, compare `budget.cumulative_cost` against `sum(c.cost for c in budget.calls)`. Tolerance: 1e-10.

**Mitigation:** Current implementation uses plain float addition. If drift is detected, switch to `decimal.Decimal`.

---

## 6. Execution Notes

- All fixtures use mocked ML models (`_fake_embed_fn`, `mock_nli`) and mocked LLM (`_make_mock_llm`). No real model inference or API calls during eval execution.
- D2 accuracy metrics (TPR, FPR) are measured against fixture ground truth, not real NLI model output. A separate benchmark (spec task B5) should evaluate real model accuracy.
- D5 scale fixtures require wall-clock timing and memory measurement (e.g., `tracemalloc` or `/proc/self/status`).
- This eval plan covers the contract deliverables as implemented. It does not cover future scope items (adaptive decay, compound claim splitting, Postgres adapter).
- The existing 38 unit tests cover individual phase correctness. This eval plan adds cross-cutting concerns: lifecycle end-to-end, scale degradation, budget economics, and safety invariants that span multiple phases.
