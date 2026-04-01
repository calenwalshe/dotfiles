---
subsystem: schema
tags: [agent-contracts, pydantic, typed-artifacts, role-definitions]
requires: [handoff-package-schema]
provides: [agent-contracts, agent-artifact-models]
affects: [orchestrator, uxr, pm, ds, evaluation, pressure-test, feedback-synthesis]
tech-stack: [pydantic-v2]
key-files: [docs/agent-contracts.md, src/schemas/agent_artifacts.py, tests/test_agent_contracts.py]
key-decisions:
  - "Agent artifacts reuse sub-models from handoff_package.py (Persona, Requirement, etc.)"
  - "PressureTestArtifact requires min_length=1 on objections — no rubber-stamping"
  - "Objection.target_claim has min_length=1 — must name a specific claim"
patterns-established:
  - "ArtifactMetadata shared across all agents (agent_id, phase, timestamp, run_id)"
  - "Agent artifacts map to handoff package sections via shared sub-models"
requirements-completed: [SCHEMA-02]
duration: ~5min
completed: 2026-04-01
---

## Performance

- Duration: ~5 min
- Tasks: 3/3
- Files created: 3

## Accomplishments

- `docs/agent-contracts.md` — full contracts for all 7 agents (input, output, tool access, eval rubric)
- 7 typed artifact Pydantic models sharing sub-models with HandoffPackage
- 16 contract compliance tests (valid construction + validation error paths)
- Full test suite: 26 tests passing

## Task Commits

| Task | Commit | Files |
|------|--------|-------|
| All 3 tasks | `6f2c03e` | docs/agent-contracts.md, src/schemas/agent_artifacts.py, tests/test_agent_contracts.py |

## Files Created

- `docs/agent-contracts.md` — 7 agent contracts
- `src/schemas/agent_artifacts.py` — 7 artifact models + shared metadata
- `tests/test_agent_contracts.py` — 16 tests

## Decisions Made

- Reuse HandoffPackage sub-models in agent artifacts (no duplication)
- PressureTestArtifact enforces min 1 objection at schema level
- Objection.target_claim enforces non-empty (min_length=1)

## Deviations from Plan

- Added `min_length=1` constraint on `Objection.target_claim` to enforce specificity at schema level (caught by test)
