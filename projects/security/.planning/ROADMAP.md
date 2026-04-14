# Roadmap: Server Hardening — radio.calenwalshe.com

## Overview

Harden the radio.calenwalshe.com VPS (149.28.12.120, Ubuntu 24.04.3 LTS) against active and latent attack vectors by applying SSH hardening, Docker port rebinding, fail2ban, auditd, Caddy security headers, sysctl tuning, and UFW logging upgrades — then confirm closure with a PTES-structured pentest. Success means the two critical live exposures (SSH password brute force, Docker UFW bypass) are closed and verified, and the radio stream remains up throughout.

## Phases

### Phase 1: SSH & Authentication Hardening

**Goal**: Close the two SSH attack vectors (password auth + root login), identify and resolve port 2022, and install intrusion detection (fail2ban) and audit logging (auditd).
**Depends on**: Nothing
**Requirements**: SSH hardening, port 2022 resolution, fail2ban, auditd
**Success Criteria** (what must be TRUE):
  1. `sshd -T | grep -E "passwordauthentication|permitrootlogin"` returns `passwordauthentication no` and `permitrootlogin no`
  2. `sshd -T | grep -E "x11forwarding|gatewayports|loglevel"` returns `no`, `no`, `VERBOSE`
  3. Port 2022: process identified; either `nmap -p 2022 149.28.12.120` returns `closed`/`filtered`, or a FIND-NNN record with explicit accept-risk exists in the pentest report
  4. `systemctl is-active fail2ban` returns `active`; `fail2ban-client status sshd` shows jail enabled
  5. `systemctl is-active auditd` returns `active`
**Research**: Unlikely
**Plans**: 0 plans

---

### Phase 2: Network Exposure Closure

**Goal**: Eliminate the Docker UFW bypass by rebinding all internal service ports to 127.0.0.1 in docker-compose, and apply sysctl network hardening and UFW logging upgrade.
**Depends on**: Phase 1: SSH & Authentication Hardening
**Requirements**: Docker port rebinding, sysctl hardening, UFW logging
**Success Criteria** (what must be TRUE):
  1. `docker ps --format "{{.Ports}}"` shows no `0.0.0.0:PORT` bindings except Caddy 80 and 443
  2. `nmap -p 9090,9091,9092,9095,9098,9099 149.28.12.120` returns `filtered` or `closed` for all listed ports
  3. `sysctl net.ipv4.conf.all.rp_filter` = `1`; `sysctl net.ipv4.conf.all.send_redirects` = `0`; `sysctl net.ipv4.conf.all.log_martians` = `1`
  4. `ufw status verbose | grep Logging` shows `medium`
**Research**: Unlikely
**Plans**: 0 plans

---

### Phase 3: Application Layer Hardening

**Goal**: Add Caddy global security headers to all vhosts, protect the /status and /costs dashboard routes with authentication, and remove the stale vnc-auth.calenwalshe.com Caddyfile entry.
**Depends on**: Phase 2: Network Exposure Closure
**Requirements**: Caddy security headers, dashboard auth, Caddyfile cleanup
**Success Criteria** (what must be TRUE):
  1. `curl -sI https://radio.calenwalshe.com` response includes `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`; no `Server:` header
  2. `curl -s -o /dev/null -w "%{http_code}" https://radio.calenwalshe.com/status` returns `401` or `403`
  3. `grep -c "vnc-auth.calenwalshe.com" /home/agent/agent-stack/Caddyfile` returns `0`
**Research**: Unlikely
**Plans**: 0 plans

---

### Phase 4: Pentest & Closure Verification

**Goal**: Confirm the radio stream is still accessible, run a PTES-structured pentest (phases 0–6) against 149.28.12.120, document all findings with CVSS v3.1 scores, and verify each in-scope Critical/High finding is closed by re-running the original PoC.
**Depends on**: Phase 3: Application Layer Hardening
**Requirements**: Stream health, pentest execution, findings documentation, closure verification
**Success Criteria** (what must be TRUE):
  1. `curl -sI https://radio.calenwalshe.com/stream` returns HTTP 200 or 302
  2. `docs/findings/server-hardening-pentest-YYYYMMDD.md` exists; all findings in the in-scope hardening categories (SSH, Docker bypass, headers, sysctl, fail2ban, dashboard auth) are marked `Status: CLOSED`
**Research**: Unlikely
**Plans**: 0 plans

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| Phase 1: SSH & Authentication Hardening | 2/2 | Complete | 2026-04-14 |
| Phase 2: Network Exposure Closure | 2/2 | Complete | 2026-04-14 |
| Phase 3: Application Layer Hardening | 1/1 | Complete | 2026-04-14 |
| Phase 4: Pentest & Closure Verification | 3/3 | Complete | 2026-04-14 |
