---
phase: 02-l2-perception-harness
plan: "01"
subsystem: testing
tags: [perception, classifier, browser-service, cf-bypass, asyncpg, aiohttp, artifact-storage, tdd]

# Dependency graph
requires:
  - phase: 01-l1-screenshot-actor
    provides: _classify_screenshot 5-class taxonomy and browser-service HTTP call patterns

provides:
  - l2_perception.py harness suite with @suite decorator
  - Pure functions: _prune_artifacts, _classify_screenshot, _artifact_dir, _detect_drift, _build_error_result
  - test_l2_perception.py with 16 unit tests covering all pure functions
  - config.yaml l2_perception entry with hourly schedule

affects: [03-alerting, any phase consuming site_test_scores, any phase consuming harness artifacts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - asyncpg deferred import inside run() to keep module importable without Docker env
    - TDD with import guard: skipIf(_MODULE_MISSING) allows test file to load in all states
    - Pure functions separated from async DB/network code for testability
    - Global semaphore for CF bypass concurrency control
    - Skip-and-continue error handling: per-site RuntimeError produces failed TestResult, not a crash

key-files:
  created:
    - agent-stack/openclaw-scheduler/master_harness/suites/l2_perception.py
    - agent-stack/openclaw-scheduler/master_harness/suites/test_l2_perception.py
  modified:
    - agent-stack/openclaw-scheduler/config.yaml

key-decisions:
  - "asyncpg deferred to inside run() — keeps pure functions locally importable without Docker env, enables TDD on local machine"
  - "Import guard in test file uses skipIf(ImportError) rather than crashing — handles both RED phase and missing-dep scenarios"
  - "Classifier adapted from screenshot_tool.py with title-based SOFT_BLOCK detection and text-length BLANK_PAGE heuristic — no LLM fallback (no API keys in scheduler)"

patterns-established:
  - "Deferred heavy imports (asyncpg) inside async entry points to keep pure functions testable without full Docker stack"
  - "skipIf import guard pattern for suites that depend on Docker-only modules"

requirements-completed: [INFR-03]

# Metrics
duration: 4min
completed: "2026-03-30"
---

# Phase 2 Plan 1: L2 Perception Harness Suite Summary

**Autonomous hourly catalog scanner: captures screenshots via browser-service, classifies using rule-based 5-class taxonomy, writes PNG+JSON artifacts, records drift-aware scores to site_test_scores, prunes old artifacts at run start**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-30T04:54:26Z
- **Completed:** 2026-03-30T04:58:30Z
- **Tasks:** 3 (TDD: RED + GREEN + config)
- **Files modified:** 3

## Accomplishments
- Built complete l2_perception harness suite with 360 lines covering all plan behaviors
- 16 unit tests covering all pure functions — all green
- asyncpg deferred import pattern enables local TDD without Docker env

## Task Commits

Each task was committed atomically (in agent-stack git repo):

1. **Task 1: Write unit tests (RED phase)** - `e1bafe4` (test)
2. **Task 2: Build l2_perception.py (GREEN phase)** - `a61daed` (feat)
3. **Task 3: Add config.yaml entry** - `54ccb70` (chore)

## Files Created/Modified
- `agent-stack/openclaw-scheduler/master_harness/suites/l2_perception.py` — @suite decorated suite with all pure functions and async run()
- `agent-stack/openclaw-scheduler/master_harness/suites/test_l2_perception.py` — 16 unit tests with import guard
- `agent-stack/openclaw-scheduler/config.yaml` — l2_perception suite entry under harness.suites

## Decisions Made
- asyncpg deferred to inside `run()` so pure functions remain importable without Docker env. This is the correct pattern for all harness suites that depend on in-container-only packages.
- Import guard in tests uses `skipIf(ImportError)` rather than `skipIf(not exists)`. This handles both RED phase (module absent) and missing-dependency scenarios identically.
- Classifier adapted from screenshot_tool.py but uses `page_text` instead of `blocker` dict + `screenshot_b64`. The scheduler's browser-service response includes text/title directly, not the blocker struct used in the L1 actor.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Deferred asyncpg import to enable local TDD**
- **Found during:** Task 2 (l2_perception.py implementation)
- **Issue:** `import asyncpg` at module level fails in local Python env (asyncpg only available in Docker). All 16 tests stayed in skip state with `_MODULE_MISSING=True`.
- **Fix:** Moved `import asyncpg` inside `run()` function with a comment explaining the deferral. Pure functions (_prune_artifacts, _classify_screenshot, etc.) remain at module level with no asyncpg dependency.
- **Files modified:** master_harness/suites/l2_perception.py
- **Verification:** `python -c "from master_harness.suites.l2_perception import _prune_artifacts..."` succeeds; all 16 tests pass GREEN.
- **Committed in:** a61daed (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Fix required for TDD to function. No scope change. Deferred import is correct for Docker-only dependencies.

## Issues Encountered
None beyond the asyncpg deferred-import deviation above.

## Next Phase Readiness
- l2_perception suite is registered and will be auto-discovered by the harness runner at startup
- config.yaml entry enables hourly execution once deployed to scheduler container
- site_test_scores table will populate on first run, giving Phase 3 alerting real data to consume
- Artifact filesystem at /var/lib/openclaw/workspace/harness-artifacts/l2_perception/ will populate per-run

---
*Phase: 02-l2-perception-harness*
*Completed: 2026-03-30*
