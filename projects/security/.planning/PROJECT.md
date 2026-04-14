# Server Hardening — radio.calenwalshe.com

## What This Is

The server at `149.28.12.120` (radio.calenwalshe.com), running Ubuntu 24.04.3 LTS, has two active critical compromise vectors that need closing immediately: SSH root login via password is fully enabled with no brute-force protection; and the `DOCKER-USER` iptables chain is empty, causing Docker's NAT PREROUTING rules to bypass UFW for all `0.0.0.0`-published container ports — approximately 30 services are internet-reachable despite UFW appearing restrictive. A root SSH compromise directly exposes every API key held in Docker container env vars (OpenAI, Anthropic, Google). Layered on top are medium-priority gaps: no Caddy security headers, UFW logging set to `low`, no fail2ban or auditd, incomplete sysctl hardening, unauthenticated admin dashboard routes, and a stale VNC Caddyfile entry.

## Core Value

Two active critical compromise vectors are closed (SSH password brute force, Docker UFW bypass), the radio stream remains continuously available, and a PTES-structured pentest confirms all in-scope fixes hold.

## Requirements

### Validated

- ✓ SSH: PasswordAuthentication no + PermitRootLogin no — v1.0
- ✓ SSH: X11Forwarding no + GatewayPorts no + LogLevel VERBOSE — v1.0
- ✓ Port 2022 identified (etserver) and accept-risked — v1.0
- ✓ fail2ban installed, active, sshd jail enabled — v1.0
- ✓ auditd installed and active with custom ruleset — v1.0
- ✓ Docker services rebound to 127.0.0.1 — v1.0
- ✓ Key Docker ports filtered/closed externally — v1.0
- ✓ sysctl hardening applied — v1.0
- ✓ UFW logging at medium — v1.0
- ✓ Caddy security headers on all vhosts — v1.0
- ✓ Dashboard routes /status+/costs return 401 — v1.0
- ✓ vnc-auth.calenwalshe.com removed from Caddyfile — v1.0
- ✓ Radio stream accessible throughout — v1.0
- ✓ Pentest findings report, all in-scope Critical/High closed — v1.0

### Active

None — v1.0 complete. Start fresh with `/gsd:define-requirements` for next milestone.

### Out of Scope

- Application architecture changes or radio pipeline modifications
- WAF or CDN changes beyond what Cloudflare already provides
- GDPR or compliance audit
- Secrets management overhaul (separate slug)
- Docker user namespace remapping (risk of breaking 40-container compose stack)
- AppArmor/seccomp custom profiles beyond Docker CE defaults
- CrowdSec (optional, deferred — RAM overhead not justified for this stack)
- Content-Security-Policy headers (high configuration effort, deferred)
- Greenbone/OpenVAS setup (quarterly tool, not this spec)
- Provider migration

## Context

**Current baseline:** Ubuntu 24.04.3 LTS, SSH with PasswordAuthentication + PermitRootLogin enabled, DOCKER-USER iptables chain empty, no fail2ban, no auditd, no Caddy security headers, UFW logging at `low`, sysctl partially hardened.

**Target:** Defensible security baseline — critical vectors closed, intrusion detection active, connection logging actionable, application-layer headers hardened, pentest confirms closure.

**Ownership contract:** `docs/cortex/contracts/server-hardening/contract-001.md`

## Constraints

- Radio stream at `radio.calenwalshe.com` must remain available — no changes that require unannounced downtime
- Docker bridge routing on `agent-stack_default` (172.18.0.0/16) must remain intact
- Caddy TLS termination + Cloudflare proxy chain must continue functioning
- Icecast source password must remain env-var sourced (`ICECAST_SOURCE_PASSWORD`)
- Host web frontend (`src/web/app.py`) runs on port 9093 bound to 0.0.0.0 — preserve this binding
- Every host service uses systemd with `Restart=always`; hardening must not break unit files
- Only Caddy's `:80` and `:443` may bind to `0.0.0.0`; all other Docker services must use `127.0.0.1`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 127.0.0.1 rebind over DOCKER-USER iptables DROP | Durable across reboots; no iptables-persistent dependency | ✓ All internal docker-compose bindings → 127.0.0.1 |
| fail2ban over CrowdSec | 50–100MB RAM overhead not justified; fail2ban covers SSH brute force | ✓ fail2ban with `banaction = ufw`, banning live attackers |
| sysctl in /etc/sysctl.d/99-hardening.conf | Never edit base sysctl.conf; drop file survives upgrades | ✓ New file at 99-hardening.conf |
| PTES pentest as closure gate | Each fix retested with original PoC — not assumed closed on deploy | ✓ PTES phases 0–6, CVSS v3.1, 12/12 findings closed |
| Pentest AC scoped to in-spec items | Prevents unbounded scope expansion from unrelated scan findings | ✓ Additional findings documented and subsequently all closed |

---
*Last updated: 2026-04-14 after v1.0 milestone*
