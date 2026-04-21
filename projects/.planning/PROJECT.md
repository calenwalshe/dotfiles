# experiment-control-plane

## What This Is

Claude Code hook invocations, SDK calls, and eval runs currently produce no unified observability signal — there is no way to correlate tool calls across a session into a trace, no automated gate that prevents a PR from merging when LLM quality degrades, and no durable record of what prompts produced what outcomes. This project builds a self-hosted experiment control plane on the existing Vultr VPS (144.202.81.218): Phoenix (Arize) as the tracing and eval backend, OpenLLMetry as the SDK instrumentation layer, `otel-cli` as the hook-level instrumentation tool, and a pytest-based CI eval gate wired into GitHub Actions branch protection. All infrastructure runs on hardware the operator controls; no prompt or response content is exported to any third-party SaaS by default.

## Core Value

PRs that degrade LLM eval scores are blocked from merging; every Claude Code session produces correlated OTLP spans visible in Phoenix; no prompt/response content leaves the VPS by default.

## Requirements

### Active

- [ ] **REQ-001**: Phoenix container running on 144.202.81.218:6006 with health check passing
- [ ] **REQ-002**: Three Claude Code hooks (SessionStart, PostToolUse, SessionEnd) producing correlated OTLP spans
- [ ] **REQ-003**: W3C traceparent propagation via `/tmp/claude-trace-{session_id}.json` with lazy-init guard
- [ ] **REQ-004**: OpenLLMetry instrumentation with `TRACELOOP_TRACE_CONTENT=false` global default
- [ ] **REQ-005**: pytest eval runner using arize-phoenix-evals>=2 with correct choices dict form
- [ ] **REQ-006**: eval-gate.py with hybrid delta+absolute threshold logic against committed baseline
- [ ] **REQ-007**: GitHub Actions ci-evals workflow + branch protection blocking merges on eval regression

### Out of Scope

- Label promotion from dev to production (dropped — Phoenix has no label model)
- OpenTelemetry Collector as a required service
- Multi-tenant trace stores
- Langfuse, Weave, Helicone backends
- Prompt registry or prompt CMS
- Replacing /cortex-status continuity reconstruction
- PreCompact hook instrumentation
- Caddy reverse proxy for Phoenix (deferred to v2)

## Context

**Contract:** docs/cortex/contracts/experiment-control-plane/contract-001.md
**Spec:** docs/cortex/specs/experiment-control-plane/spec.md
**VPS:** 144.202.81.218 — 15 GB RAM (7.6 GB available), 300 GB disk (31 GB free), Docker installed

## Constraints

- Phoenix must run as a single Docker container (SQLite storage, no external DB)
- No prompt/response content exported to third-party SaaS by default
- All hook scripts go in `~/.claude/hooks/`; settings.json changes are additive only
- otel-cli installed to `~/bin/otel-cli` (no sudo); must work in non-interactive shell
- arize-phoenix-evals>=2 (separate package — no `[evals]` extra exists)
- choices={"label": float} dict form is mandatory on ClassificationEvaluator (list form produces NaN)
- Port 6006 open to 0.0.0.0/0 accepted for v1 (Caddy auth proxy deferred)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Phoenix over Langfuse | Langfuse requires 16–32 GB RAM (ClickHouse); VPS has 7.6 GB available | Phoenix single container |
| traceparent via /tmp file | Env vars don't persist across hook subprocess invocations | /tmp/claude-trace-{session_id}.json |
| Lazy-init in PostToolUse | SessionStart may not fire after /clear | Guard in postuse hook required |
| gpt-4o-mini eval judge | Native Phoenix support; ~$0.01/50-case run | gpt-4o-mini (haiku wrapper deferred) |
| UFW open to 0.0.0.0/0 | GitHub Actions IPs rotate; static allowlist breaks CI | Accept v1 risk; Caddy proxy in v2 |
| Hybrid delta+absolute gate | Catches regressions absolute-only misses; dominant production pattern | max_delta=0.05, min_absolute=0.75 |
| Label promotion dropped | Phoenix has no label model; Langfuse concept doesn't port | Git history is audit trail |
