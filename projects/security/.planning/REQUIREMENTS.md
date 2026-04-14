# Requirements: Server Hardening — radio.calenwalshe.com

**Defined:** 2026-04-14
**Core Value:** Two active critical compromise vectors are closed (SSH password brute force, Docker UFW bypass), the radio stream remains continuously available, and a PTES-structured pentest confirms all in-scope fixes hold.

## Hardening Requirements

None formalized with REQ-IDs. All requirements are derived directly from the contract done criteria and spec acceptance criteria. See `docs/cortex/contracts/server-hardening/contract-001.md` — `## Done Criteria` section.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SSH: PasswordAuthentication no + PermitRootLogin no | Phase 1: SSH & Authentication | Complete |
| SSH: X11Forwarding no + GatewayPorts no + LogLevel VERBOSE | Phase 1: SSH & Authentication | Complete |
| Port 2022 identified and resolved | Phase 1: SSH & Authentication | Complete |
| fail2ban installed, active, sshd jail enabled | Phase 1: SSH & Authentication | Complete |
| auditd installed and active | Phase 1: SSH & Authentication | Complete |
| Docker services rebound to 127.0.0.1 (no 0.0.0.0 except Caddy 80/443) | Phase 2: Network Exposure Closure | Complete |
| Key Docker ports filtered/closed externally (nmap confirmed) | Phase 2: Network Exposure Closure | Complete |
| sysctl hardening applied (rp_filter=1, send_redirects=0, log_martians=1) | Phase 2: Network Exposure Closure | Complete |
| UFW logging at medium | Phase 2: Network Exposure Closure | Complete |
| Caddy security headers on all vhosts (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy) | Phase 3: Application Layer | Complete |
| Dashboard routes /status and /costs return 401/403 | Phase 3: Application Layer | Complete |
| vnc-auth.calenwalshe.com removed from Caddyfile | Phase 3: Application Layer | Complete |
| Radio stream accessible (curl /stream returns 200/302) | Phase 4: Pentest & Closure | Complete |
| Pentest findings report exists, all in-scope Critical/High closed | Phase 4: Pentest & Closure | Complete |

**Coverage:**
- Hardening requirements: 14 total — all mapped
- Unmapped: 0
