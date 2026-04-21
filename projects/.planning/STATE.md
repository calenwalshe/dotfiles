---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: experiment-control-plane
status: in_progress
stopped_at: "02-01 complete"
last_updated: "2026-04-21T04:17:00Z"
last_activity: 2026-04-21 — Completed 02-01-PLAN.md (otel hooks + traceloop-sdk)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 2
  completed_plans: 2
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** PRs that degrade LLM eval scores are blocked from merging; every Claude Code session produces correlated OTLP spans visible in Phoenix; no prompt/response content leaves the VPS by default.
**Current focus:** Phase 1 — VPS Infrastructure

## Current Position

Phase: 2 — Hook Instrumentation
Plan: 02-01 complete (1 of N in phase)
Status: In progress
Last activity: 2026-04-21 — Completed 02-01 (otel hooks + traceloop-sdk installed)

Progress: [██░░░░░░░░░░░░░░░░░░░] 2/2 plans done; 0/4 phases complete

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

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-21T04:17:00Z
Stopped at: Completed 02-01-PLAN.md
Resume file: None
