---
slug: server-hardening
spec_id: server-hardening-001
created: 2026-04-14
status: pending_approval
---

# Spec: server-hardening

## 1. Problem

The server at `149.28.12.120` (radio.calenwalshe.com), running Ubuntu 24.04.3 LTS, has two active critical compromise vectors that need closing immediately: SSH root login via password is fully enabled with no brute-force protection, meaning any attacker can attempt unlimited password guesses against root on port 22; and the `DOCKER-USER` iptables chain is empty, which causes Docker's NAT PREROUTING rules to bypass UFW for all `0.0.0.0`-published container ports — approximately 30 services including codex-bridge, gemini-bridge, cost-dashboard, and the MCP server are likely internet-reachable right now despite UFW appearing restrictive. A root SSH compromise directly exposes every API key held in Docker container env vars (OpenAI, Anthropic, Google), making this an economic as well as operational risk. Layered on top are medium-priority gaps: no Caddy security headers, UFW logging set to `low` (misses allowed connections), no fail2ban or auditd, incomplete sysctl hardening, unauthenticated admin dashboard routes, and a stale VNC Caddyfile entry. This spec covers systematic closure of all gaps — Critical first — followed by a structured pentest using PTES methodology to verify the fixes hold and surface any remaining exposures.

## 2. Acceptance Criteria

- [ ] `PasswordAuthentication no` and `PermitRootLogin no` verified in sshd running config (`sshd -T | grep -E "passwordauth|permitroot"`)
- [ ] `X11Forwarding no` and `GatewayPorts no` in sshd running config
- [ ] Port 2022 is identified: `sudo ss -tlnp | grep 2022` names the owning process. If closed: `nmap -p 2022 149.28.12.120` returns `closed` or `filtered`. If accept-risk: a FIND-NNN record in the pentest report documents the process, exposure, and explicit owner sign-off
- [ ] All internal Docker services use `127.0.0.1:PORT:PORT` bindings — no `0.0.0.0:PORT` bindings except Caddy's `:80` and `:443`
- [ ] `nmap -p 9090,9091,9092,9095,9098,9099 149.28.12.120` returns `filtered` or `closed` for all listed ports
- [ ] fail2ban is installed, running (`systemctl is-active fail2ban`), and covers ports 22 and 2022 (`fail2ban-client status sshd`)
- [ ] auditd is installed and running (`systemctl is-active auditd`)
- [ ] `curl -sI https://radio.calenwalshe.com` returns `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` headers
- [ ] `curl -sI https://radio.calenwalshe.com | grep -i server` returns no `Server:` header
- [ ] `/status` and `/costs` routes on `:443` return HTTP 401 or 403 for unauthenticated requests
- [ ] `vnc-auth.calenwalshe.com` entry removed from Caddyfile (grep confirms absent)
- [ ] `/etc/sysctl.d/99-hardening.conf` exists and `sysctl net.ipv4.conf.all.rp_filter` returns `1`; `sysctl net.ipv4.conf.all.send_redirects` returns `0`; `sysctl net.ipv4.conf.all.log_martians` returns `1`
- [ ] UFW logging level is `medium` (`ufw status verbose | grep Logging`)
- [ ] `sshd -T | grep loglevel` returns `VERBOSE`
- [ ] `curl -sI https://radio.calenwalshe.com/stream` returns HTTP 200 (or HTTP 302 to the Icecast mountpoint); the stream URL is the one currently exposed by the Caddyfile — confirm exact mountpoint before running
- [ ] Pentest report exists at `docs/findings/server-hardening-pentest-YYYYMMDD.md`; all findings corresponding to the hardening items in this spec's scope (SSH, Docker bypass, security headers, sysctl, fail2ban, dashboard auth) are marked CLOSED; any new unrelated findings discovered during scanning are documented but do not block this spec

## 3. Scope

### In Scope

- SSH hardening: disable PasswordAuthentication, PermitRootLogin, X11Forwarding, GatewayPorts; set LogLevel VERBOSE
- Docker UFW bypass fix: rebind all internal service ports from `0.0.0.0:PORT:PORT` to `127.0.0.1:PORT:PORT` in docker-compose files
- Port 2022 identification and resolution (close or document)
- fail2ban installation and configuration covering SSH ports
- auditd installation and enablement
- Caddy global security headers snippet (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Server header removal) applied to all vhosts
- Dashboard route authentication: basic auth or IP restriction on `/status` and `/costs`
- Caddyfile cleanup: remove `vnc-auth.calenwalshe.com` stale entry
- sysctl hardening file: rp_filter=1, send_redirects=0, log_martians=1, source_route=0, secure_redirects=0, tcp_rfc1337=1
- UFW logging upgrade from `low` to `medium`
- Pentest (PTES methodology): phases 0–6 using nmap, testssl.sh, nuclei, lynis
- Pentest findings documented in CVSS-scored report; closure verified per PTES Phase 6

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

## 4. Architecture Decision

**Chosen approach:** Incremental hardening in priority order (Critical → High → Medium → Low) with each step independently verifiable, followed by a structured PTES pentest as the closure gate.

**Rationale:** Closes the two highest-impact vectors (SSH password auth + Docker bypass) first to minimize the window of exposure before any other changes are made. Docker port rebinding to `127.0.0.1` is chosen over DOCKER-USER iptables rules because it is durable across reboots and restarts without requiring iptables-persistent. The pentest at the end acts as closure verification per PTES Phase 6 — each fix is retested with the original PoC, not just assumed closed.

**Alternatives Considered:**

- **DOCKER-USER iptables DROP rule** — rejected: iptables rules are ephemeral without iptables-persistent; rebinding docker-compose ports to `127.0.0.1` is a durable config change that survives container and host restarts.
- **CrowdSec instead of fail2ban** — rejected: 50–100MB RAM overhead, requires internet connectivity for crowd-sourced ban lists, and adds operational complexity not commensurate with benefit for a low-traffic VPS. fail2ban covers SSH brute force adequately.
- **Docker user namespace remapping** — rejected: risk of breaking bind mounts and file ownership across a 40-container compose stack is high; the Docker UFW bypass is already fully addressed by `127.0.0.1` rebinding.
- **CSP headers now** — deferred: requires per-vhost content inventory to configure correctly without breaking the radio stream player; better handled as a separate focused task once the critical fixes are done.
- **AppArmor/seccomp custom profiles** — deferred: Docker CE default seccomp profile already blocks 44 syscalls; custom profiles require profiling each container workload, disproportionate effort for this scope.

## 5. Interfaces

| Interface | Type | Owner | Reads | Writes |
|-----------|------|-------|-------|--------|
| `/etc/ssh/sshd_config.d/50-cloud-init.conf` | OS config file | host | yes | yes — PasswordAuthentication, PermitRootLogin |
| `/etc/ssh/sshd_config` | OS config file | host | yes | yes — X11Forwarding, GatewayPorts, LogLevel |
| `/etc/sysctl.d/99-hardening.conf` | OS config file | host | no | yes — create new file |
| `/etc/fail2ban/jail.local` | fail2ban config | host | no | yes — create new file |
| `/home/agent/agent-stack/docker-compose.yml` (and sibling compose files) | Docker compose | agent-stack | yes | yes — rebind ports to 127.0.0.1 |
| Caddyfile (path: `/home/agent/agent-stack/Caddyfile` or equivalent) | Caddy config | agent-stack | yes | yes — security headers snippet, dashboard auth, VNC route removal |
| `docs/findings/server-hardening-pentest-YYYYMMDD.md` | Findings report | this spec | no | yes — create new file |
| UFW (`ufw` CLI) | Firewall | host | yes | yes — logging level |
| systemd (auditd, fail2ban, sshd) | Service manager | host | no | yes — enable/restart services |

**Note:** All Caddy config changes require `docker compose restart caddy` (inode change rule from system conventions).

## 6. Dependencies

| Name | Version | Purpose |
|------|---------|---------|
| fail2ban | latest apt | SSH brute-force IP banning via UFW |
| auditd | latest apt | Privilege escalation and file-access audit trail |
| nmap | latest apt | Port discovery, service fingerprinting, NSE scripts |
| testssl.sh | latest git | TLS protocol, cipher suite, and known-vuln audit |
| nuclei | v3 latest | CVE and misconfiguration scanning (5000+ templates) |
| lynis | latest apt | On-host OS hardening audit |
| logwatch | latest apt (optional) | Daily log digest emails |
| Docker CE | installed | Container runtime — UFW bypass fix is in docker-compose config, not daemon |

## 7. Risks

- **SSH lockout if key auth fails before PasswordAuthentication is disabled** — Mitigation: test `ssh -o PasswordAuthentication=no <user>@149.28.12.120` from a separate terminal before applying the config change; verify key works before saving the sshd config.
- **Docker compose port rebind causes brief service downtime** — Mitigation: rebind and restart one compose file at a time; after each restart, run `curl -sI https://radio.calenwalshe.com/stream` — if response is not 200/302 within 30 seconds, rollback that compose file (`git checkout` the changed file and `docker compose up -d`) before proceeding to the next.
- **Caddy restart fails after Caddyfile edit (inode change)** — Mitigation: use `docker compose restart caddy` not `caddy reload`; run `docker exec caddy caddy validate --config /etc/caddy/Caddyfile` before restart.
- **sysctl rp_filter=1 (strict) breaks Docker networking** — Mitigation: Docker sets `net.ipv4.conf.docker0.rp_filter=0` via its own sysctl tuning; set `net.ipv4.conf.default.rp_filter=1` but verify Docker bridge interface retains its value post-apply with `sysctl net.ipv4.conf.docker0.rp_filter`.
- **Port 2022 identity unknown — may be a critical internal service** — Mitigation: run `sudo ss -tlnp | grep 2022` and `sudo lsof -i :2022` before any firewall changes; document finding before proceeding.
- **fail2ban UFW banaction fails if UFW is not in `ufw` mode** — Mitigation: verify `ufw status` shows active before configuring `banaction = ufw` in jail.local.
- **Pentest nmap full port scan (-p-) is noisy and slow** — Mitigation: run in background with `-oN nmap-full.txt`; use `-T4` throttle; expected runtime 5–15 min.

## 8. Sequencing

1. **Identify port 2022** — `sudo ss -tlnp | grep 2022` + `sudo lsof -i :2022`. Document process. Decide: close or accept-risk. Checkpoint: port 2022 status documented.
2. **Verify SSH key auth** — from a separate terminal, test `ssh -o PasswordAuthentication=no agent@149.28.12.120`. Confirm key login succeeds before proceeding. Checkpoint: successful keyonly SSH session confirmed.
3. **Harden SSH config** — set `PasswordAuthentication no`, `PermitRootLogin no`, `X11Forwarding no`, `GatewayPorts no`, `LogLevel VERBOSE` in sshd_config files. Restart sshd. Verify with `sshd -T`. Checkpoint: `sshd -T` shows all four params set correctly.
4. **Install fail2ban** — `apt install fail2ban`, create `/etc/fail2ban/jail.local`, enable and start. Verify `fail2ban-client status sshd`. Checkpoint: fail2ban active with sshd jail enabled.
5. **Install auditd** — `apt install auditd`, `systemctl enable --now auditd`. Checkpoint: `systemctl is-active auditd` returns `active`.
6. **Rebind Docker services to 127.0.0.1** — Edit all docker-compose files: change `0.0.0.0:PORT:PORT` → `127.0.0.1:PORT:PORT` for all internal services. Keep only Caddy's `:80` and `:443` on `0.0.0.0`. Restart affected containers. Checkpoint: `docker ps` shows no `0.0.0.0:PORT` bindings except Caddy 80/443; `nmap -p 9090,9091 149.28.12.120` returns filtered.
7. **Apply sysctl hardening** — Create `/etc/sysctl.d/99-hardening.conf`, run `sudo sysctl --system`. Verify key values. Checkpoint: `sysctl net.ipv4.conf.all.rp_filter` = 1.
8. **Upgrade UFW logging to medium** — `sudo ufw logging medium`. Checkpoint: `ufw status verbose | grep Logging` shows `medium`.
9. **Apply Caddy security headers** — Add `(security_headers)` snippet to Caddyfile, import in all vhosts. Add basic auth or IP restriction to `/status` and `/costs`. Remove `vnc-auth.calenwalshe.com` entry. Validate Caddyfile, then `docker compose restart caddy`. Checkpoint: `curl -sI https://radio.calenwalshe.com` shows HSTS and X-Content-Type-Options headers; `/status` returns 401.
10. **Verify radio stream** — `curl -I https://radio.calenwalshe.com` returns 200; audio stream endpoint accessible. Checkpoint: stream live and playing.
11. **Run pentest (PTES Phase 0–2)** — Write authorization note. Run `nmap -sV -sC -O -p- -T4 149.28.12.120`, `testssl.sh --fast radio.calenwalshe.com`, `nuclei -u 149.28.12.120 -t cves/ -t misconfigurations/ -t exposures/`, `sudo lynis audit system`. Checkpoint: scan output files captured.
12. **Document findings** — Create `docs/findings/server-hardening-pentest-YYYYMMDD.md` using FIND-NNN template with CVSS v3.1 scoring for each confirmed finding. Checkpoint: findings report exists.
13. **Closure verification (PTES Phase 6)** — For each Critical/High finding, rerun original PoC against patched system and confirm failure. Update finding status to CLOSED. Checkpoint: zero Critical/High findings remain open.

## 9. Tasks

- [ ] Run `sudo ss -tlnp | grep 2022` and `sudo lsof -i :2022` — identify port 2022 process; document in findings log
- [ ] From separate terminal: verify `ssh -o PasswordAuthentication=no agent@149.28.12.120` succeeds with key auth
- [ ] Set `PasswordAuthentication no` in `/etc/ssh/sshd_config.d/50-cloud-init.conf`
- [ ] Set `PermitRootLogin no`, `X11Forwarding no`, `GatewayPorts no`, `LogLevel VERBOSE` in `/etc/ssh/sshd_config`
- [ ] `sudo systemctl restart sshd` — verify with `sshd -T | grep -E "passwordauth|permitroot|x11|gateway|loglevel"`
- [ ] `sudo apt install -y fail2ban` and create `/etc/fail2ban/jail.local` with sshd jail covering ports 22,2022
- [ ] `sudo systemctl enable --now fail2ban` — verify with `fail2ban-client status sshd`
- [ ] `sudo apt install -y auditd` — `sudo systemctl enable --now auditd`
- [ ] Locate all docker-compose files in `/home/agent/agent-stack/` — list all `0.0.0.0:PORT:PORT` bindings
- [ ] Edit each compose file: change internal service bindings to `127.0.0.1:PORT:PORT`; keep Caddy `:80`/`:443` on `0.0.0.0`
- [ ] `docker compose up -d` for changed compose files — verify `docker ps` shows 127.0.0.1 bindings
- [ ] `nmap -p 9090,9091,9092,9095,9098,9099 149.28.12.120` — confirm all return `filtered` or `closed`
- [ ] Create `/etc/sysctl.d/99-hardening.conf` with rp_filter=1, send_redirects=0, log_martians=1, source_route=0, secure_redirects=0, tcp_rfc1337=1
- [ ] `sudo sysctl --system` — verify key params with `sysctl net.ipv4.conf.all.rp_filter`
- [ ] `sudo ufw logging medium`
- [ ] Add `(security_headers)` snippet to Caddyfile with HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, `-Server`
- [ ] Import `security_headers` in all vhost blocks in Caddyfile
- [ ] Add `basicauth` (or `@internal` IP restriction) to `/status` and `/costs` route matchers in Caddyfile
- [ ] Remove `vnc-auth.calenwalshe.com` block from Caddyfile
- [ ] `docker exec caddy caddy validate --config /etc/caddy/Caddyfile` — confirm no errors
- [ ] `docker compose restart caddy` — verify `curl -sI https://radio.calenwalshe.com` shows HSTS header and no Server header
- [ ] Verify radio stream still accessible after Caddy restart
- [ ] Write pre-engagement authorization note with scope, IP, test window
- [ ] `nmap -sV -sC -O -p- -T4 149.28.12.120 -oN nmap-full.txt`
- [ ] `./testssl.sh --fast https://radio.calenwalshe.com`
- [ ] `nuclei -u 149.28.12.120 -t cves/ -t misconfigurations/ -t exposures/ -t network/ -o nuclei-findings.txt`
- [ ] `sudo lynis audit system --report-file /tmp/lynis-report.txt`
- [ ] Review scanner output — confirm each finding manually before recording
- [ ] Create `docs/findings/server-hardening-pentest-YYYYMMDD.md` with FIND-NNN entries, CVSS v3.1 scores
- [ ] For each Critical/High finding: rerun original PoC — confirm failure — update status to CLOSED
- [ ] Final verification: `curl -I https://radio.calenwalshe.com` returns 200; stream accessible
