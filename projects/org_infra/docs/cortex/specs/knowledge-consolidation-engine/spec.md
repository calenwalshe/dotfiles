# Spec -- knowledge-consolidation-engine

**Slug:** knowledge-consolidation-engine
**Status:** draft
**Timestamp:** 20260402T060000Z

---

## 1. Problem

The autonomous R&D platform ingests observations through perceivers (codebase, conversations, APIs) and writes them as L0 claims into the knowledge store. Without a consolidation process, these raw observations accumulate indefinitely -- the store grows but never matures. L0 claims are noisy, unvalidated, potentially contradictory, and increasingly stale. The downstream consumers (agents reading MEMORY.md, decision journals, experiment logs) operate on whatever the projector renders, which means they inherit every unvalidated assertion and every expired fact.

The Consolidator is the missing lifecycle manager. It runs between sessions to promote claims through maturity levels (L0 raw -> L1 extracted -> L2 validated -> L3 actionable), detect contradictions, decay stale facts, archive expired knowledge, and trigger projection regeneration. Without it, the knowledge store is a write-only log. With it, the store becomes a curated, self-maintaining knowledge base where claim quality improves over time and stale or contradictory information is surfaced and resolved.

The core technical challenge is doing this cheaply. A naive approach (send every claim pair to an LLM for contradiction detection, send every claim to an LLM for promotion) costs ~$5-10 per cycle at 1000 claims. The hybrid approach -- open-source NLI models for contradiction detection, embeddings for corroboration, rule-based extraction, LLM only for promotion validation -- brings this to ~$0.05-0.08 per cycle. The architecture must be a pipeline where each phase is independently testable, the LLM is used only where judgment is required, and all local models are open source with inspectable code.

---

## 2. Scope

### In Scope

- 7-phase consolidation pipeline: Embed, Detect Contradictions, Detect Corroboration, Promote, Decay, Archive, Project
- Standalone CLI entry point: `python -m src.consolidator --db knowledge.db`
- Embedding generation using sentence-transformers (all-MiniLM-L6-v2)
- Contradiction detection using HDBSCAN clustering + cross-encoder NLI model
- Corroboration detection using cosine similarity + source independence check
- Rule-based L0->L1 promotion (provenance, timestamp, atomicity checks)
- LLM-validated L1->L2 promotion (Claude Haiku, ~10-20 calls/cycle)
- LLM-proposed L2->L3 promotion (Claude Sonnet, human approval gate)
- Exponential decay with domain-specific half-lives
- Archive table for expired and extracted claims
- Audit trail for every promotion, demotion, contradiction, and archive action
- Embedding storage (new column or table in SQLite store)
- Trigger of existing Markdown projector after consolidation completes
- Unit and integration tests with synthetic claims

### Out of Scope

- New perceiver development (perceivers write L0 claims; Consolidator reads them)
- Projector modifications (Phase 7 calls the existing projector as-is)
- StoreProtocol interface changes (Consolidator works within the current API; archive table is an implementation detail of the SQLite adapter)
- Postgres migration (Consolidator codes against StoreProtocol; Postgres is a future adapter)
- Real-time / streaming consolidation (batch pipeline only)
- Compound claim splitting beyond rule-based (LLM splitting is a future enhancement)
- Adaptive decay rates (fixed rates with calibration flags for MVP)
- Web UI or dashboard for contradiction resolution (Markdown projection is the interface)

---

## 3. Architecture Decision

**Chosen approach:** 7-phase hybrid pipeline. Local open-source models handle the expensive O(n) and O(n^2)-reducible operations (embedding, clustering, NLI classification, corroboration). Claude API handles only the judgment calls that require reasoning (promotion validation at L1->L2 and L2->L3). Each phase is a pure function: reads store state, writes store state, returns a structured audit log.

**Rationale:** The hybrid approach achieves <$0.10/cycle at 1000 claims vs ~$5-10 for full-LLM. Local NLI models (cross-encoder/nli-MiniLM2-L6-H768) achieve ~85% accuracy on contradiction detection -- good enough when ambiguous cases (score 0.4-0.7) fall through to Claude for final judgment. The 7-phase structure means each phase can be tested, benchmarked, and replaced independently. The pipeline is sequential (each phase depends on the prior phase's writes) but phases are internally parallelizable.

**Alternatives rejected:**

| Alternative | Rejection reason |
|---|---|
| Full-LLM consolidation (Letta-style) | Claims are typed Pydantic models with structured metadata. LLM is unnecessary for metadata comparisons, math operations, and embedding lookups. Cost is 50-100x higher. |
| Rule-only (no LLM at all) | L1->L2 promotion requires judgment about whether corroborating evidence actually validates a claim. Rule-based checks miss semantic nuance. False promotion to L2/L3 is high-cost because it enters MEMORY.md. |
| Graph-based knowledge store (Cognee-style) | Adds a knowledge graph layer on top of the existing typed claim store. Premature for <10K claims. The typed schema with embeddings handles corroboration and contradiction without graph traversal. Revisit if claim relationships become complex. |
| Hosted NLI API (e.g., HuggingFace Inference API) | Adds network dependency, costs money, and sends claim data to third-party infrastructure. Local CPU inference at 22s/1000 claims is acceptable for a background batch job. |

**Pipeline phases in execution order:**

```
Phase 1: EMBED       -- sentence-transformers, local, $0.00
Phase 2: CONTRADICT  -- HDBSCAN + NLI, local + ~5 Claude calls, ~$0.01
Phase 3: CORROBORATE -- cosine + metadata, local, $0.00
Phase 4: PROMOTE     -- rules (L0->L1) + Claude Haiku (L1->L2) + Claude Sonnet (L2->L3), ~$0.02-0.05
Phase 5: DECAY       -- exponential math, local, $0.00
Phase 6: ARCHIVE     -- SQL moves, local, $0.00
Phase 7: PROJECT     -- existing projector, local, $0.00
```

---

## 4. Interfaces

### Reads (from StoreProtocol)

| Method | Used by phase | Purpose |
|---|---|---|
| `query_claims(level=L0)` | Promote (L0->L1) | Get unprocessed raw claims |
| `query_claims(level=L1)` | Corroborate, Promote (L1->L2) | Get extracted claims for corroboration check |
| `query_claims(level=L2)` | Promote (L2->L3) | Get validated claims for actionability review |
| `query_claims()` (all) | Embed, Decay | All claims for embedding and decay sweep |
| `query_evidence(claim_id=...)` | Promote | Supporting/contradicting evidence for promotion decisions |
| `query_contradictions(unresolved_only=True)` | Contradict | Avoid re-flagging known contradictions |
| `get_claim(claim_id)` | All phases | Individual claim lookup |
| `search_semantic(text, top_k)` | Corroborate | Find semantically similar claims |

### Writes (to StoreProtocol)

| Method | Used by phase | Purpose |
|---|---|---|
| `update_claim(id, level=..., confidence=..., promoted_at=..., valid_until=...)` | Promote, Decay | Level changes, confidence updates, expiration |
| `write_contradiction(contradiction)` | Contradict | New contradiction records |
| `write_evidence(evidence)` | Promote | Audit trail entries for promotion decisions |
| `write_artifact(artifact)` | Project | Record regenerated projections |

### New store capabilities required

| Capability | Reason | Implementation |
|---|---|---|
| Embedding storage | Phase 1 needs to persist embeddings for Phase 2/3 | New `claim_embeddings` table: `claim_id UUID PK, embedding BLOB, model TEXT, created_at DATETIME` |
| Archive table | Phase 6 needs cold storage | New `claims_archive` table (same schema as `claims`), plus `archived_at DATETIME, archive_reason TEXT` |
| Bulk claim query | Phases 1/5 need all claims efficiently | `query_claims()` with no filters already returns up to `limit` claims; may need pagination or unlimited mode |

These are additive changes to `sqlite_store.py` -- they do not modify the `StoreProtocol` abstract interface. The Consolidator accesses archive and embedding operations through a `ConsolidatorStore` adapter that wraps `StoreProtocol` and adds the consolidation-specific methods.

### External interfaces

| System | Direction | Protocol | Purpose |
|---|---|---|---|
| Claude API (Haiku) | Outbound | HTTPS / anthropic SDK | L1->L2 promotion validation (~10-20 calls/cycle) |
| Claude API (Sonnet) | Outbound | HTTPS / anthropic SDK | L2->L3 promotion proposal, ambiguous contradiction review (~5-7 calls/cycle) |
| Local sentence-transformers | In-process | Python API | Claim embedding generation |
| Local NLI model | In-process | Python API (transformers) | Contradiction classification |
| Existing Markdown projector | In-process | Python function call | Projection regeneration (Phase 7) |

---

## 5. Dependencies

| Package | Version | License | Purpose | Replaceable |
|---|---|---|---|---|
| `sentence-transformers` | >=2.2.0 | Apache 2.0 | Claim embeddings (all-MiniLM-L6-v2, 384-dim) | Yes -- any embedding model |
| `transformers` | >=4.30.0 | Apache 2.0 | NLI model inference (cross-encoder/nli-MiniLM2-L6-H768) | Yes -- ONNX runtime |
| `hdbscan` | >=0.8.33 | BSD 3-Clause | Density-based clustering for O(n^2) avoidance | Yes -- sklearn DBSCAN, KMeans |
| `torch` | >=2.0.0 | BSD 3-Clause | Model runtime for sentence-transformers and NLI | Yes -- ONNX |
| `anthropic` | >=0.20.0 | MIT | Claude API SDK for promotion validation | Required (Claude-only policy) |
| `numpy` | >=1.24.0 | BSD 3-Clause | Cosine similarity, embedding math | Transitive dep of sentence-transformers |

**Pre-existing (no new install):**
- `pydantic` (v2) -- schemas
- `sqlite3` -- stdlib, store backend

**Model downloads (first run):**
- `sentence-transformers/all-MiniLM-L6-v2` (~80MB)
- `cross-encoder/nli-MiniLM2-L6-H768` (~110MB)

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| NLI model accuracy insufficient (<80%) on our claim corpus | Medium | Missed contradictions enter L2/L3 | Widen ambiguous band (0.3-0.7 instead of 0.4-0.7) to send more cases to Claude. Monitor false negative rate in audit logs. |
| Embedding model quality too low for corroboration at cosine 0.85 | Medium | False corroboration leads to premature promotion | Benchmark MiniLM-L6-v2 vs all-mpnet-base-v2 on synthetic claim pairs before committing. Lower threshold to 0.80 if needed. |
| Claude API costs exceed budget at scale | Low | Budget overrun | Phase 4 has explicit call count caps per cycle. If exceeded, queue remainder for next cycle. Budget tracking in audit log. |
| HDBSCAN produces degenerate clusters (too few or too many) | Medium | Either O(n^2) fallback or missed contradictions | Cold-start path (<50 claims) skips clustering. Monitor cluster distribution in audit log. Tune min_cluster_size. |
| Domain half-life defaults are wrong | High | Claims expire too fast or too slow | Flag all decay rates as `CALIBRATE` in config. Log every decay action for retrospective analysis. Allow per-domain override. |
| Torch/sentence-transformers too heavy for deployment environment | Low | Infra issues | Models are ~200MB total. CPU inference only -- no GPU required. Can swap to ONNX runtime if needed. |
| Consolidator runs concurrently with perceiver writes | Medium | Race conditions on claim state | File lock on DB during consolidation cycle. Alternatively, snapshot claims at cycle start and only process the snapshot. |

---

## 7. Sequencing

Phases are ordered by dependency. Each checkpoint is a testable milestone.

### Phase A: Foundation (no ML, no LLM)

1. **Consolidator skeleton** -- CLI entry point, phase runner, audit logger, config
2. **ConsolidatorStore adapter** -- wraps StoreProtocol, adds embedding table and archive table
3. **Phase 5: Decay** -- pure math, no dependencies, immediately testable
4. **Phase 6: Archive** -- SQL operations, depends on archive table from step 2
5. **Phase 4a: L0->L1 Promote** -- rule-based only, no ML

**Checkpoint A:** Decay, archive, and L0->L1 promotion work end-to-end with synthetic claims. All audit logs written. Zero external dependencies.

### Phase B: Embeddings + Corroboration (local ML, no LLM)

6. **Phase 1: Embed** -- sentence-transformers integration, embedding storage
7. **Phase 3: Corroborate** -- cosine similarity + source independence check
8. **Embedding benchmark** -- MiniLM-L6-v2 vs mpnet-base-v2 on synthetic pairs

**Checkpoint B:** Claims are embedded, corroboration candidates identified. Still no LLM calls.

### Phase C: Contradiction Detection (local ML, minimal LLM)

9. **Phase 2: Contradict** -- HDBSCAN clustering + NLI classification
10. **Ambiguous case routing** -- NLI score 0.4-0.7 queued for Claude review

**Checkpoint C:** Contradictions detected locally. Ambiguous cases flagged. Full local pipeline operational.

### Phase D: LLM-Validated Promotion (Claude integration)

11. **Phase 4b: L1->L2 Promote** -- Claude Haiku validates corroborated claims
12. **Phase 4c: L2->L3 Promote** -- Claude Sonnet proposes, human approval gate
13. **Budget tracking** -- per-cycle cost calculation, cap enforcement

**Checkpoint D:** Full 7-phase pipeline operational. Cost per cycle measured and within budget.

### Phase E: Integration + Hardening

14. **Phase 7: Project** -- wire existing Markdown projector as final phase
15. **End-to-end test** -- full cycle with realistic synthetic store (100+ claims)
16. **Concurrency guard** -- file lock or snapshot isolation for perceiver coexistence
17. **CLI polish** -- `--dry-run`, `--phase`, `--verbose` flags

**Checkpoint E:** Production-ready. All acceptance criteria met.

---

## 8. Tasks

### Phase A: Foundation

- [ ] A1. Create `src/consolidator/__init__.py` with `Consolidator` class skeleton (phase runner, config, audit log)
- [ ] A2. Create `src/consolidator/__main__.py` CLI entry point (`python -m src.consolidator --db knowledge.db`)
- [ ] A3. Create `src/consolidator/config.py` with domain half-lives, thresholds, and LLM budget caps (all values flagged as CALIBRATE)
- [ ] A4. Create `src/consolidator/audit.py` -- structured audit log (JSON lines) recording every action with reason
- [ ] A5. Add `claim_embeddings` table to `sqlite_store.py` (claim_id, embedding, model, created_at)
- [ ] A6. Add `claims_archive` table to `sqlite_store.py` (same schema as claims + archived_at, archive_reason)
- [ ] A7. Create `src/consolidator/store_adapter.py` -- ConsolidatorStore wrapping StoreProtocol with embedding and archive methods
- [ ] A8. Implement Phase 5 (Decay) in `src/consolidator/phases/decay.py` -- exponential decay, source-linked check, expiration
- [ ] A9. Implement Phase 6 (Archive) in `src/consolidator/phases/archive.py` -- move expired/extracted claims to archive table
- [ ] A10. Implement Phase 4a (L0->L1 Promote) in `src/consolidator/phases/promote.py` -- rule-based provenance, timestamp, atomicity checks
- [ ] A11. Write tests for decay (synthetic claims across all 5 domains, boundary conditions)
- [ ] A12. Write tests for archive (expired claims move, non-expired stay, archive is queryable)
- [ ] A13. Write tests for L0->L1 promotion (pass/fail cases for each rule)

### Phase B: Embeddings + Corroboration

- [ ] B1. Implement Phase 1 (Embed) in `src/consolidator/phases/embed.py` -- sentence-transformers integration, skip already-embedded claims
- [ ] B2. Implement Phase 3 (Corroborate) in `src/consolidator/phases/corroborate.py` -- cosine similarity, source independence check
- [ ] B3. Write tests for embedding (correct dimensions, idempotent re-runs)
- [ ] B4. Write tests for corroboration (independent sources detected, same-source rejected, threshold behavior)
- [ ] B5. Benchmark MiniLM-L6-v2 vs mpnet-base-v2 on 50 synthetic claim pairs (document results in audit log)

### Phase C: Contradiction Detection

- [ ] C1. Implement Phase 2 (Contradict) in `src/consolidator/phases/contradict.py` -- HDBSCAN clustering, NLI within clusters, cold-start pairwise path
- [ ] C2. Implement ambiguous case routing (NLI 0.4-0.7 -> Claude review queue)
- [ ] C3. Write tests for contradiction detection (known contradictory pairs, known non-contradictory, ambiguous routing)
- [ ] C4. Write tests for cold-start path (<50 claims, pairwise without clustering)

### Phase D: LLM-Validated Promotion

- [ ] D1. Implement Phase 4b (L1->L2 Promote) in `src/consolidator/phases/promote.py` -- Claude Haiku validation of corroborated claims
- [ ] D2. Implement Phase 4c (L2->L3 Promote) in `src/consolidator/phases/promote.py` -- Claude Sonnet proposal + human approval placeholder
- [ ] D3. Implement budget tracking in `src/consolidator/budget.py` -- per-cycle cost accumulator, cap enforcement, carry-over queue
- [ ] D4. Write tests for L1->L2 promotion (mock Claude responses: approve, reject, with reasoning)
- [ ] D5. Write tests for L2->L3 promotion (mock Claude responses + approval gate)
- [ ] D6. Write tests for budget cap (cycle terminates gracefully when budget exceeded)

### Phase E: Integration + Hardening

- [ ] E1. Wire Phase 7 (Project) -- call existing `src/projectors/markdown.py` as final phase
- [ ] E2. End-to-end integration test -- synthetic store with 100+ claims across all domains, run full 7-phase cycle, verify audit log completeness
- [ ] E3. Implement concurrency guard (file lock on DB during consolidation)
- [ ] E4. Add CLI flags: `--dry-run` (report what would change), `--phase N` (run single phase), `--verbose` (detailed logging)
- [ ] E5. Write end-to-end test validating all acceptance criteria

---

## 9. Acceptance Criteria

| ID | Criterion | Validator |
|---|---|---|
| AC1 | `python -m src.consolidator --db knowledge.db` runs the full 7-phase pipeline and exits 0 | CLI smoke test |
| AC2 | L0 claims with provenance, timestamp, and atomic text are promoted to L1 | `pytest tests/test_consolidator.py -k "test_l0_to_l1"` |
| AC3 | L1 claims with >=2 independent corroborating sources are candidates for L2 promotion | `pytest tests/test_consolidator.py -k "test_corroboration"` |
| AC4 | L1->L2 promotion requires Claude Haiku validation (mocked in tests) | `pytest tests/test_consolidator.py -k "test_l1_to_l2"` |
| AC5 | L2->L3 promotion requires Claude Sonnet proposal + human approval gate | `pytest tests/test_consolidator.py -k "test_l2_to_l3"` |
| AC6 | Contradictory claim pairs (NLI score >0.7) produce Contradiction records in the store | `pytest tests/test_consolidator.py -k "test_contradiction_detected"` |
| AC7 | Ambiguous pairs (NLI 0.4-0.7) are routed to Claude for review | `pytest tests/test_consolidator.py -k "test_ambiguous_routing"` |
| AC8 | Claim confidence decays exponentially with domain-specific half-lives | `pytest tests/test_consolidator.py -k "test_decay"` |
| AC9 | Expired claims (confidence <0.1, >90 days old) are moved to archive table | `pytest tests/test_consolidator.py -k "test_archive"` |
| AC10 | Every promotion, demotion, contradiction, and archive action writes an audit log entry with reason | `pytest tests/test_consolidator.py -k "test_audit"` |
| AC11 | Full cycle at 1000 claims costs <$0.50 in LLM calls (budget tracker validates) | `pytest tests/test_consolidator.py -k "test_budget"` |
| AC12 | `--dry-run` flag reports all proposed changes without modifying the store | `pytest tests/test_consolidator.py -k "test_dry_run"` |
| AC13 | Markdown projections are regenerated after consolidation completes | `pytest tests/test_consolidator.py -k "test_projection"` |
| AC14 | Cold-start path (<50 claims) completes without errors (pairwise contradiction check, relaxed corroboration) | `pytest tests/test_consolidator.py -k "test_cold_start"` |
