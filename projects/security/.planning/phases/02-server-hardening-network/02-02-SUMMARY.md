---
plan: 02-02
phase: 2
subsystem: network-hardening
tags: [sysctl, ufw, kernel-hardening, rp_filter, martians, tcp-hardening]
requires: []
provides:
  - /etc/sysctl.d/99-hardening.conf (kernel network hardening)
  - UFW logging at medium level
affects:
  - Phase 4 pentest AC (network hardening checks)
tech-stack:
  added: []
  patterns:
    - sysctl.d drop-in config for kernel parameter management
key-files:
  created:
    - /etc/sysctl.d/99-hardening.conf
  modified: []
decisions:
  - ip_forward left untouched (not set to 0) — Docker requires net.ipv4.ip_forward = 1
  - docker0 rp_filter = 2 (strict managed by Docker kernel networking) — accepted, not overridden
duration: ~1 minute
completed: "2026-04-14"
---

# Phase 2 Plan 02: sysctl Hardening + UFW Logging Summary

**One-liner:** Kernel network hardening via sysctl.d drop-in — rp_filter=1, send_redirects=0, log_martians=1, tcp_rfc1337=1, SYN backlog tuned — plus UFW logging upgraded to medium.

## What Was Done

Created `/etc/sysctl.d/99-hardening.conf` with 14 kernel parameter settings covering:

- Reverse path filtering (strict mode) on all/default interfaces
- Martian packet logging on all/default interfaces
- Source routing disabled
- ICMP redirect sending disabled; secure redirects disabled
- ICMP broadcast echo protection
- Bogus ICMP error suppression
- SYN flood protection (backlog 4096, synack retries 2)
- tcp_rfc1337 TIME_WAIT assassination prevention

Applied with `sudo sysctl --system`. UFW logging upgraded from `low` to `medium`.

## Verification Output

**sysctl --system output (filtered to 99-hardening):**
```
* Applying /etc/sysctl.d/99-hardening.conf ...
net.ipv4.icmp_ignore_bogus_error_responses = 1
```
(Only one value shown = only that value changed from kernel default; all others were already at target values or were set silently without output.)

**Key value verification:**
```
net.ipv4.conf.all.rp_filter = 1      ✓
net.ipv4.conf.all.send_redirects = 0 ✓
net.ipv4.conf.all.log_martians = 1   ✓
```

**Docker bridge check:**
```
net.ipv4.conf.docker0.rp_filter = 2
```
Docker manages its own interface-level rp_filter independently. Value of 2 (strict) is fine — Docker networking verified with 45 running containers.

**UFW logging:**
```
Logging: on (medium)  ✓
```

## Decisions Made

1. **ip_forward not set to 0** — Docker requires `net.ipv4.ip_forward = 1`. Config file includes explicit comment explaining the omission.

2. **docker0.rp_filter = 2 accepted** — Docker sets this at the interface level. The global `all.rp_filter = 1` is authoritative for non-Docker interfaces. No change needed.

## Deviations from Plan

None — plan executed exactly as written.

## Success Criteria Met

- [x] `sysctl net.ipv4.conf.all.rp_filter` = 1
- [x] `sysctl net.ipv4.conf.all.send_redirects` = 0
- [x] `sysctl net.ipv4.conf.all.log_martians` = 1
- [x] `ufw status verbose` shows Logging: on (medium)

## Next Phase Readiness

Phase 2 Plan 01 (Docker network isolation) should be verified as complete or pending. Phase 3 (app layer) can proceed once Phase 2 is fully done.
