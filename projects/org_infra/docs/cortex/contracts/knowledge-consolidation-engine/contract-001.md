# Contract -- knowledge-consolidation-engine-001

**ID:** knowledge-consolidation-engine-001
**Slug:** knowledge-consolidation-engine
**Phase:** execute
**Status:** draft
**Timestamp:** 20260402T060000Z

---

## Objective

Build a 7-phase knowledge consolidation pipeline that runs as a standalone CLI, promotes claims through maturity levels (L0->L1->L2->L3), detects contradictions using local NLI models, identifies corroboration using embeddings, decays stale facts with domain-specific half-lives, archives expired claims, and triggers Markdown projection regeneration -- all through StoreProtocol, at <$0.10/cycle for 1000 claims.

---

## Deliverables

- `src/consolidator/__init__.py` -- Consolidator class, phase runner
- `src/consolidator/__main__.py` -- CLI entry point
- `src/consolidator/config.py` -- half-lives, thresholds, budget caps (CALIBRATE-flagged)
- `src/consolidator/audit.py` -- structured JSON-lines audit logger
- `src/consolidator/store_adapter.py` -- ConsolidatorStore wrapping StoreProtocol (embedding + archive ops)
- `src/consolidator/budget.py` -- per-cycle cost tracker with cap enforcement
- `src/consolidator/phases/embed.py` -- Phase 1: sentence-transformers embedding
- `src/consolidator/phases/contradict.py` -- Phase 2: HDBSCAN + NLI contradiction detection
- `src/consolidator/phases/corroborate.py` -- Phase 3: cosine similarity + source independence
- `src/consolidator/phases/promote.py` -- Phase 4: rule-based (L0->L1), Haiku (L1->L2), Sonnet (L2->L3)
- `src/consolidator/phases/decay.py` -- Phase 5: exponential decay with domain half-lives
- `src/consolidator/phases/archive.py` -- Phase 6: expired/extracted claims to cold table
- `src/protocols/sqlite_store.py` -- additive changes: `claim_embeddings` table, `claims_archive` table
- `tests/test_consolidator.py` -- unit + integration tests for all phases and acceptance criteria

---

## Scope

**In scope:**
- All 7 consolidation phases
- CLI with `--dry-run`, `--phase`, `--verbose` flags
- ConsolidatorStore adapter for embedding and archive operations
- Claude Haiku/Sonnet integration for promotion validation
- Budget tracking and cap enforcement
- Audit trail for every mutation
- Concurrency guard (file lock)
- Tests with synthetic claims (mock Claude, mock models for CI)

**Out of scope:**
- StoreProtocol interface changes
- Perceiver or projector modifications
- Postgres adapter
- Compound claim splitting via LLM
- Adaptive decay rates
- Web UI for contradiction resolution

---

## Write Roots

The executing agent is authorized to write to:

- `src/consolidator/`
- `src/protocols/sqlite_store.py` (additive only: new tables, new methods)
- `tests/test_consolidator.py`

All other paths are read-only during execution.

---

## Done Criteria

- [ ] `python -m src.consolidator --db knowledge.db` runs full 7-phase pipeline, exits 0
- [ ] L0 claims with provenance + timestamp + atomic text promote to L1
- [ ] L1 claims with >=2 independent corroborating sources are L2 candidates
- [ ] L1->L2 promotion requires Claude Haiku validation
- [ ] L2->L3 promotion requires Claude Sonnet proposal + human approval gate
- [ ] Contradictory pairs (NLI >0.7) produce Contradiction records in store
- [ ] Ambiguous pairs (NLI 0.4-0.7) route to Claude for review
- [ ] Confidence decays exponentially with domain-specific half-lives
- [ ] Expired claims (confidence <0.1, >90 days) move to archive table
- [ ] Every action writes audit log entry with structured reason
- [ ] Full cycle at 1000 claims costs <$0.50 in LLM calls
- [ ] `--dry-run` reports all proposed changes without modifying store
- [ ] Markdown projections regenerated after consolidation
- [ ] Cold-start (<50 claims) completes without errors

---

## Validators

```bash
# Phase A: Foundation (no ML, no LLM)
pytest tests/test_consolidator.py -k "test_decay" -v
pytest tests/test_consolidator.py -k "test_archive" -v
pytest tests/test_consolidator.py -k "test_l0_to_l1" -v
pytest tests/test_consolidator.py -k "test_audit" -v

# Phase B: Embeddings + Corroboration
pytest tests/test_consolidator.py -k "test_embed" -v
pytest tests/test_consolidator.py -k "test_corroboration" -v

# Phase C: Contradiction Detection
pytest tests/test_consolidator.py -k "test_contradiction_detected" -v
pytest tests/test_consolidator.py -k "test_ambiguous_routing" -v
pytest tests/test_consolidator.py -k "test_cold_start" -v

# Phase D: LLM Promotion
pytest tests/test_consolidator.py -k "test_l1_to_l2" -v
pytest tests/test_consolidator.py -k "test_l2_to_l3" -v
pytest tests/test_consolidator.py -k "test_budget" -v

# Phase E: Integration
pytest tests/test_consolidator.py -k "test_dry_run" -v
pytest tests/test_consolidator.py -k "test_projection" -v
pytest tests/test_consolidator.py -k "test_e2e" -v

# Full suite
pytest tests/test_consolidator.py -v
```

---

## Eval Plan

docs/cortex/evals/knowledge-consolidation-engine/eval-plan.md (pending)

---

## Approvals

- [x] Spec approved
- [x] Contract approved

---

## Rollback Hints

If execution needs to be undone:
- Delete `src/consolidator/` directory
- Delete `tests/test_consolidator.py`
- Revert additive changes to `src/protocols/sqlite_store.py` (drop `claim_embeddings` and `claims_archive` tables, remove associated methods)
- No external systems modified -- Claude API is called but does not persist state
- No schema changes to existing tables -- rollback is clean at any point
