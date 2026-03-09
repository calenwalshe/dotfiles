# Milestones

## v1.2 Parallel Execution & Agent Specialization (Shipped: 2026-03-09)

**Phases completed:** 6 phases (9-14), 18 plans, 30 commits
**Timeline:** 2026-03-03 → 2026-03-09 (7 days)

**Key accomplishments:**
- Integrated /gsd:verify-work with UAT workflow, templates, and phase-scoped issues
- Built parallel phase execution — wave-based orchestration with independent agent spawning
- Created parallel-aware planning — vertical slices, frontmatter markers, file ownership
- Added changelog and /gsd:whats-new for version discovery
- Created gsd-debugger agent (990 lines) with thin orchestrator pattern (149 lines)
- Created gsd-researcher agent (902 lines) with 4 research modes and parallel project research

**Known Gaps:**
- 12-02: Publish command update (changelog generation in publish workflow) — deferred to next milestone

---

