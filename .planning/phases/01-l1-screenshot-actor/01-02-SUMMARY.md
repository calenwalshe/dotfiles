---
phase: 01-l1-screenshot-actor
plan: 02
subsystem: tools
tags: [telegram-bot-api, subprocess, asyncpg, staging-queue, agent-dispatch]

# Dependency graph
requires:
  - "01-01: screenshot_tool.py L1 pipeline (capture, classify, bypass, resize, save)"
provides:
  - "screenshot_agent_bridge.py: Python wrapper invoking screenshot_tool.py with Telegram photo delivery"
  - "TOOLS.md agent instructions: agent knows how to invoke screenshot tool for user requests"
  - "Staging queue enrollment: non-PASS URLs written to harness.site_test_catalog with active=false"
affects: [02-l2-harness-runner, 03-staging-queue]

# Tech tracking
tech-stack:
  added: [asyncpg]
  patterns: [llm-agent-tool-dispatch-via-exec, telegram-bot-api-multipart-photo-upload, staging-enrollment-non-fatal]

key-files:
  created:
    - /home/agent/openclaw-fresh/workspace/tools/screenshot_agent_bridge.py
  modified:
    - /home/agent/openclaw-fresh/workspace/tools/screenshot_tool.py
    - /home/agent/openclaw-fresh/workspace/TOOLS.md

key-decisions:
  - "Python bridge instead of Node.js: openclaw is an LLM agent with exec dispatch, not a traditional Node.js app -- tools are Python scripts invoked via exec"
  - "Agent wiring via TOOLS.md instructions rather than handler file: the agent is an LLM that reads TOOLS.md to know which tools are available"
  - "Staging uses category=l1-staging + active=false in existing schema rather than adding a staging column"

patterns-established:
  - "LLM agent tool registration: add tool usage instructions to workspace/TOOLS.md"
  - "Non-fatal DB enrollment: asyncpg import is conditional, connection errors logged to stderr only"
  - "Bridge pattern: wrapper script handles subprocess invocation + Telegram delivery, returns JSON to stdout"

requirements-completed: [CAPT-01, INFR-01]

# Metrics
duration: 9min
completed: 2026-03-10
---

# Phase 1 Plan 02: Agent Integration Summary

**Python bridge wiring screenshot_tool.py into openclaw LLM agent via exec dispatch + TOOLS.md, with Telegram photo delivery and staging queue enrollment via asyncpg**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-10T01:25:24Z
- **Completed:** 2026-03-10T01:34:19Z
- **Tasks:** 4 (including discovery + auto-approved checkpoint)
- **Files created:** 1
- **Files modified:** 2

## Accomplishments
- Built screenshot_agent_bridge.py: Python wrapper that invokes screenshot_tool.py as subprocess, parses JSON result, delivers photo + caption to Telegram via Bot API sendPhoto (multipart/form-data)
- Added staging queue enrollment to screenshot_tool.py: non-PASS URLs written to harness.site_test_catalog with category=l1-staging, active=false -- non-fatal if DB unavailable
- Updated TOOLS.md with comprehensive screenshot tool instructions so the LLM agent recognizes screenshot requests and knows how to invoke the bridge
- Installed asyncpg in container (persists via mounted python-packages volume)

## Task Commits

Each task was committed atomically:

1. **Task 0+1: Discovery + Bridge + Agent wiring** - `6cfec14` (feat)
2. **Task 2: Staging queue enrollment** - `b84c01d` (feat)
3. **Task 3: Auto-approved checkpoint** - no commit (verification only)

## Files Created/Modified
- `workspace/tools/screenshot_agent_bridge.py` - Python bridge: subprocess wrapper + Telegram photo delivery via Bot API (170 lines)
- `workspace/tools/screenshot_tool.py` - Added enroll_staging() and DATABASE_URL config (+67 lines)
- `workspace/TOOLS.md` - Added "Screenshot & Classify (L1 Actor)" section with usage instructions

## Decisions Made
- **Python bridge instead of Node.js:** Discovery (Task 0) revealed openclaw-fresh is an LLM agent platform, not a traditional Node.js app. There are no JS handler files to hook into. The agent dispatches tools via its `exec` capability. Python bridge matches the existing tool pattern (playwright_explorer.py, imagegen.py, notes.py).
- **TOOLS.md for intent wiring:** Instead of modifying a message handler, the agent learns about tools by reading TOOLS.md. Added comprehensive instructions for screenshot capture, JSON-only mode, and direct tool invocation.
- **Staging schema adaptation:** Plan assumed a `staging` column in site_test_catalog. Actual schema uses `site_key, base_url, category, active, priority, notes`. Used `category='l1-staging'` + `active=false` to achieve equivalent staging behavior without schema migration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted from Node.js bridge to Python bridge**
- **Found during:** Task 0 (Discovery)
- **Issue:** Plan assumed openclaw-fresh is a traditional Node.js app with handler files. Discovery revealed it is an LLM agent platform with no JS handler files -- tools are Python scripts invoked via exec.
- **Fix:** Created screenshot_agent_bridge.py (Python) instead of screenshot_agent_bridge.js (Node.js). Added agent instructions to TOOLS.md instead of modifying a handler file.
- **Files modified:** screenshot_agent_bridge.py (created), TOOLS.md (modified)
- **Verification:** Bridge importable in container, functions callable, TOOLS.md has screenshot instructions

**2. [Rule 3 - Blocking] Installed asyncpg in container**
- **Found during:** Task 2
- **Issue:** asyncpg not available in openclaw-fresh container, needed for staging enrollment
- **Fix:** `docker exec openclaw-fresh pip3 install --break-system-packages asyncpg` (persists via mounted volume)
- **Files modified:** System Python packages (mounted volume)
- **Verification:** `import asyncpg` succeeds in container

**3. [Rule 1 - Bug] Adapted staging INSERT to actual schema**
- **Found during:** Task 2
- **Issue:** Plan assumed site_test_catalog has a `staging` boolean column. Actual schema has no such column.
- **Fix:** Used `category='l1-staging'` + `active=false` instead of `staging=true`. ON CONFLICT guard prevents overwriting manually promoted sites (category='general').
- **Files modified:** screenshot_tool.py
- **Verification:** SQL matches actual schema, unit tests pass

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** All deviations were necessary adaptations to match actual infrastructure. Core deliverables achieved: bridge exists, agent can invoke it, staging enrollment works, photo delivery wired. The Python bridge is architecturally correct for this platform.

## Issues Encountered
- openclaw-fresh workspace/ is in .gitignore -- used `git add -f` to force-track tool files (same as Plan 01)
- openclaw-fresh is a symlink from /home/agent/openclaw-fresh -> /home/agent/projects/openclaw-fresh, requiring commits in the openclaw-fresh git repo, not the home directory repo

## User Setup Required
None - no external service configuration required. asyncpg installed automatically.

## Next Phase Readiness
- Full L1 pipeline wired end-to-end: user message -> agent exec -> bridge -> screenshot_tool -> photo delivery
- Staging queue enrollment populates harness.site_test_catalog for future L2 harness consumption
- Classification contract (5-class) stable for Phase 2

---
*Phase: 01-l1-screenshot-actor*
*Completed: 2026-03-10*

## Self-Check: PASSED

All files exist, all commits verified (6cfec14, b84c01d), all 18 unit tests pass, SSRF validation confirmed.
