# Project Milestones: Server Hardening — radio.calenwalshe.com

## v1.0 Server Hardening (Shipped: 2026-04-14)

**Delivered:** Closed two active critical compromise vectors (SSH password brute force, Docker UFW bypass), layered in fail2ban/auditd/sysctl/Caddy security controls, and confirmed closure with a PTES-structured pentest — 12/12 findings closed, radio stream continuously available throughout.

**Phases completed:** 1–4 (7 plans total)

**Key accomplishments:**

- SSH fully hardened: password auth disabled, root login blocked, fail2ban banning live attackers within seconds of activation (8 IPs, 47 failed attempts)
- Docker UFW bypass eliminated: 18 agent-stack ports + 4 orphaned containers rebound to 127.0.0.1
- Caddy security headers applied globally across all 13 vhosts; /status+/costs behind basicauth
- sysctl hardened: rp_filter, log_martians, send_redirects, source routing all locked down
- auditd active with custom privilege-escalation ruleset
- PTES pentest confirmed all closures; lynis hardening index 63/100; nuclei: 0 CVEs
- 83 OS packages upgraded; AllowTcpForwarding+AgentForwarding disabled

**Stats:**

- 20 files created/modified
- 1,515 lines added
- 4 phases, 7 plans
- 1 day (2026-04-14, single engagement)

**Git range:** `436ee24` (bridge import) → `b5d6c58` (final follow-up)

---
