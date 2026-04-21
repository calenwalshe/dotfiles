---
plan: 02-01
phase: 02-hook-instrumentation
name: write-and-register-hooks
subsystem: observability
tags: [otel, hooks, claude-code, traceparent, phoenix, openllmetry]
status: complete
completed: 2026-04-21
duration: "~12 minutes"

dependency_graph:
  requires:
    - 01-01  # Phoenix + otel-cli deployed
  provides:
    - otel-session-start.sh
    - otel-post-tool-use.sh
    - otel-session-end.sh
    - hooks registered in settings.json
    - traceloop-sdk installed
  affects:
    - 02-02  # any further hook instrumentation
    - 03-xx  # eval pipeline (sessions now emit OTLP spans)

tech_stack:
  added:
    - traceloop-sdk==0.60.0 (OpenLLMetry — installed in claude-stack-env venv)
  patterns:
    - W3C traceparent propagation via /tmp/claude-trace-{session_id}.json
    - Lazy-init guard in PostToolUse for /clear edge case
    - Async hooks to avoid blocking Claude Code execution

key_files:
  created:
    - /home/agent/.claude/hooks/otel-session-start.sh
    - /home/agent/.claude/hooks/otel-post-tool-use.sh
    - /home/agent/.claude/hooks/otel-session-end.sh
  modified:
    - /home/agent/.claude/settings.json
---

# Phase 02 Plan 01: Write and Register Claude Code Hooks — Summary

**One-liner:** Three otel hook scripts registered in settings.json; W3C traceparent propagated via /tmp files; traceloop-sdk 0.60.0 installed in claude-stack-env.

## What Was Done

Wrote and registered three Claude Code hook scripts that propagate W3C traceparent context and emit OTLP spans to Phoenix (running at localhost:6006). Installed OpenLLMetry (traceloop-sdk). All hooks registered additively in `~/.claude/settings.json` — no existing hooks removed.

## Tasks Completed

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Install traceloop-sdk | Done | Installed in claude-stack-env venv (system python3 is a venv without .local/lib on path) |
| 2 | Write SessionStart hook | Done | Generates W3C traceparent, writes /tmp/claude-trace-{session_id}.json, emits root span |
| 3 | Write PostToolUse hook | Done | Reads traceparent, emits child span per tool call, lazy-init guard present |
| 4 | Write SessionEnd hook | Done | Deletes /tmp/claude-trace-{session_id}.json |
| 5 | Make hooks executable | Done | chmod +x all three |
| 6 | Register hooks in settings.json | Done | Additive merge using nested hook group format matching existing schema |

## Verification Results

| Check | Result |
|-------|--------|
| Hook files exist and executable | PASS — all three at /home/agent/.claude/hooks/otel-*.sh |
| Hooks in settings.json | PASS — SessionStart: 7 hooks, PostToolUse: 8 hooks, SessionEnd: 5 hooks |
| SessionStart test: traceparent file written | PASS — valid W3C format (00-{32hex}-{16hex}-01) |
| PostToolUse test: span emitted | PASS — otel-cli exited 0, Phoenix returned 200 |
| Lazy-init test: recreates missing file | PASS — deleted file, ran hook, file recreated with fresh traceparent |
| SessionEnd test: file deleted | PASS — file absent after hook run |
| traceloop-sdk importable | PASS — `from traceloop.sdk import Traceloop` works in claude-stack-env |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Install traceloop-sdk into claude-stack-env venv (not system pip) | System python3 is the venv; `--break-system-packages` installs to .local/lib which is not on the venv's sys.path; venv pip ensures hooks using python3 can find the package |
| Hooks registered as `async: true` | Avoids blocking Claude Code execution; span emission latency should not affect UX |
| settings.json hook format: nested `{"hooks": [...]}` groups | Matched existing format in settings.json — plan showed flat format but actual schema uses nested groups; used the actual format |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] settings.json hook registration format mismatch**

- **Found during:** Task 6
- **Issue:** The plan's python script used flat `{"type": "command", "command": "..."}` objects in the hook arrays, but the actual settings.json uses nested `{"hooks": [{"type": "command", ...}]}` objects with an optional `matcher` field at the outer level. Using the flat format would create invalid entries.
- **Fix:** Wrote the merge script to use the nested format matching all existing hook entries.
- **Files modified:** /home/agent/.claude/settings.json

**2. [Rule 1 - Bug] traceloop-sdk not importable after `pip install --break-system-packages`**

- **Found during:** Task 1
- **Issue:** System `python3` is `/home/agent/claude-stack-env/bin/python3` (a venv). `pip install --break-system-packages` installs to `/home/agent/.local/lib/python3.12/site-packages` which is not on the venv's `sys.path`, so `import traceloop` fails.
- **Fix:** Also ran `/home/agent/claude-stack-env/bin/pip3 install traceloop-sdk` to install directly into the venv.
- **Files modified:** None (venv site-packages)

## Next Phase Readiness

- Phoenix is running and receiving spans
- All three hooks fire on their respective events
- traceloop-sdk ready for instrumentation wrappers
- No blockers for Phase 3 (eval pipeline)
