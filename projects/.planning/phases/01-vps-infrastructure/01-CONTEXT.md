# Phase 1: VPS Infrastructure — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Deploy Phoenix container on 144.202.81.218, open UFW port 6006, and install otel-cli binary. This phase produces the running backend that all subsequent phases depend on.

</domain>

<decisions>
## Implementation Decisions

- **Phoenix image:** `arizephoenix/phoenix:latest` — single container, SQLite storage, OTLP ingestion on port 6006
- **Docker run command:** `docker run -d --name phoenix -p 6006:6006 -v phoenix-data:/phoenix-storage arizephoenix/phoenix:latest`
- **UFW:** Open port 6006 to `0.0.0.0/0` (v1 accepted risk — GitHub Actions IPs rotate, static allowlist not viable; Caddy auth proxy deferred to v2)
- **otel-cli:** Install to `~/bin/otel-cli` (no sudo); binary from github.com/equinix-labs/otel-cli releases; must verify it works in non-interactive shell

### Claude's Discretion

- Specific otel-cli release version to download
- Whether to add Phoenix to a docker-compose or run standalone (standalone preferred for simplicity)
- UFW rule syntax

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/experiment-control-plane/spec.md (§6 Dependencies, §8 Sequencing steps 1–2, §7 Risks)
- docs/cortex/specs/experiment-control-plane/gsd-handoff.md (Tasks 1–4)
- docs/cortex/contracts/experiment-control-plane/contract-001.md (Done Criteria 1–2)
- docs/cortex/research/experiment-control-plane/implementation-20260421T031706Z.md (Q1 VPS capacity)

</canonical_refs>

<specifics>
## Specific Ideas

- VPS confirmed: 15 GB RAM (7.6 GB available), 300 GB disk (31 GB free), Docker already installed
- Existing running containers: caddy (unhealthy), liquidsoap, icecast, gemma-task-runner stack — Phoenix will coexist
- Health check endpoint: `curl http://localhost:6006/health` → HTTP 200
- otel-cli PATH: hooks run in non-interactive shell — prepend `export PATH="$HOME/bin:$PATH"` in hook scripts if needed

</specifics>

<deferred>
## Deferred Ideas

- Caddy reverse proxy for Phoenix HTTPS (v2)
- OpenTelemetry Collector (optional future addition)
- UFW scoped to GitHub Actions IP ranges (not viable without automated refresh)

</deferred>

---

*Phase: 01-vps-infrastructure*
*Context gathered: 2026-04-21 via /cortex-bridge*
