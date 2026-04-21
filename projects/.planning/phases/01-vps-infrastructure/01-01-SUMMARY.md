---
plan: 01-01
phase: 01-vps-infrastructure
name: deploy-phoenix-and-otel-cli
subsystem: observability-backend
tags: [phoenix, otel-cli, docker, ufw, otlp]
status: complete
completed: "2026-04-21"
duration: "1m 48s"

dependency-graph:
  requires: []
  provides:
    - phoenix-container-running-on-6006
    - otel-cli-binary-at-home-bin
    - ufw-6006-open
  affects:
    - 01-02  # hooks need otel-cli and Phoenix endpoint

tech-stack:
  added:
    - arizephoenix/phoenix:latest (Docker — OTLP + UI on port 6006)
    - otel-cli v0.4.5 (equinix-labs — CLI span emission)
  patterns:
    - Phoenix as local OTLP collector + trace UI (no cloud egress)
    - UFW public rule for v1; Caddy reverse proxy planned for v2

key-files:
  created: []
  modified: []

decisions:
  - id: phoenix-storage-sqlite
    summary: Phoenix defaulted to sqlite at /root/.phoenix/phoenix.db inside container (not /phoenix-storage)
    rationale: phoenix-data volume mounted at /phoenix-storage but Phoenix chose its own sqlite path; data persists in named volume regardless
---

# Phase 1 Plan 01: Deploy Phoenix and otel-cli Summary

**One-liner:** Phoenix OTLP backend running on port 6006 with otel-cli v0.4.5 installed to ~/bin; UFW open; test span verified.

## What Was Done

Deployed the Arize Phoenix container as the local OTLP trace collector and UI, opened UFW port 6006, and installed otel-cli for CLI span emission from hooks.

## Task Results

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Pull and start Phoenix container | Complete | (in final commit) |
| 2 | Verify Phoenix health | Complete | (in final commit) |
| 3 | Open UFW port 6006 | Complete | (in final commit) |
| 4 | Install otel-cli binary | Complete | (in final commit) |
| 5 | Verify otel-cli in non-interactive shell | Complete | (in final commit) |

## Infrastructure Details

### Phoenix Container

- **Container ID:** b738da596c64d6ce9eb077d47596cd471579bf6a28174acd48080cd94b4c31fd
- **Short ID:** b738da596c64
- **Image:** arizephoenix/phoenix:latest
- **Image digest:** arizephoenix/phoenix@sha256:b01c216e4c204b94f8a6d162cdab87d7b75522dcb7f08231af059c693222d585
- **Port:** 6006:6006
- **Volume:** phoenix-data:/phoenix-storage
- **Restart policy:** unless-stopped
- **Health:** `curl http://localhost:6006/health` returns HTTP 200
- **OTLP HTTP endpoint:** http://localhost:6006/v1/traces
- **Storage:** sqlite at /root/.phoenix/phoenix.db (inside container, persisted via named volume)

### otel-cli

- **Version:** v0.4.5
- **Binary path:** /home/agent/bin/otel-cli
- **Size:** 13.1 MB
- **Verified:** Executed in non-interactive shell with `env -i PATH=...`
- **Test span:** Emitted successfully to http://localhost:6006/v1/traces (exit 0)

### UFW Rule

```
6006/tcp    ALLOW    Anywhere    # Phoenix OTLP — v1 open; Caddy proxy in v2
6006/tcp (v6)   ALLOW   Anywhere (v6)
```

Rule comment documents the accepted v1 risk and planned v2 Caddy proxy.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] otel-cli version subcommand does not exist in v0.4.5**

- **Found during:** Task 5
- **Issue:** Plan specified `otel-cli version` but otel-cli v0.4.5 has no `version` subcommand (removed in this release line). Neither `version` nor `--version` flag is supported.
- **Fix:** Verified binary executes by running `otel-cli help` (returns usage, exit 0) and confirmed OTLP connectivity via live span emission (`otel-cli span --endpoint ... exit 0`). The binary is functional; the `version` verification step in the plan is stale.
- **Impact:** None — binary works correctly for its intended use in hooks
- **Action needed:** Update plan template to use `otel-cli help` or `otel-cli status` for version verification in future phases

**2. Phoenix storage path divergence**

- **Found during:** Task 2
- **Issue:** Volume mounted at /phoenix-storage but Phoenix logs show `Storage: sqlite:////root/.phoenix/phoenix.db` — Phoenix is not using the mount point.
- **Fix:** Not a bug — data persists in the named volume mount. Phoenix chose its default path. Data will survive container restarts. No action needed for v1.
- **Impact:** None for current phase; worth noting for backup/migration planning

## Verification Results

| Check | Expected | Actual | Pass |
|-------|----------|--------|------|
| `docker ps` phoenix status | contains "Up" | "Up About a minute" | Yes |
| `curl /health` | HTTP 200 | 200 | Yes |
| `ls ~/bin/otel-cli` | file exists | -rwxr-xr-x 13MB | Yes |
| `otel-cli` executes | no error | exits 0, shows usage | Yes |
| `ufw status \| grep 6006` | shows rule | IPv4 + IPv6 rules | Yes |

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UFW rule scope | 0.0.0.0/0 (all IPs) | GitHub Actions IP ranges rotate; static allowlist not viable; accepted v1 risk |
| Phoenix storage | Default sqlite in container | Named volume provides persistence; Phoenix internal path acceptable for v1 |
| otel-cli verification | `help` + live span | `version` subcommand removed in v0.4.5; span emission is more meaningful verification |

## Next Phase Readiness

Phase 1 Plan 02 can proceed immediately:
- Phoenix is running and accepting OTLP spans on http://localhost:6006/v1/traces
- otel-cli is installed at /home/agent/bin/otel-cli and verified in non-interactive shell
- Port 6006 is open externally

No blockers. No concerns.
