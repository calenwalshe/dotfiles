# Critique: spec — server-hardening

**Gate:** spec
**Slug:** server-hardening
**Timestamp:** 2026-04-14T04:13:16Z
**Artifact:** docs/cortex/specs/server-hardening/spec.md
**Engine:** codex
**Overall Severity:** STOP

---

## Summary

The spec has a broken definition of done and at least one acceptance criterion that cannot be objectively tested. It also relies on vague mitigations where precise rollback and verification steps are required.

---

## Findings (4 total — STOP: 2, CAUTION: 2, GO: 0)

### [STOP] scope_coherence

**Finding:** The spec turns the pentest into an unbounded closure gate: any new High finding discovered during scanning must be fixed for acceptance, even if it is unrelated to the originally scoped hardening work. That destroys scope boundaries and guarantees execution churn.

**Quote from artifact:**
> This spec covers systematic closure of all gaps — Critical first — followed by a structured pentest using PTES methodology to verify the fixes hold and surface any remaining exposures.
> ...
> - [ ] Pentest report exists at `docs/findings/server-hardening-pentest-YYYYMMDD.md` with zero Critical or High findings remaining open

**Impact:** Implementation cannot reach a stable definition of done, because the final scan can pull unrelated vulnerabilities into scope and force additional work indefinitely.

---

### [STOP] ac_testability

**Finding:** The stream-health acceptance criterion is not mechanically verifiable because it never identifies the actual stream endpoint and mixes an objective check with a subjective claim about accessibility.

**Quote from artifact:**
> - [ ] `radio.calenwalshe.com` audio stream is accessible after all changes (HTTP 200 on stream endpoint)

**Impact:** Different executors can declare success against different URLs, or pass the check while the real stream is broken, making the acceptance result unreliable.

---

### [CAUTION] ac_testability

**Finding:** The port-2022 criterion is ambiguous because one branch of success is a subjective paperwork outcome rather than a measurable system state.

**Quote from artifact:**
> - [ ] Port 2022 is identified (process documented) and either closed or explicitly accepted with a comment in the findings log

**Impact:** The task can be marked complete without resolving the exposure, and reviewers cannot mechanically determine whether the residual risk was intentionally accepted under any defined rule.

---

### [CAUTION] risk_completeness

**Finding:** Several mitigations are vague operational advice instead of concrete, enforceable controls. "Schedule during lowest-traffic period" and "verify radio stream after each batch" do not define thresholds, rollback triggers, or who approves downtime.

**Quote from artifact:**
> - **Docker compose port rebind causes brief service downtime** — Mitigation: schedule during lowest-traffic period; rebind and restart one compose file at a time; verify radio stream after each batch.

**Impact:** Operators are left to improvise during a risky change window, increasing the chance of avoidable outage and inconsistent execution.

---
