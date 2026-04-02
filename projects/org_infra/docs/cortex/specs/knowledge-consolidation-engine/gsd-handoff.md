# GSD Handoff -- knowledge-consolidation-engine

**Status:** pending human import into GSD
**Contract:** docs/cortex/contracts/knowledge-consolidation-engine/contract-001.md
**DO NOT auto-execute -- human must import this into GSD explicitly**

---

## Objective

Build a 7-phase knowledge consolidation pipeline that promotes claims through maturity levels (L0->L1->L2->L3), detects contradictions via local NLI models, identifies corroboration via embeddings, decays stale facts with domain-specific half-lives, archives expired claims, and regenerates Markdown projections. The pipeline runs as a standalone CLI (`python -m src.consolidator --db knowledge.db`), talks only to StoreProtocol, uses open-source local models for the heavy lifting, and reserves Claude API calls for promotion validation only. Target cost: <$0.10 per cycle at 1000 claims.

---

## Deliverables

| Artifact | Path |
|---|---|
| Consolidator package | `src/consolidator/` |
| CLI entry point | `src/consolidator/__main__.py` |
| Config (half-lives, thresholds, budget) | `src/consolidator/config.py` |
| Audit logger | `src/consolidator/audit.py` |
| Store adapter (embeddings, archive) | `src/consolidator/store_adapter.py` |
| Budget tracker | `src/consolidator/budget.py` |
| Phase 1: Embed | `src/consolidator/phases/embed.py` |
| Phase 2: Contradict | `src/consolidator/phases/contradict.py` |
| Phase 3: Corroborate | `src/consolidator/phases/corroborate.py` |
| Phase 4: Promote | `src/consolidator/phases/promote.py` |
| Phase 5: Decay | `src/consolidator/phases/decay.py` |
| Phase 6: Archive | `src/consolidator/phases/archive.py` |
| Embedding + archive tables | `src/protocols/sqlite_store.py` (additive changes) |
| Test suite | `tests/test_consolidator.py` |

---

## Requirements

Existing infrastructure this build depends on (DO NOT rebuild):

| Component | Path | Status |
|---|---|---|
| Claim, Evidence, Contradiction schemas | `src/protocols/schemas.py` | Stable, 40 tests passing |
| StoreProtocol interface | `src/protocols/store.py` | Stable |
| SQLite adapter | `src/protocols/sqlite_store.py` | Stable, full CRUD |
| Markdown projector | `src/projectors/markdown.py` | Stable |
| Codebase perceiver | `src/perceivers/codebase.py` | Stable, writes L0 claims |

---

## Tasks

### Phase A: Foundation (no ML, no LLM)

1. - [ ] Create Consolidator class skeleton with phase runner, config, audit log
2. - [ ] Create CLI entry point (`python -m src.consolidator --db knowledge.db`)
3. - [ ] Create config module with domain half-lives, thresholds, budget caps
4. - [ ] Create structured audit logger (JSON lines)
5. - [ ] Add `claim_embeddings` table to SQLite store
6. - [ ] Add `claims_archive` table to SQLite store
7. - [ ] Create ConsolidatorStore adapter wrapping StoreProtocol
8. - [ ] Implement Phase 5: Decay (exponential, source-linked check)
9. - [ ] Implement Phase 6: Archive (move expired/extracted to cold table)
10. - [ ] Implement Phase 4a: L0->L1 Promote (rule-based)
11. - [ ] Write tests for decay, archive, and L0->L1 promotion

### Phase B: Embeddings + Corroboration (local ML, no LLM)

12. - [ ] Implement Phase 1: Embed (sentence-transformers, skip already-embedded)
13. - [ ] Implement Phase 3: Corroborate (cosine >0.85, source independence)
14. - [ ] Write tests for embedding and corroboration
15. - [ ] Benchmark MiniLM-L6-v2 vs mpnet-base-v2 on synthetic pairs

### Phase C: Contradiction Detection (local ML, minimal LLM)

16. - [ ] Implement Phase 2: Contradict (HDBSCAN + NLI, cold-start path)
17. - [ ] Implement ambiguous case routing (0.4-0.7 -> Claude queue)
18. - [ ] Write tests for contradiction detection and cold-start

### Phase D: LLM-Validated Promotion (Claude integration)

19. - [ ] Implement Phase 4b: L1->L2 Promote (Claude Haiku validation)
20. - [ ] Implement Phase 4c: L2->L3 Promote (Claude Sonnet + human gate)
21. - [ ] Implement budget tracker with per-cycle caps
22. - [ ] Write tests for LLM promotion and budget enforcement

### Phase E: Integration + Hardening

23. - [ ] Wire Phase 7: Project (call existing Markdown projector)
24. - [ ] End-to-end integration test (100+ claims, full pipeline)
25. - [ ] Implement concurrency guard (file lock)
26. - [ ] Add CLI flags: `--dry-run`, `--phase N`, `--verbose`
27. - [ ] Write end-to-end acceptance test

---

## Acceptance Criteria

- [ ] `python -m src.consolidator --db knowledge.db` completes full 7-phase pipeline, exits 0
- [ ] L0 claims with provenance + timestamp + atomic text promote to L1
- [ ] L1 claims with >=2 independent sources are L2 candidates
- [ ] L1->L2 requires Claude Haiku validation; L2->L3 requires Claude Sonnet + human gate
- [ ] Contradictory pairs (NLI >0.7) produce Contradiction records
- [ ] Ambiguous pairs (NLI 0.4-0.7) route to Claude review
- [ ] Confidence decays exponentially per domain half-life
- [ ] Expired claims (confidence <0.1, >90d) move to archive
- [ ] Every action writes audit log entry with reason
- [ ] Full cycle at 1000 claims costs <$0.50
- [ ] `--dry-run` reports changes without modifying store
- [ ] Markdown projections regenerated after consolidation
- [ ] Cold-start (<50 claims) completes without errors

---

## Contract Link

docs/cortex/contracts/knowledge-consolidation-engine/contract-001.md
