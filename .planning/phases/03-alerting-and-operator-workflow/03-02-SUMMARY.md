---
phase: 03-alerting-and-operator-workflow
plan: "02"
subsystem: alerting
tags: [tdd, telegram, asyncpg, bypass-health, drift-detection, notifier]

# Dependency graph
requires:
  - phase: 03-alerting-and-operator-workflow
    plan: "01"
    provides: RED test scaffold for l2_perception_alerting (13 tests)
  - phase: 02-l2-perception-harness
    provides: l2_perception.py with drift detection, site_test_scores schema
provides:
  - l2_perception_alerting.py: _should_alert, _get_consecutive_failures_for_site, _compute_bypass_health, _send_failure_alert, _send_bypass_digest
  - l2_perception.py: alerting wired at both integration points (per-URL and post-run)
  - config.yaml: failure_alert_threshold, bypass_health_threshold, send_bypass_digest params
affects:
  - INFR-02 (bypass health tracking implemented)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "html.escape() applied to all URL/site_key content in Telegram messages"
    - "Sparse suppression pattern: below_threshold only when total_challenged >= 3"
    - "Alert gate pattern: consecutive >= threshold before firing, prevents noise from single-run blips"
    - "Non-fatal alert pattern: all alert calls wrapped in try/except with log.warning, never crash run()"

key-files:
  created:
    - agent-stack/openclaw-scheduler/master_harness/suites/l2_perception_alerting.py
  modified:
    - agent-stack/openclaw-scheduler/master_harness/suites/l2_perception.py
    - agent-stack/openclaw-scheduler/config.yaml

key-decisions:
  - "Bypass digest fires once per run (outside per-site loop) — not per-site, avoids digest spam"
  - "failure_alert_threshold=2 default: single-failure blips suppressed, two consecutive failures trigger alert"
  - "send_bypass_digest=true by default: operators see health every run without opt-in"

requirements-completed: [INFR-02]

# Metrics
duration: 2min
completed: 2026-03-30
---

# Phase 03 Plan 02: Alerting and Operator Workflow Summary

**Alerting module implemented GREEN: per-URL drift alerts and per-run bypass health digest wired into l2_perception lifecycle**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-30T05:25:29Z
- **Completed:** 2026-03-30T05:27:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `l2_perception_alerting.py` with all 5 required exports — all 13 RED tests turned GREEN
- Wired failure alert hook into `l2_perception.run()` after drift detection (per-site, only PASS_CONTENT→failing transitions, consecutive >= threshold)
- Wired bypass health digest hook into `l2_perception.run()` after URL loop (once per run, inside outer try, before pool close)
- Added 3 new config params to `config.yaml` under `l2_perception.params`
- Full scheduler suite: 29 tests, 0 failures (16 Phase 2 + 13 alerting)

## Task Commits

Each task committed atomically (agent-stack repo):

1. **Task 1: Build l2_perception_alerting.py (GREEN)** — `fbe5b22`
2. **Task 2: Wire alerting into l2_perception.py and update config.yaml** — `108f21e`

## Files Created/Modified

- `agent-stack/openclaw-scheduler/master_harness/suites/l2_perception_alerting.py` — new module (174 lines): _should_alert, _get_consecutive_failures_for_site, _compute_bypass_health, _send_failure_alert, _send_bypass_digest
- `agent-stack/openclaw-scheduler/master_harness/suites/l2_perception.py` — 3 insertion points wired: import, param extraction, failure alert block, bypass digest block
- `agent-stack/openclaw-scheduler/config.yaml` — added failure_alert_threshold: 2, bypass_health_threshold: 0.5, send_bypass_digest: true

## Decisions Made

- Bypass digest placed outside the per-site loop (fires once per run) to avoid sending N digests for N sites
- Default `failure_alert_threshold: 2` suppresses single-run blips; alert fires when site has failed consecutively
- Both alert senders are non-fatal — wrapped in try/except/log.warning so a Telegram outage never kills a harness run

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- FOUND: agent-stack/openclaw-scheduler/master_harness/suites/l2_perception_alerting.py
- FOUND: alert wiring in l2_perception.py (failure alert + bypass digest)
- FOUND: config.yaml contains failure_alert_threshold, bypass_health_threshold, send_bypass_digest
- FOUND: commit fbe5b22 (agent-stack repo)
- FOUND: commit 108f21e (agent-stack repo)
- FOUND: 29 tests, 0 failures (full scheduler suite)
