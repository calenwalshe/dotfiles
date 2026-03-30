---
phase: 03
slug: alerting-and-operator-workflow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (stdlib) |
| **Config file** | none — tests run with `python -m unittest discover` |
| **Quick run command** | `python -m unittest master_harness.suites.test_l2_perception_alerting -v` |
| **Full suite command** | `python -m unittest discover -s . -p "test_*.py" -v` |
| **Estimated runtime** | ~5 seconds |

*(Run from `/home/agent/agent-stack/openclaw-scheduler/`)*

---

## Sampling Rate

- **After every task commit:** Run `python -m unittest master_harness.suites.test_l2_perception_alerting -v`
- **After every plan wave:** Run `python -m unittest discover -s . -p "test_*.py" -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | INFR-02 | unit | `python -m unittest master_harness.suites.test_l2_perception_alerting -v` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | SC-3 | unit | `python -m unittest tests.test_promote_bridge -v` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | INFR-02 | unit | `python -m unittest master_harness.suites.test_l2_perception_alerting -v` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | SC-1 | unit | `python -m unittest master_harness.suites.test_l2_perception_alerting -v` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | SC-3 | unit | `python -m unittest tests.test_promote_bridge -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `master_harness/suites/test_l2_perception_alerting.py` — stubs for `_compute_bypass_health()`, `_send_failure_alert()` trigger logic, `_get_consecutive_failures_for_site()`, sparse-data suppression (INFR-02, SC-1)
- [ ] `openclaw-fresh/workspace/tools/tests/test_promote_bridge.py` — stubs for `list_staging()`, `promote_site()` with mock urllib responses (SC-3)

*No framework install needed — unittest is stdlib in both environments.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram alert actually delivered to operator chat | SC-1 | Requires live Telegram bot token + chat ID | Trigger a site failure via test entry in site_test_scores; confirm message received in Telegram within 60s |
| `/promote <site_key>` command accepted by openclaw-fresh agent | SC-3 | Requires live bot + TOOLS.md wiring | Send `/promote test-site` from operator Telegram; confirm staging entry moves to active |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
