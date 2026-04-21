---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: experiment-control-plane
status: in_progress
stopped_at: "03-01 complete"
last_updated: "2026-04-21T04:35:00Z"
last_activity: 2026-04-21 — Completed 03-01-PLAN.md (eval runner, gate script, baseline.json)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 3
  completed_plans: 3
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** PRs that degrade LLM eval scores are blocked from merging; every Claude Code session produces correlated OTLP spans visible in Phoenix; no prompt/response content leaves the VPS by default.
**Current focus:** Phase 3 — Eval Runner and Gate

## Current Position

Phase: 3 — Eval Runner and Gate
Plan: 03-01 complete (1 of 1 in phase)
Status: In progress
Last activity: 2026-04-21 — Completed 03-01 (eval runner, gate script, baseline.json)

Progress: [███░░░░░░░░░░░░░░░░░░] 3/3 plans done; 0/4 phases complete

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

## Accumulated Context

### Decisions

Bridge import from Cortex contract: docs/cortex/contracts/experiment-control-plane/contract-001.md

**01-01 decisions:**
- Phoenix storage: Default sqlite at /root/.phoenix/phoenix.db (not /phoenix-storage mount); named volume provides persistence; acceptable for v1
- otel-cli v0.4.5 `version` subcommand removed; verify with `help` + live span instead
- UFW 6006 open to 0.0.0.0/0 (accepted v1 risk — GitHub Actions IP ranges rotate)

Key decisions carried forward:
- Phoenix over Langfuse (RAM constraint)
- traceparent via /tmp file (subprocess isolation)
- Lazy-init guard in PostToolUse (handles /clear edge case)
- gpt-4o-mini eval judge (native Phoenix support)
- UFW open to 0.0.0.0/0 v1 accepted risk
- choices={"label": float} dict form mandatory (list form → NaN)

**02-01 decisions:**
- traceloop-sdk installed into claude-stack-env venv (system python3 IS the venv; .local/lib not on venv sys.path)
- Hooks registered as async: true to avoid blocking Claude Code execution
- settings.json hook format: nested {"hooks": [...]} groups (not flat) — matched existing schema

**03-01 decisions:**
- arize-phoenix-evals installed into claude-stack-env venv via pip3 (same pattern as 02-01; .local/lib not on venv sys.path)
- asyncio.run() over pytest-asyncio for async eval runner (simpler, no extra dependency)
- NaN guard assertion (scores.count() == len(df)) added before mean check — catches silent regression if choices format changes to list
- evals/current.json is CI-generated artifact (not committed); baseline.json is committed and changes via PR

### Pending Todos

- Add evals/current.json to .gitignore (CI-generated, should not be committed)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-21T04:35:00Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
