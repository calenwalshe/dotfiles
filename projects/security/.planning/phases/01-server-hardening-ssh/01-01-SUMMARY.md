---
phase: "01"
plan: "01-01"
subsystem: ssh-hardening
tags: [ssh, sshd, password-auth, root-login, x11, gateway-ports, loglevel]

dependency-graph:
  requires: []
  provides: [ssh-hardened, password-auth-disabled, root-login-disabled]
  affects: [02-docker-hardening, 03-fail2ban-auditd, 04-pentest-verification]

tech-stack:
  added: []
  patterns: [ssh-config-split-files]

key-files:
  created: []
  modified:
    - /etc/ssh/sshd_config.d/50-cloud-init.conf
    - /etc/ssh/sshd_config

decisions:
  - "PasswordAuthentication disabled in cloud-init override (50-cloud-init.conf) which takes precedence"
  - "PermitRootLogin, X11Forwarding, GatewayPorts, LogLevel changed in main sshd_config"
  - "Port 2022 (etserver/EternalTerminal) documented as blocked by UFW default deny — no change needed"

metrics:
  duration: "~5 minutes"
  completed: "2026-04-14"
---

# Phase 1 Plan 01: SSH Hardening Summary

**One-liner:** Disabled SSH password auth and root login, locked down X11/GatewayPorts, set VERBOSE logging — all five sshd -T values confirmed.

## What Was Done

### Task 1: Port 2022 documented

Port 2022 is owned by `etserver` (EternalTerminal, pid 986). It listens on `0.0.0.0:2022` and `[::]:2022`. UFW has no allow rule for port 2022, so it is blocked by the default deny policy. No firewall change or service change is needed — the port is already inaccessible externally.

### Task 2: PasswordAuthentication disabled

Edited `/etc/ssh/sshd_config.d/50-cloud-init.conf`:
- Before: `PasswordAuthentication yes`
- After: `PasswordAuthentication no`

This file is loaded via `Include /etc/ssh/sshd_config.d/*.conf` in the main config and takes precedence over the commented-out main config entry.

### Task 3: Main sshd_config hardened

Four changes applied to `/etc/ssh/sshd_config`:

| Setting | Before | After |
|---------|--------|-------|
| `PermitRootLogin` | `yes` (uncommented at EOF) | `no` |
| `X11Forwarding` | `yes` | `no` |
| `GatewayPorts` | `clientspecified` | `no` |
| `LogLevel` | `#LogLevel INFO` (commented) | `LogLevel VERBOSE` |

### Task 4: sshd restarted

```
sudo systemctl restart sshd
systemctl is-active sshd → active
```

### Task 5: Verification

```
$ sudo sshd -T | grep -E "passwordauthentication|permitrootlogin|x11forwarding|gatewayports|loglevel"
permitrootlogin no
passwordauthentication no
x11forwarding no
gatewayports no
loglevel VERBOSE
```

All five values match success criteria.

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

Phase 2 (Docker UFW hardening) can proceed. SSH attack vectors are closed:
- Password brute force: blocked (PasswordAuthentication no)
- Root login: blocked (PermitRootLogin no)
- Audit trail: improved (LogLevel VERBOSE writes key fingerprint on each auth)
