---
id: server-hardening-001
slug: server-hardening
phase: execute
created: 2026-04-14
status: approved
---

# Contract: server-hardening-001

## Objective

Harden 149.28.12.120 (radio.calenwalshe.com) by closing the two active critical compromise vectors (SSH password auth + Docker UFW bypass), layering in fail2ban/auditd/sysctl/Caddy security controls, and running a PTES-structured pentest to verify all in-scope fixes hold — while keeping the radio stream continuously accessible.

## Deliverables

| # | Artifact | Path | Type |
|---|----------|------|------|
| 1 | SSH hardened config | `/etc/ssh/sshd_config` + `/etc/ssh/sshd_config.d/50-cloud-init.conf` | OS config |
| 2 | sysctl hardening file | `/etc/sysctl.d/99-hardening.conf` | OS config (new) |
| 3 | fail2ban jail config | `/etc/fail2ban/jail.local` | Service config (new) |
| 4 | Docker compose files (all rebound) | `/home/agent/agent-stack/*.yml` | Docker config |
| 5 | Caddyfile (headers + auth + cleanup) | `/home/agent/agent-stack/Caddyfile` | Caddy config |
| 6 | Pentest findings report | `docs/findings/server-hardening-pentest-YYYYMMDD.md` | Report (new) |

## Scope

### In Scope

- SSH: PasswordAuthentication, PermitRootLogin, X11Forwarding, GatewayPorts, LogLevel VERBOSE
- Docker UFW bypass: rebind all internal service ports to `127.0.0.1` in agent-stack compose files
- Port 2022 identification and resolution
- fail2ban installation and sshd jail configuration
- auditd installation and enablement
- Caddy security headers global snippet + per-vhost import
- Dashboard route auth (`/status`, `/costs`)
- Caddyfile cleanup (remove `vnc-auth.calenwalshe.com`)
- sysctl: rp_filter=1, send_redirects=0, log_martians=1, source_route=0, secure_redirects=0, tcp_rfc1337=1
- UFW logging upgrade to `medium`
- PTES pentest phases 0–6 against 149.28.12.120

### Out of Scope

- Application architecture or radio pipeline changes
- WAF/CDN changes beyond Cloudflare
- GDPR/compliance audit
- Secrets management overhaul
- Docker user namespace remapping
- AppArmor/seccomp custom profiles
- CrowdSec
- Content-Security-Policy headers
- Greenbone/OpenVAS

## Write Roots

| Path | Allowed Operations |
|------|--------------------|
| `/etc/ssh/sshd_config` | Edit |
| `/etc/ssh/sshd_config.d/50-cloud-init.conf` | Edit |
| `/etc/sysctl.d/99-hardening.conf` | Create |
| `/etc/fail2ban/jail.local` | Create |
| `/home/agent/agent-stack/*.yml` | Edit (all compose files) |
| `/home/agent/agent-stack/Caddyfile` | Edit |
| `docs/findings/server-hardening-pentest-YYYYMMDD.md` | Create |
| UFW (via `ufw` CLI) | `ufw logging medium` |
| systemd (via `systemctl`) | enable/start auditd, fail2ban; restart sshd |
| docker compose (via CLI) | `up -d`, `restart caddy` |

**Explicitly NOT allowed:** editing files outside the write roots above; modifying `/etc/ufw/` rules files directly; touching `/home/agent/openclaw-fresh/` or any service outside agent-stack.

## Done Criteria

- [ ] `sshd -T | grep -E "passwordauth|permitroot"` returns `passwordauthentication no` and `permitrootlogin no`
- [ ] `sshd -T | grep -E "x11forwarding|gatewayports|loglevel"` returns `no`, `no`, `VERBOSE`
- [ ] Port 2022: process identified; either `nmap -p 2022 149.28.12.120` returns `closed`/`filtered`, or a FIND-NNN record with explicit accept-risk exists in the pentest report
- [ ] `docker ps --format "{{.Ports}}"` shows no `0.0.0.0:PORT` bindings except Caddy 80 and 443
- [ ] `nmap -p 9090,9091,9092,9095,9098,9099 149.28.12.120` returns `filtered` or `closed` for all listed ports
- [ ] `systemctl is-active fail2ban` returns `active`; `fail2ban-client status sshd` shows jail enabled
- [ ] `systemctl is-active auditd` returns `active`
- [ ] `curl -sI https://radio.calenwalshe.com` response includes `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`; no `Server:` header
- [ ] `curl -s -o /dev/null -w "%{http_code}" https://radio.calenwalshe.com/status` returns `401` or `403`
- [ ] `grep -r "vnc-auth.calenwalshe.com" /home/agent/agent-stack/Caddyfile` returns no matches
- [ ] `sysctl net.ipv4.conf.all.rp_filter` = `1`; `sysctl net.ipv4.conf.all.send_redirects` = `0`; `sysctl net.ipv4.conf.all.log_martians` = `1`
- [ ] `ufw status verbose | grep Logging` shows `medium`
- [ ] `curl -sI https://radio.calenwalshe.com/stream` returns HTTP 200 or 302
- [ ] `docs/findings/server-hardening-pentest-YYYYMMDD.md` exists; all findings in the in-scope hardening categories (SSH, Docker bypass, headers, sysctl, fail2ban, dashboard auth) are marked `Status: CLOSED`

## Validators

```bash
# 1. SSH auth settings
sshd -T | grep -E "passwordauthentication|permitrootlogin|x11forwarding|gatewayports|loglevel"

# 2. Docker port bindings
docker ps --format "{{.Ports}}" | grep "0.0.0.0" | grep -v ":80\|:443"
# Expected: no output

# 3. nmap confirm Docker ports filtered
nmap -p 9090,9091,9092,9095,9098,9099 149.28.12.120
# Expected: all ports filtered or closed

# 4. fail2ban + auditd active
systemctl is-active fail2ban auditd

# 5. Caddy security headers
curl -sI https://radio.calenwalshe.com | grep -iE "(strict-transport|x-content-type|x-frame|referrer-policy|server:)"

# 6. Dashboard auth
curl -s -o /dev/null -w "%{http_code}" https://radio.calenwalshe.com/status
# Expected: 401 or 403

# 7. sysctl values
sysctl net.ipv4.conf.all.rp_filter net.ipv4.conf.all.send_redirects net.ipv4.conf.all.log_martians

# 8. UFW logging level
ufw status verbose | grep Logging

# 9. Stream health
curl -sI https://radio.calenwalshe.com/stream | head -1

# 10. VNC route removed
grep -c "vnc-auth.calenwalshe.com" /home/agent/agent-stack/Caddyfile
# Expected: 0
```

## Eval Plan

docs/cortex/evals/server-hardening/eval-plan.md (pending)

## Repair Budget

```
max_repair_contracts: 3
cooldown_between_repairs: 1
```

### Failed Approaches

(none)

### Why Previous Approach Failed

N/A — initial contract

## Approvals

- [ ] Contract approved for execution
- [ ] Evals approved

## Rollback Hints

| Change | Rollback |
|--------|---------|
| SSH config | `git checkout /etc/ssh/sshd_config /etc/ssh/sshd_config.d/50-cloud-init.conf && sudo systemctl restart sshd` |
| sysctl | `sudo rm /etc/sysctl.d/99-hardening.conf && sudo sysctl --system` |
| Docker compose port rebind | `git checkout <compose-file> && docker compose up -d` |
| Caddyfile changes | `git checkout /home/agent/agent-stack/Caddyfile && docker compose restart caddy` |
| fail2ban | `sudo systemctl stop fail2ban && sudo apt remove fail2ban` |
| auditd | `sudo systemctl stop auditd` (does not need removal unless noisy) |
| UFW logging | `sudo ufw logging low` |
