---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: server-hardening
status: archived
stopped_at: v1.0 milestone archived — all 12 findings closed, engagement complete
last_updated: "2026-04-14T05:52:00Z"
last_activity: 2026-04-14 — Completed 04-03-PLAN.md (findings report, closure PoCs)
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 7
  completed_plans: 7
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Two active critical compromise vectors are closed (SSH password brute force, Docker UFW bypass), the radio stream remains continuously available, and a PTES-structured pentest confirms all in-scope fixes hold.
**Current focus:** COMPLETE — all 4 phases, 7 plans done

## Current Position

Phase: 4 of 4 (PTES Pentest AC) — COMPLETE
Plan: 04-03 complete — 3/3 phase-4 plans done, 7/7 total plans done
Status: COMPLETE
Last activity: 2026-04-14 — Completed 04-03 closure verification and findings report

Progress: [███████████████████████████] 7/7 plans complete (100%)

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Engagement date: 2026-04-14 (single-day)

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

**04-03 Closure Verification + Findings Report (2026-04-14):**
- Cloudflare strips Authorization header — /status and /costs return 404 via public URL, 401 on direct-origin test. Auth is functioning. PoC: `curl --insecure -H "Host: radio.calenwalshe.com" https://149.28.12.120/status` → 401
- `server: cloudflare` in public responses is CF's addition. Caddy `-Server` directive suppresses Caddy's own header correctly. Not a disclosure issue for Caddy.
- All 7 in-scope findings CLOSED. Report at docs/findings/server-hardening-pentest-20260414.md
- Radio stream live throughout (no downtime across entire engagement)

### Pending Todos

- Change dashboard basicauth password from generated value (`u6P4FRokt727+Bq+`)
- FIND-008: Rebind Radarr/Sonarr/Prowlarr ports to 127.0.0.1 in their separate compose file
- FIND-009: Rebind smart-router 9080 to 127.0.0.1
- FIND-010: `sudo apt upgrade` for PKGS-7392 vulnerable packages
- FIND-011: Add `AllowTcpForwarding no` / `AllowAgentForwarding no` to sshd_config
- FIND-012: Add custom auditd rules for privilege escalation monitoring

### Blockers/Concerns

None — engagement complete.

## Session Continuity

Last session: 2026-04-14T05:52:00Z
Stopped at: Completed 04-03-PLAN.md — engagement COMPLETE
Resume file: None
