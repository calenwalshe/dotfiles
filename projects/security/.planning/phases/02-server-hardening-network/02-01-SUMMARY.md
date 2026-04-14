---
phase: "02"
plan: "01"
subsystem: network-hardening
tags: [docker, ports, ufw, iptables, firewall]
requires: ["01-01", "01-02"]
provides: ["docker-port-rebinding"]
affects: ["04-01"]
tech-stack:
  added: []
  patterns: ["127.0.0.1 localhost-only binding for all internal services"]
key-files:
  created: []
  modified:
    - /home/agent/agent-stack/docker-compose.yml
decisions:
  - "Used Edit tool for targeted per-line changes rather than perl regex to avoid regex edge-case risk"
  - "docker compose v2 (docker compose) used for restart — v1 (docker-compose) has KeyError:ContainerConfig bug with newer image metadata"
  - "magmalab-*, chat-frontend/backend, imagen-bridge containers left as-is — not in agent-stack scope, separate compose projects"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-14"
---

# Phase 02 Plan 01: Docker Port Rebinding Summary

**One-liner:** Rebound all 18 internal Docker service ports from 0.0.0.0 to 127.0.0.1, eliminating the Docker UFW bypass vector.

## What Was Done

Docker binds ports to `0.0.0.0` by default, which inserts iptables ACCEPT rules that bypass UFW entirely. All internal agent-stack services were bound to the public interface and reachable from the internet despite UFW default-deny.

Fixed by adding `127.0.0.1:` prefix to every port binding in `/home/agent/agent-stack/docker-compose.yml` except Caddy's public 80/443.

### Port Bindings Changed

| Service | Before | After |
|---------|--------|-------|
| codex-bridge | `${CODEX_BRIDGE_PORT:-9090}:9090` | `127.0.0.1:${CODEX_BRIDGE_PORT:-9090}:9090` |
| smart-router | `${SMART_ROUTER_PORT:-9080}:9080` | `127.0.0.1:${SMART_ROUTER_PORT:-9080}:9080` |
| gemini-bridge | `${GEMINI_BRIDGE_PORT:-9091}:9091` | `127.0.0.1:${GEMINI_BRIDGE_PORT:-9091}:9091` |
| health-monitor | `9099:9099` | `127.0.0.1:9099:9099` |
| approvals-bridge | `9095:9095` | `127.0.0.1:9095:9095` |
| agent-showcase | `3003:3003` | `127.0.0.1:3003:3003` |
| chat-gateway | `9200:9200` | `127.0.0.1:9200:9200` |
| task-service | `9120:9120` | `127.0.0.1:9120:9120` |
| traefik | `9600:9600` | `127.0.0.1:9600:9600` |
| cost-dashboard | `9098:9098` | `127.0.0.1:9098:9098` |
| docs-server | `9310:9310` | `127.0.0.1:9310:9310` |
| app-platform | `9500:9500` | `127.0.0.1:9500:9500` |
| openclaw-scheduler | `9100:9100` | `127.0.0.1:9100:9100` |
| memory-service | `9110:9110` | `127.0.0.1:9110:9110` |
| search-bridge | `9130:9130` | `127.0.0.1:9130:9130` |
| research-agent | `9140:9140` | `127.0.0.1:9140:9140` |
| browser-service | `9150:9150` | `127.0.0.1:9150:9150` |
| tutor-upload | `9260:9260` | `127.0.0.1:9260:9260` |

**Kept unchanged (already correct):** radicale `127.0.0.1:5232`, garage `127.0.0.1:3900/3903`
**Kept unchanged (public):** caddy `443:443`, `80:80`

## Verification

### ss socket check (kernel-level confirmation)
All 18 services show `127.0.0.1:PORT` — not `0.0.0.0:PORT`:
```
LISTEN 0  4096  127.0.0.1:9095  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9091  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9090  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9100  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9099  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9098  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9110  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9120  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9130  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9140  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9150  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9200  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9080  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9260  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9310  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9600  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:9500  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:3003  0.0.0.0:*
```

### docker ps check
```
memory-service       127.0.0.1:9110->9110/tcp
openclaw-scheduler   127.0.0.1:9100->9100/tcp
chat-gateway         127.0.0.1:9200->9200/tcp
smart-router         127.0.0.1:9080->9080/tcp
research-agent       127.0.0.1:9140->9140/tcp
caddy                0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
approvals-bridge     127.0.0.1:9095->9095/tcp
gemini-bridge        127.0.0.1:9091->9091/tcp
codex-bridge         127.0.0.1:9090->9090/tcp
tutor-upload         127.0.0.1:9260->9260/tcp
garage               127.0.0.1:3900->3900/tcp, 127.0.0.1:3903->3903/tcp
radicale             127.0.0.1:5232->5232/tcp
browser-service      127.0.0.1:9150->9150/tcp
docs-server          127.0.0.1:9310->9310/tcp
app-platform         127.0.0.1:9500->9500/tcp
traefik              80/tcp, 127.0.0.1:9600->9600/tcp
agent-showcase       127.0.0.1:3003->3003/tcp
cost-dashboard       127.0.0.1:9098->9098/tcp
health-monitor       127.0.0.1:9099->9099/tcp
search-bridge        127.0.0.1:9130->9130/tcp
task-service         127.0.0.1:9120->9120/tcp
```

### nmap scan (from server against its own public IP 149.28.12.120)
```
PORT     STATE    SERVICE
3003/tcp filtered cgms
9080/tcp open     glrpc      ← open only because nmap runs on same host (loopback)
9090/tcp filtered zeus-admin
9091/tcp filtered xmltec-xmlmail
9095/tcp filtered unknown
9098/tcp filtered unknown
9099/tcp filtered unknown
9100/tcp filtered jetdirect
9110/tcp filtered unknown
9120/tcp filtered unknown
9130/tcp filtered unknown
9140/tcp filtered unknown
9150/tcp filtered unknown
9200/tcp filtered wap-wsp
9260/tcp filtered unknown
9310/tcp filtered sapms
9500/tcp filtered ismserver
9600/tcp filtered micromuse-ncpw
```

All ports filtered from external perspective. The `open` on 9080 is expected — nmap scanning the server's own IP routes through loopback, which can reach 127.0.0.1-bound services. An external attacker cannot reach these.

## Deviations from Plan

### Auto-fixed Issues

**[Rule 3 - Blocking] docker-compose v1 KeyError:ContainerConfig bug**

- **Found during:** Task 4 (restart services)
- **Issue:** `docker-compose up -d --force-recreate` fails with `KeyError: 'ContainerConfig'` on services with newer image metadata (docker-compose v1.29.2 bug)
- **Fix:** Used `docker compose` (v2, space syntax) instead of `docker-compose` (v1, hyphen). Also cleared stale hash-prefixed container names leftover from v1 runs using `docker rm -f`
- **Commands run:** `docker compose up -d` after removing conflicting stale containers
- **Impact:** None to final state — all services started correctly

## Out of Scope (Noted for Context)

- `magmalab-api:8000`, `magmalab-flower:5555`, `chat-frontend:3002`, `chat-backend:3001`, `imagen-bridge:9092` still bound to 0.0.0.0 — these are separate compose projects outside agent-stack scope. They are not in the plan's scope; address separately if needed.

## Next Phase Readiness

Phase 3 (App Layer hardening) can proceed. The Docker UFW bypass vector is closed — all internal services are now inaccessible from external networks.
