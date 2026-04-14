---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: server-hardening
status: in-progress
stopped_at: 02-02 sysctl hardening + UFW logging complete
last_updated: "2026-04-14T04:52:57Z"
last_activity: 2026-04-14 — Completed 02-02-PLAN.md (sysctl hardening + UFW logging)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 4
  completed_plans: 3
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Two active critical compromise vectors are closed (SSH password brute force, Docker UFW bypass), the radio stream remains continuously available, and a PTES-structured pentest confirms all in-scope fixes hold.
**Current focus:** Phase 1 — SSH & Authentication Hardening

## Current Position

Phase: 2 — Network Hardening
Plan: 02-02 complete (sysctl hardening + UFW logging)
Status: In progress — next: Phase 3 (app layer) or remaining Phase 2 plans
Last activity: 2026-04-14 — Completed 02-02 sysctl hardening + UFW logging

Progress: [███░░░░░░░░░░░░░░░░░░] 3/4 plans; 0/4 phases complete

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

**02-02 sysctl hardening + UFW logging (2026-04-14):**
- ip_forward NOT set to 0 — Docker requires net.ipv4.ip_forward = 1
- docker0.rp_filter = 2 (Docker-managed) — accepted, global all.rp_filter = 1 is authoritative for non-Docker interfaces
- UFW logging upgraded from low to medium

**01-02 fail2ban + auditd (2026-04-14):**
- banaction=ufw chosen — UFW is active firewall, keeps ban state consistent
- Ports 22+2022 covered in sshd jail — matches both sshd listening ports
- auditd left with default rules — no custom rules needed for Phase 1
- fail2ban was banning live attackers (8 IPs, 47 failed attempts) by the time verification ran

### Pending Todos

- Confirm exact Icecast stream mountpoint URL before Phase 4 stream-health AC check

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-14T04:52:57Z
Stopped at: Completed 02-02-PLAN.md (sysctl hardening + UFW logging)
Resume file: None
