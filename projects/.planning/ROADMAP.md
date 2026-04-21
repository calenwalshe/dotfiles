# Roadmap: experiment-control-plane

## Overview

Deploy Phoenix tracing + CI eval gate on the agent VPS (144.202.81.218) so that every Claude Code session produces correlated OTLP spans in Phoenix and PRs that degrade LLM eval scores are blocked from merging via GitHub Actions branch protection.

## Phases

### Phase 1: VPS Infrastructure

**Goal**: Phoenix container running and reachable on port 6006; UFW open; otel-cli installed
**Depends on**: Nothing
**Requirements**: REQ-001
**Success Criteria** (what must be TRUE):
1. `docker ps` on 144.202.81.218 shows a running `phoenix` container; `curl http://localhost:6006/health` returns HTTP 200
**Research**: Unlikely
**Plans**: 1 plan

---

### Phase 2: Hook Instrumentation

**Goal**: Three Claude Code hook scripts registered and producing correlated spans in Phoenix
**Depends on**: Phase 1: VPS Infrastructure
**Requirements**: REQ-002, REQ-003, REQ-004
**Success Criteria** (what must be TRUE):
1. A Claude Code session produces spans visible in the Phoenix UI: one root span per session (created by SessionStart hook), one child span per tool call (created by PostToolUse hook with W3C traceparent propagation)
2. `/tmp/claude-trace-{session_id}.json` is written at SessionStart, read at PostToolUse, and deleted at SessionEnd; no stale files remain after session end
3. A tool call made immediately after `/clear` still produces a span in Phoenix (lazy-init guard fires)
4. A Python script that imports `anthropic` and runs inside a skill with `TRACELOOP_TRACE_CONTENT=true` (opt-in) emits LLM spans with prompt/response content to Phoenix; the same script with `TRACELOOP_TRACE_CONTENT=false` (global default) emits spans without content
**Research**: Unlikely
**Plans**: 1 plan

---

### Phase 3: Eval Runner and Gate

**Goal**: pytest eval runner, gate script, and committed baseline operational
**Depends on**: Phase 1: VPS Infrastructure
**Requirements**: REQ-005, REQ-006
**Success Criteria** (what must be TRUE):
1. `pytest tests/evals/test_ci_gate.py` runs a `ClassificationEvaluator` with `choices={"correct": 1.0, "incorrect": 0.0}`, unwraps score dicts correctly, and asserts `scores.mean() >= threshold`
2. The eval gate script (`scripts/eval-gate.py`) reads `evals/baseline.json` and `evals/current.json`, fails with exit code 1 when a score drops more than `max_delta` below baseline or below `min_absolute`, and exits 0 when all metrics pass
3. `evals/baseline.json` is committed to the repo with the schema from the implementation dossier (metadata + scores + thresholds); thresholds initialized to `min_absolute: 0.75, max_delta: 0.05` for the first eval suite
**Research**: Unlikely
**Plans**: 1 plan

---

### Phase 4: CI Wiring and Branch Protection

**Goal**: GitHub Actions workflow running on PRs; branch protection blocking merges on eval regression
**Depends on**: Phase 3: Eval Runner and Gate
**Requirements**: REQ-007
**Success Criteria** (what must be TRUE):
1. A GitHub Actions workflow (`ci-evals.yml`) runs on PR; the job fails (blocking merge) when `eval-gate.py` exits 1; the job passes when all metrics clear thresholds
2. GitHub repository branch protection is configured with `ci-evals` as a required status check on the default branch
**Research**: Unlikely
**Plans**: 1 plan

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| Phase 1: VPS Infrastructure | 1/1 | Complete | 2026-04-21 |
| Phase 2: Hook Instrumentation | 1/1 | Complete | 2026-04-21 |
| Phase 3: Eval Runner and Gate | 1/1 | Complete | 2026-04-21 |
| Phase 4: CI Wiring and Branch Protection | 1/1 | Complete | 2026-04-21 |
