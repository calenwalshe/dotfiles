# Milestone Verification: experiment-control-plane

Verified: 2026-04-20T22:00:00Z

## Summary
- Phases checked: 4
- Must-haves verified: 19/19
- Status: PASSED

---

## Phase Results

### Phase 1: VPS Infrastructure — PASS

| Check | Result |
|-------|--------|
| `docker ps --filter name=phoenix` | Up 55 minutes |
| `curl localhost:6006/health` | HTTP 200 |
| `/home/agent/bin/otel-cli` | Exists, executable (-rwxr-xr-x, 13 MB) |
| `ufw status` for port 6006 | Rule present (ALLOW Anywhere + v6), with note: "Phoenix OTLP — v1 open; Caddy proxy in v2" |

All four infrastructure checks pass. Phoenix container is live, health endpoint responding, otel-cli binary present, and UFW rule is active.

---

### Phase 2: Hook Instrumentation — PASS

| Check | Result |
|-------|--------|
| `otel-session-start.sh` exists + executable | Yes (-rwxrwxr-x, 1055 bytes) |
| `otel-post-tool-use.sh` exists + executable | Yes (-rwxrwxr-x, 1521 bytes) |
| `otel-session-end.sh` exists + executable | Yes (-rwxrwxr-x, 352 bytes) |
| Lazy-init guard in `otel-post-tool-use.sh` | Present: comment confirms "Lazy-init guard: generate traceparent if file absent (handles /clear edge case)" |
| All three hooks registered in `settings.json` | Confirmed — all three `bash /home/agent/.claude/hooks/otel-*.sh` commands present |
| `python3 -c "import traceloop; print('ok')"` | Prints `ok` — package importable |

All hook checks pass. The lazy-init guard pattern is present in otel-post-tool-use.sh, all three hooks are wired into settings.json, and traceloop-sdk is installed.

---

### Phase 3: Eval Runner and Gate — PASS

| Check | Result |
|-------|--------|
| `tests/evals/test_ci_gate.py` exists | Yes (2957 bytes) |
| `choices={"correct": 1.0, "incorrect": 0.0}` (dict form) | Confirmed on line 42 — comment explicitly notes "MUST be dict — list form silently produces NaN" |
| Score dict unwrap in test | Confirmed lines 52-54: `lambda x: x["score"] if isinstance(x, dict) else None` |
| NaN guard present | Confirmed lines 56-60: `assert scores.count() == len(eval_results)` with descriptive failure message |
| `scripts/eval-gate.py` exists | Yes (1585 bytes, executable) |
| Gate exits 1 on floor fail | Verified: score 0.70 < floor 0.75 → exit 1 |
| Gate exits 1 on delta regression | Verified: score 0.81 drops 0.06 from baseline 0.87 > max_delta 0.05 → exit 1 |
| Gate exits 0 on passing score | Verified: score 0.88 → exit 0 |
| `evals/baseline.json` committed to repo | Confirmed: `git log` shows commit 81643db "feat(03-01): eval runner, gate script, and initial baseline" |
| Baseline schema has metadata+scores+thresholds | Confirmed: all three top-level keys present; correctness=0.87, floor=0.75, max_delta=0.05 |

All eval checks pass. The NaN guard and dict-form choices fix are both implemented with explicit comments explaining the rationale.

---

### Phase 4: CI Wiring — PASS

| Check | Result |
|-------|--------|
| `.github/workflows/ci-evals.yml` exists | Yes (842 bytes) |
| Job name is exactly `ci-evals` | Confirmed: `jobs: ci-evals:` |
| Trigger is `pull_request` on `main` | Confirmed: `on: pull_request: branches: [main]` |
| Workflow runs pytest | Confirmed: `pytest tests/evals/test_ci_gate.py -v` |
| Workflow runs eval-gate | Confirmed: `python scripts/eval-gate.py` as next step after pytest |
| `evals/current.json` in `.gitignore` | Confirmed: line 2 of .gitignore, with comment "CI-generated eval artifacts — do not commit" |
| `evals/current.json` not tracked in git | Confirmed: `git ls-files evals/current.json` returns nothing |

Note on manual steps: GitHub Actions secrets (`OPENAI_API_KEY`) and repo variables (`PHOENIX_URL`) must be set in the GitHub repository settings UI — these cannot be verified from the filesystem. Branch protection rules (requiring CI pass before merge) are also a GitHub UI configuration and are not verifiable from the codebase. Both are pre-requisites for the gate to enforce on PRs; the workflow file itself is complete and correct.

---

## Gaps

None. All 19 must-have checks pass across all four phases.

---

_Verified: 2026-04-20T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
