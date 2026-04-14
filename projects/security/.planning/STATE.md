---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: server-hardening
status: in-progress
stopped_at: 04-02 PTES pentest scan complete (nmap, testssl, nuclei, lynis)
last_updated: "2026-04-14T05:45:00Z"
last_activity: 2026-04-14 — Completed 04-02-PLAN.md (PTES Phases 0-2 pentest scans)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Two active critical compromise vectors are closed (SSH password brute force, Docker UFW bypass), the radio stream remains continuously available, and a PTES-structured pentest confirms all in-scope fixes hold.
**Current focus:** Phase 4 — PTES Pentest AC (all hardening plans complete)

## Current Position

Phase: 4 — PTES Pentest AC (in progress)
Plan: 04-02 complete — 2/3 phase-4 plans done
Status: In progress — next: 04-03 (findings analysis + remediation plan)
Last activity: 2026-04-14 — Completed 04-02 PTES pentest scans (nmap, testssl, nuclei, lynis)

Progress: [███████████████████████░░] 6/7 plans complete

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

## Accumulated Context

### Decisions

Bridge import from Cortex contract: docs/cortex/contracts/server-hardening/contract-001.md

**01-01 SSH Hardening (2026-04-14):**
- PasswordAuthentication disabled in `/etc/ssh/sshd_config.d/50-cloud-init.conf` (cloud-init override takes precedence)
- PermitRootLogin, X11Forwarding, GatewayPorts, LogLevel changed in `/etc/ssh/sshd_config`
- Port 2022 (etserver/EternalTerminal) is blocked by UFW default deny — no change needed
- All five sshd -T values verified: passwordauthentication no, permitrootlogin no, x11forwarding no, gatewayports no, loglevel VERBOSE

Key decisions carried forward:
- Docker port rebind to 127.0.0.1 (not DOCKER-USER iptables — ephemeral)
- fail2ban with `banaction = ufw` (not CrowdSec — RAM overhead)
- Caddy changes require `docker compose restart caddy` (inode change rule)
- Pentest AC scoped to in-spec items only (not unbounded scan findings)
- Verify SSH key auth from second terminal before disabling PasswordAuthentication

**02-01 Docker port rebinding (2026-04-14):**
- 18 internal service ports rebound from 0.0.0.0 to 127.0.0.1 in docker-compose.yml
- docker compose v2 (space syntax) required — v1 has KeyError:ContainerConfig bug with newer images
- magmalab-*, chat-frontend/backend, imagen-bridge left as-is (separate compose projects, out of scope)
- Caddy 80/443 kept as public bindings (intentional)
- Verified via ss: all services listen on 127.0.0.1 only

**02-02 sysctl hardening + UFW logging (2026-04-14):**
- ip_forward NOT set to 0 — Docker requires net.ipv4.ip_forward = 1
- docker0.rp_filter = 2 (Docker-managed) — accepted, global all.rp_filter = 1 is authoritative for non-Docker interfaces
- UFW logging upgraded from low to medium

**01-02 fail2ban + auditd (2026-04-14):**
- banaction=ufw chosen — UFW is active firewall, keeps ban state consistent
- Ports 22+2022 covered in sshd jail — matches both sshd listening ports
- auditd left with default rules — no custom rules needed for Phase 1
- fail2ban was banning live attackers (8 IPs, 47 failed attempts) by the time verification ran

**03-01 Caddy app layer hardening (2026-04-14):**
- (security_headers) snippet added — HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, -Server
- import security_headers in all 13 named vhosts; :80 skipped (redirect only)
- basicauth added to /status, /status/metrics, /costs — username: admin
- Dashboard password: `u6P4FRokt727+Bq+` (change after review)
- vnc-auth.calenwalshe.com block removed
- caddy fmt canonically restructures handles before route into route block — validated correct

### Pending Todos

- Change dashboard basicauth password from generated value (`u6P4FRokt727+Bq+`)

**04-01 Pentest tools install (2026-04-14):**
- lynis 3.0.9 installed via apt
- nuclei v3.7.1 installed via go install to ~/go/bin (GOPATH=$HOME/go)
- testssl.sh 3.3dev cloned to ~/testssl.sh (shallow clone)
- stream health confirmed: https://radio.calenwalshe.com/stream.mp3 → HTTP/2 200 audio/mpeg
- GOOGLE_API_CX warning from nuclei is benign (unrelated env var, does not affect operation)
- Stream mountpoint pending todo from 03-01 resolved: /stream.mp3 confirmed

**04-02 PTES Pentest Scans (2026-04-14):**
- nuclei template paths are full paths (~/nuclei-templates/http/cves/ etc.), not bare names
- testssl.sh grades via Cloudflare edge — TLS 1.0/1.1 is Cloudflare policy, origin Caddy enforces TLS 1.2+
- Ports 7878/8989/9696/9080 are internet-exposed (Radarr/Sonarr/Prowlarr, Python HTTP) — separate compose projects, not rebound in phase 02
- Redis has no requirepass (DBS-1884) — risk depends on bind address
- lynis hardening index: 63/100, 1 warning (vulnerable packages), 52 suggestions
- Scan outputs in /tmp/pentest/ — not versioned

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-14T05:45:00Z
Stopped at: Completed 04-02-PLAN.md (PTES pentest scans — nmap, testssl, nuclei, lynis)
Resume file: None
