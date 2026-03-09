# GSD Retrospective

## Milestone: v1.2 — Parallel Execution & Agent Specialization

**Shipped:** 2026-03-09
**Phases:** 6 (9-14) | **Plans:** 18 | **Commits:** 30

### What Was Built
- Verify-work integration with UAT workflow, templates, phase-scoped issues
- Parallel phase execution with wave-based orchestration and agent spawning
- Parallel-aware planning with vertical slices, frontmatter markers, file ownership
- Changelog foundation and /gsd:whats-new for version discovery
- gsd-debugger agent (990 lines) — scientific method, hypothesis testing, 7+ investigation techniques
- gsd-researcher agent (902 lines) — 4 research modes, Context7 > Official > WebSearch hierarchy

### What Worked
- **Thin orchestrator pattern**: Commands stay <200 lines, expertise lives in agents. Massive context reduction (2,400 → 150 lines loaded per invocation).
- **Parallel execution**: 3 agents completing independent work simultaneously proved reliable with no merge conflicts on file-disjoint plans.
- **Wave-based dependency resolution**: Simple but effective — group plans by wave number from frontmatter, execute waves sequentially, plans within waves in parallel.
- **Agent spot-checking**: Verifying SUMMARY.md existence and git commits after agent completion catches false failures (classifyHandoffIfNeeded bug).

### What Was Inefficient
- Phase 12-02 (publish command update) skipped — not blocking but creates a gap in the changelog pipeline.
- Some summaries lack one_liner fields, making automated extraction unreliable.
- Duplicate phase 14 directories (14-dedicated-researcher-agent and 14-researcher-agent) — artifact of planning iteration.

### Patterns Established
- **Agent specialization**: Domain expertise baked into agent files, commands become thin orchestrators
- **Frontmatter-driven parallelization**: `wave`, `depends_on`, `files_exclusive` in PLAN.md frontmatter
- **Source hierarchy for research**: Context7 > Official docs > WebSearch to prevent hallucination

### Key Lessons
- Consolidating expertise into agents pays off immediately — every invocation loads less context
- Parallel execution works when file ownership is explicit and non-overlapping
- The verification step (gsd-verifier) catches real gaps — worth the extra agent spawn

### Cost Observations
- Model mix: Orchestrator on opus, executors/verifiers on sonnet
- Average plan execution: 3-4 min (sonnet), verification: ~1 min (sonnet)
- Parallel waves save ~50% wall-clock time vs sequential

---

## Cross-Milestone Trends

| Metric | v1.2 |
|--------|------|
| Phases | 6 |
| Plans | 18 |
| Avg plan duration | 3.5 min |
| Total wall-clock | ~115 min |
| Known gaps | 1 (12-02) |
