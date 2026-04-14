---
phase: 01-hardening
plan: "01"
subsystem: infra
tags: [pm2, node, mcp, session, judge, async, process-management]

requires: []
provides:
  - Async judge pipeline: judge runs after research completes, cached in job JSON
  - pm2 process management with systemd startup for auto-restart on reboot
  - Disk-persisted session state: active project survives server restarts

affects: [future research polling, mcp-server operations, session state]

tech-stack:
  added: [pm2@6.0.14]
  patterns:
    - "Async job enrichment: child process close → setImmediate → secondary async task"
    - "Disk session persistence on module load + write-through on mutation"
    - "pm2 ecosystem.config.js as single source of truth for server start"

key-files:
  created:
    - chatgpt-mcp-test/ecosystem.config.js
    - chatgpt-mcp-test/lib/context.js
  modified:
    - chatgpt-mcp-test/lib/research.js
    - chatgpt-mcp-test/server.js

key-decisions:
  - "setImmediate for async judge: allows close handler to complete before judge runs, avoids blocking Node event loop"
  - "Legacy inline fallback in poll handler: jobs created before this change (no judge_status field) still work"
  - "SESSION_FILE lives in chatgpt-mcp-test/, not project dir — it is server state, not project state"
  - "MCP_TOKEN loaded from shell env (source ~/.api-keys) before pm2 start — ecosystem.config reads process.env"

patterns-established:
  - "Job JSON as state machine: status (running/done/failed) + judge_status (pending/running/done/failed)"
  - "Write-through session: every setActiveProject call writes SESSION_FILE synchronously"
  - "pm2 startup: always source ~/.api-keys before pm2 start/restart to propagate MCP_TOKEN"

duration: 18min
completed: 2026-04-14
---

# Phase 01 Plan 01: Hardening — Async Judge, pm2, Session Persist Summary

**Async judge caching via setImmediate post-research, pm2 systemd management, and disk-persisted session state across server restarts**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-14T02:51:22Z
- **Completed:** 2026-04-14T03:09:00Z
- **Tasks:** 3/3
- **Files modified:** 4

## Accomplishments

- cortex_research_poll never blocks on judge — reads cached mobile_report from job JSON; judge runs async after research completes
- MCP server runs under pm2 with systemd auto-startup; survives crashes and reboots without manual intervention
- Active project (chatgptmcp) survives pm2 restart — loaded from .mcp-session.json on module init

## Task Commits

Each task was committed atomically:

1. **Task 1: Async judge caching** - `f1a4a71` (feat)
2. **Task 2: pm2 process management** - `c2e225e` (feat)
3. **Task 3: Persist session state to disk** - `c4d630a` (feat)

## Files Created/Modified

- `chatgpt-mcp-test/lib/research.js` - Imports judge + cortex; runs judge async via setImmediate after research done; writes mobile_report/judge_scores/judge_error to job JSON
- `chatgpt-mcp-test/server.js` - Poll handler reads job.judge_status to return cached report; legacy inline fallback preserved for old jobs
- `chatgpt-mcp-test/ecosystem.config.js` - pm2 app config: PORT 8787, MCP_ROOT, MCP_TOKEN from env, logs to logs/, restart_delay 2000ms
- `chatgpt-mcp-test/lib/context.js` - SESSION_FILE constant; restores session on module load (session_restored/session_fresh log); setActiveProject writes SESSION_FILE; clearSession() helper added

## Decisions Made

- Used `setImmediate` instead of spawning a new process for judge — keeps judge within the Node process, shares logger/env, simpler; acceptable because judge uses execSync internally (no event loop blocking during judge itself)
- Legacy inline judge fallback kept in server.js poll handler — existing jobs with no `judge_status` field would otherwise return empty/broken results
- pm2 installed globally via npm (not saved in package.json) — it's infrastructure, not app dependency
- SESSION_FILE in chatgpt-mcp-test root (not inside jobs/) — explicit separation of server operational state vs research job state

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- pm2 startup required `sudo` to install systemd service — ran the suggested command successfully
- Server root endpoint (`/`) returns 401 without token — auth middleware applies to all routes globally. This is existing behavior, not a regression. Verified with `?token=` query param.

## Next Phase Readiness

- Server is production-hardened: no manual node server.js restarts needed
- Judge output is now decoupled from poll latency — no more 60-120s timeout risk on ChatGPT side
- Active project context persists — ChatGPT sessions resume without needing cortex_set_project

Blockers: None.

---
*Phase: 01-hardening*
*Completed: 2026-04-14*
