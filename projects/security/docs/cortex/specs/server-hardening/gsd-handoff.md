---
slug: server-hardening
handoff_version: 1
created: 2026-04-14
contract: docs/cortex/contracts/server-hardening/contract-001.md
---

# GSD Handoff: server-hardening

## Objective

Harden the radio.calenwalshe.com VPS (149.28.12.120, Ubuntu 24.04.3 LTS) against active and latent attack vectors by applying SSH hardening, Docker port rebinding, fail2ban, auditd, Caddy security headers, sysctl tuning, and UFW logging upgrades — then confirm closure with a PTES-structured pentest. Success means the two critical live exposures (SSH password brute force, Docker UFW bypass) are closed and verified, and the radio stream remains up throughout.

## Deliverables

| Artifact | Path |
|----------|------|
| SSH hardening | `/etc/ssh/sshd_config` + `/etc/ssh/sshd_config.d/50-cloud-init.conf` |
| sysctl hardening | `/etc/sysctl.d/99-hardening.conf` (new file) |
| fail2ban config | `/etc/fail2ban/jail.local` (new file) |
| Docker compose rebind | All compose files in `/home/agent/agent-stack/` |
| Caddy security headers + auth | Caddyfile in `/home/agent/agent-stack/` |
| Pentest findings report | `docs/findings/server-hardening-pentest-YYYYMMDD.md` (new file) |

## Requirements

None formalized.

## Tasks

1. - [ ] Identify port 2022 process (`sudo ss -tlnp | grep 2022` + `sudo lsof -i :2022`); document
2. - [ ] Verify SSH key auth works: `ssh -o PasswordAuthentication=no agent@149.28.12.120` from a second terminal
3. - [ ] Set `PasswordAuthentication no` in `/etc/ssh/sshd_config.d/50-cloud-init.conf`
4. - [ ] Set `PermitRootLogin no`, `X11Forwarding no`, `GatewayPorts no`, `LogLevel VERBOSE` in `/etc/ssh/sshd_config`
5. - [ ] `sudo systemctl restart sshd` — verify with `sshd -T | grep -E "passwordauth|permitroot|x11|gateway|loglevel"`
6. - [ ] `sudo apt install -y fail2ban` — create `/etc/fail2ban/jail.local` (sshd jail, ports 22+2022, `banaction=ufw`) — `sudo systemctl enable --now fail2ban`
7. - [ ] `sudo apt install -y auditd` — `sudo systemctl enable --now auditd`
8. - [ ] Locate all `0.0.0.0:PORT:PORT` bindings in agent-stack compose files — rebind all internal services to `127.0.0.1:PORT:PORT`; keep Caddy `:80`/`:443` on `0.0.0.0`
9. - [ ] `docker compose up -d` for each changed compose file; verify with `docker ps`; after each restart confirm `curl -sI https://radio.calenwalshe.com/stream` returns 200/302 within 30s; rollback if not
10. - [ ] `nmap -p 9090,9091,9092,9095,9098,9099 149.28.12.120` — confirm all return `filtered` or `closed`
11. - [ ] Create `/etc/sysctl.d/99-hardening.conf`; `sudo sysctl --system`; verify `sysctl net.ipv4.conf.all.rp_filter` = 1
12. - [ ] `sudo ufw logging medium`
13. - [ ] Add `(security_headers)` global snippet to Caddyfile (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, `-Server`); import in all vhosts
14. - [ ] Add basicauth or IP restriction to `/status` and `/costs` routes in Caddyfile
15. - [ ] Remove `vnc-auth.calenwalshe.com` block from Caddyfile
16. - [ ] `docker exec caddy caddy validate --config /etc/caddy/Caddyfile` — `docker compose restart caddy`
17. - [ ] Verify `curl -sI https://radio.calenwalshe.com` shows HSTS, X-Content-Type-Options; stream still accessible
18. - [ ] Write pre-engagement authorization note (scope: 149.28.12.120, all ports, test window)
19. - [ ] `nmap -sV -sC -O -p- -T4 149.28.12.120 -oN nmap-full.txt`
20. - [ ] `./testssl.sh --fast https://radio.calenwalshe.com`
21. - [ ] `nuclei -u 149.28.12.120 -t cves/ -t misconfigurations/ -t exposures/ -t network/ -o nuclei-findings.txt`
22. - [ ] `sudo lynis audit system --report-file /tmp/lynis-report.txt`
23. - [ ] Manually confirm each scanner finding — create `docs/findings/server-hardening-pentest-YYYYMMDD.md` with FIND-NNN records, CVSS v3.1 scores
24. - [ ] For each in-scope Critical/High finding: rerun original PoC — confirm failure — mark CLOSED
25. - [ ] Final: `curl -sI https://radio.calenwalshe.com/stream` returns 200/302; stream accessible

## Acceptance Criteria

- `PasswordAuthentication no` and `PermitRootLogin no` in sshd running config
- `X11Forwarding no` and `GatewayPorts no` in sshd running config
- Port 2022 identified, closed or documented with explicit accept-risk
- All internal Docker services bound to `127.0.0.1`; `nmap` confirms key ports filtered/closed
- fail2ban and auditd installed and active
- HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy headers on `https://radio.calenwalshe.com`
- `/status` and `/costs` return 401/403 for unauthenticated requests
- sysctl rp_filter=1, send_redirects=0, log_martians=1 applied
- UFW logging at `medium`
- Radio stream accessible (`/stream` endpoint returns 200/302) after all changes
- Pentest report exists; all in-scope Critical/High findings closed

## Contract Link

docs/cortex/contracts/server-hardening/contract-001.md
