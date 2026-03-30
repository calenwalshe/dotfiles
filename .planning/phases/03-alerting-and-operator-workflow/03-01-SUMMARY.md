---
phase: 03-alerting-and-operator-workflow
plan: "01"
subsystem: testing
tags: [unittest, tdd, asyncpg, urllib, mock, bypass-health, promote-bridge]

# Dependency graph
requires:
  - phase: 02-l2-perception-harness
    provides: skipIf import guard pattern (test_l2_perception.py)
provides:
  - RED test scaffold for l2_perception_alerting module (_compute_bypass_health, _get_consecutive_failures_for_site, _should_alert)
  - RED test scaffold for promote_bridge module (list_staging, promote_site)
affects:
  - 03-02 (l2_perception_alerting implementation — must satisfy these test contracts)
  - 03-03 (promote_bridge implementation — must satisfy these test contracts)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "skipIf import guard: try/except ImportError on missing module + @skipIf decorator on all test classes"
    - "AsyncMock pool pattern: mock asyncpg pool.acquire() as async context manager returning fetch results"
    - "urllib mock pattern: patch promote_bridge.urllib_request.urlopen with MagicMock context manager returning JSON bytes"

key-files:
  created:
    - agent-stack/openclaw-scheduler/master_harness/suites/test_l2_perception_alerting.py
    - openclaw-fresh/workspace/tools/test_promote_bridge.py
  modified: []

key-decisions:
  - "test_l2_perception_alerting committed to agent-stack repo (feature/perception-learning-arch-smoke-20260301 branch)"
  - "test_promote_bridge force-added (-f) to openclaw-fresh repo because workspace/ is gitignored but tools/ has tracked precedent"
  - "_should_alert tests pure function in alerting module — alert trigger logic separated from async send for testability"

patterns-established:
  - "Alerting tests use AsyncMock for asyncpg pool with fetch returning list of dicts"
  - "Sparse-data suppression (< 3 challenges) tested explicitly as a distinct case from below-threshold"

requirements-completed: [INFR-02]

# Metrics
duration: 3min
completed: 2026-03-30
---

# Phase 03 Plan 01: Alerting and Operator Workflow Summary

**TDD RED scaffolds for bypass health alerting and staging promote_bridge — 19 tests total, all skipping cleanly until implementation exists**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-30T05:20:03Z
- **Completed:** 2026-03-30T05:23:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created 13-test RED scaffold for `l2_perception_alerting` covering bypass health computation, consecutive failure counting, and alert trigger logic
- Created 6-test RED scaffold for `promote_bridge` covering list_staging filtering and promote_site success/error paths
- Both test files exit 0 with all tests skipped (no unhandled ImportErrors); existing Phase 2 suite unaffected (29 tests, 0 failures)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing alerting tests (RED)** - `cb2635f` (test) — agent-stack repo
2. **Task 2: Write failing promote_bridge tests (RED)** - `09affa3` (test) — openclaw-fresh repo

**Plan metadata:** committed in final docs commit

## Files Created/Modified
- `agent-stack/openclaw-scheduler/master_harness/suites/test_l2_perception_alerting.py` — 13 tests for alerting module (_compute_bypass_health sparse suppression, _get_consecutive_failures_for_site, _should_alert)
- `openclaw-fresh/workspace/tools/test_promote_bridge.py` — 6 tests for promote_bridge (list_staging, promote_site success/not-found/active-site)

## Decisions Made
- `_should_alert` is a pure function, not a method on the alerting class — enables direct unit testing without mocking async send machinery
- `test_promote_bridge.py` force-added with `git add -f` because `workspace/` is in openclaw-fresh `.gitignore`, but `workspace/tools/` has existing tracked precedent (`test_screenshot_tool.py` was already tracked this way)
- Tests committed to their respective repos (agent-stack and openclaw-fresh), not the home repo — matching where the source modules live

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `agent-stack/` appears as untracked in the home repo at `/home/agent` — it has its own git repo. Commits were made to `agent-stack` and `openclaw-fresh` repos directly, which is the correct approach matching how Phase 2 tests were committed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 03-02 can now implement `l2_perception_alerting.py` — test contracts are locked
- 03-03 can implement `promote_bridge.py` — test contracts are locked
- Both modules have full import guards so GREEN phase implementation can be validated incrementally

---
*Phase: 03-alerting-and-operator-workflow*
*Completed: 2026-03-30*

## Self-Check: PASSED

- FOUND: agent-stack/openclaw-scheduler/master_harness/suites/test_l2_perception_alerting.py
- FOUND: openclaw-fresh/workspace/tools/test_promote_bridge.py
- FOUND: .planning/phases/03-alerting-and-operator-workflow/03-01-SUMMARY.md
- FOUND: commit cb2635f (agent-stack repo)
- FOUND: commit 09affa3 (openclaw-fresh repo)
