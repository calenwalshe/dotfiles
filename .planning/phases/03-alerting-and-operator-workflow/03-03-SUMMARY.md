---
phase: 03-alerting-and-operator-workflow
plan: "03"
subsystem: operator-workflow
tags: [promote-bridge, staging-queue, urllib, tools, TOOLS.md, operator-ux]

# Dependency graph
requires:
  - phase: 03-01
    provides: RED test scaffold for promote_bridge (list_staging, promote_site contracts)
provides:
  - promote_bridge.py: list and promote staging URLs via scheduler HTTP API
  - TOOLS.md Perception Staging Queue section: agent instruction for /list-staging and /promote
affects:
  - openclaw-fresh container: new tool available at /var/lib/openclaw/workspace/tools/promote_bridge.py
  - Operator workflow: no config file editing needed to promote staging URLs

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "urllib.request bridge pattern: match screenshot_agent_bridge.py exactly (no aiohttp)"
    - "promote_site fetches staging first via list_staging(), then POSTs with active=True preserving category/priority/notes"
    - "All error paths return {ok: False, error: str} — never raise to caller"

key-files:
  created:
    - openclaw-fresh/workspace/tools/promote_bridge.py
  modified:
    - openclaw-fresh/workspace/TOOLS.md

key-decisions:
  - "promote_site calls list_staging() internally (not a separate GET) to get current site fields before POST — avoids stale field assumptions"
  - "TOOLS.md force-added with git add -f (workspace/ gitignored, but tools/ has tracked precedent from Phase 1)"
  - "All error paths return JSON ok=false — never sys.exit(1) — keeps agent consumption predictable"

# Metrics
duration: 2min
completed: 2026-03-30
---

# Phase 03 Plan 03: Staging Queue Promotion Tool Summary

**promote_bridge.py implements list and promote subcommands via urllib.request against scheduler API — 6 tests pass GREEN, live smoke test confirmed from inside openclaw-fresh container**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-30T05:25:23Z
- **Completed:** 2026-03-30T05:26:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Built `promote_bridge.py` following the exact urllib.request pattern from `screenshot_agent_bridge.py`
- `list_staging()` GETs `/harness/sites?active_only=false` and filters to `active == False` entries explicitly
- `promote_site(site_key)` calls `list_staging()` internally to fetch current site fields, then POSTs back with `active=True`, preserving `category`, `priority`, `notes`
- `main()` dispatches `list` and `promote <site_key>` subcommands; unknown/missing args return JSON error, exit 0
- All 6 TDD RED tests from 03-01 turned GREEN on first implementation
- Live smoke test from inside container: `{"ok": true, "staging": [], "count": 0}` (staging empty — all sites currently active, expected)
- Added "Perception Staging Queue" section to `workspace/TOOLS.md` with list/promote command examples and UX rules

## Task Commits

Each task was committed atomically (openclaw-fresh repo):

1. **Task 1: Build promote_bridge.py (GREEN)** - `c3d59ac` (feat) — openclaw-fresh repo
2. **Task 2: Wire promote_bridge into workspace/TOOLS.md** - `0e6ec3c` (feat) — openclaw-fresh repo

## Files Created/Modified
- `openclaw-fresh/workspace/tools/promote_bridge.py` — 109-line implementation: `list_staging()`, `promote_site(site_key)`, `main()` dispatcher
- `openclaw-fresh/workspace/TOOLS.md` — 24-line "Perception Staging Queue" section added with command examples and UX rules

## Decisions Made
- `promote_site` calls `list_staging()` internally rather than a separate GET — ensures site fields are current at time of promotion; avoids duplicating the filter logic
- Force-add `workspace/TOOLS.md` with `git add -f` — workspace/ is gitignored in openclaw-fresh, but tools/ and TOOLS.md have tracked precedent from Phase 1
- All code paths return `{"ok": False, "error": str(e)}` — never raise, never exit(1) — consistent with screenshot_agent_bridge.py contract

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `workspace/TOOLS.md` required `git add -f` due to `.gitignore` rule on `workspace/` — same pattern used for `test_promote_bridge.py` in 03-01 (tracked in decisions)

## User Setup Required
None.

## Next Phase Readiness
- Phase 03 is now complete: alerting tests (03-01), alerting implementation (03-02, separate), promote_bridge (03-03)
- Operator can list staging queue and promote URLs via Telegram without editing config files
- `promote_bridge.py` is live in the container at `/var/lib/openclaw/workspace/tools/promote_bridge.py`

---
*Phase: 03-alerting-and-operator-workflow*
*Completed: 2026-03-30*

## Self-Check: PASSED

- FOUND: openclaw-fresh/workspace/tools/promote_bridge.py
- FOUND: openclaw-fresh/workspace/TOOLS.md
- FOUND: .planning/phases/03-alerting-and-operator-workflow/03-03-SUMMARY.md
- FOUND: commit c3d59ac (openclaw-fresh repo)
- FOUND: commit 0e6ec3c (openclaw-fresh repo)
