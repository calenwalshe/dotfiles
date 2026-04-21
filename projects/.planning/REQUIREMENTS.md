# Requirements: experiment-control-plane

**Defined:** 2026-04-21
**Core Value:** PRs that degrade LLM eval scores are blocked from merging; every Claude Code session produces correlated OTLP spans visible in Phoenix; no prompt/response content leaves the VPS by default.

## Infrastructure Requirements

- [ ] **REQ-001**: Phoenix container running on 144.202.81.218:6006 with health check passing

## Instrumentation Requirements

- [ ] **REQ-002**: Three Claude Code hooks (SessionStart, PostToolUse, SessionEnd) producing correlated OTLP spans
- [ ] **REQ-003**: W3C traceparent propagation via `/tmp/claude-trace-{session_id}.json` with lazy-init guard
- [ ] **REQ-004**: OpenLLMetry instrumentation with `TRACELOOP_TRACE_CONTENT=false` global default

## Eval Requirements

- [ ] **REQ-005**: pytest eval runner using arize-phoenix-evals>=2 with correct choices dict form
- [ ] **REQ-006**: eval-gate.py with hybrid delta+absolute threshold logic against committed baseline

## CI Requirements

- [ ] **REQ-007**: GitHub Actions ci-evals workflow + branch protection blocking merges on eval regression

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| **REQ-001** | Phase 1: VPS Infrastructure | Pending |
| **REQ-002** | Phase 2: Hook Instrumentation | Pending |
| **REQ-003** | Phase 2: Hook Instrumentation | Pending |
| **REQ-004** | Phase 2: Hook Instrumentation | Pending |
| **REQ-005** | Phase 3: Eval Runner and Gate | Pending |
| **REQ-006** | Phase 3: Eval Runner and Gate | Pending |
| **REQ-007** | Phase 4: CI Wiring and Branch Protection | Pending |

**Coverage:**
- Infrastructure requirements: 1 total — mapped
- Instrumentation requirements: 3 total — all mapped
- Eval requirements: 2 total — all mapped
- CI requirements: 1 total — mapped
- Unmapped: 0
