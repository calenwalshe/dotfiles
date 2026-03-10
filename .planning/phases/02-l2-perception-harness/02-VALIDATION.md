---
phase: 02
slug: l2-perception-harness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (stdlib) |
| **Config file** | none — tests run with `python -m unittest discover` |
| **Quick run command** | `cd /home/agent/agent-stack/openclaw-scheduler && python -m unittest master_harness.suites.test_l2_perception -v` |
| **Full suite command** | `cd /home/agent/agent-stack/openclaw-scheduler && python -m unittest discover -s . -p "test_*.py" -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | INFR-03 | unit | quick run | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | INFR-03 | unit | quick run | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | INFR-03 | unit | quick run | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | INFR-03 | unit | quick run | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | INFR-03 | unit | quick run | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `master_harness/suites/test_l2_perception.py` — unit tests for: `_prune_artifacts()`, `_classify_screenshot()`, `_artifact_dir()`, drift detection logic, per-URL error handling
- [ ] No framework install needed — unittest is stdlib

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Suite visible in `/harness/suites` API | INFR-03 | Requires running container | `curl localhost:9090/harness/suites \| jq '.[] \| select(.name=="l2_perception")'` |
| Hourly schedule triggers run | INFR-03 | Requires APScheduler runtime | Check scheduler logs after deploy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
