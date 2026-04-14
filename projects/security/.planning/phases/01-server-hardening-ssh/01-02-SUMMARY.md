---
phase: 01-server-hardening-ssh
plan: "01-02"
subsystem: infra
tags: [fail2ban, auditd, ufw, ssh, brute-force-protection, audit-logging]

requires:
  - phase: 01-server-hardening-ssh
    provides: plan 01-01 (sshd hardening baseline)

provides:
  - fail2ban installed with sshd jail covering ports 22 and 2022
  - banaction=ufw integration (UFW is the ban backend)
  - bantime=3600, findtime=600, maxretry=5 policy active
  - auditd installed and running for kernel-level audit logging

affects:
  - phase 2 (Docker hardening) — audit trail already running
  - pentest AC — fail2ban active and banning attackers before pentest

tech-stack:
  added: [fail2ban 1.0.2, auditd 3.1.2, whois, libauparse0t64]
  patterns: [UFW-integrated banning via banaction=ufw, /etc/fail2ban/jail.local overrides defaults]

key-files:
  created: [/etc/fail2ban/jail.local]
  modified: []

key-decisions:
  - "banaction=ufw chosen over iptables (UFW already active, consistent with existing firewall management)"
  - "Port coverage: 22,2022 — matches sshd listening ports (standard + alternate)"
  - "Default auditd rules retained (no custom rules added) — base audit trail is sufficient for Phase 1"

patterns-established:
  - "fail2ban jail.local: always override defaults in jail.local, never modify jail.conf"

duration: 2min
completed: 2026-04-14
---

# Phase 1 Plan 02: fail2ban + auditd Summary

**fail2ban sshd jail (ports 22+2022, UFW backend, banning 8 live IPs within minutes) and auditd kernel audit logging both active on first boot**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-14T04:47:08Z
- **Completed:** 2026-04-14T04:48:55Z
- **Tasks:** 7
- **Files modified:** 1 (system: /etc/fail2ban/jail.local)

## Accomplishments

- fail2ban installed and immediately operational — sshd jail detected 47 failed attempts and banned 8 IPs before verification ran
- /etc/fail2ban/jail.local created with UFW backend, covering both SSH ports (22 and 2022), 5 retry limit, 1-hour ban duration
- auditd installed and active, providing kernel-level syscall audit trail for all subsequent hardening steps

## Task Commits

Tasks were committed as a single atomic unit (system-level changes in /etc, outside git repo boundary):

1. **Install fail2ban** - system package install
2. **Create /etc/fail2ban/jail.local** - sshd jail config with UFW banaction
3. **Enable and start fail2ban** - `systemctl enable --now fail2ban`
4. **Verify fail2ban** - `active`; `fail2ban-client status sshd` shows 8 banned IPs
5. **Install auditd** - system package install
6. **Enable and start auditd** - `systemctl enable --now auditd`
7. **Verify auditd** - `active`

**Plan metadata commit:** see git log — `chore(01-02): install fail2ban (sshd jail) and auditd`

## Files Created/Modified

- `/etc/fail2ban/jail.local` - sshd jail: ports 22+2022, bantime=3600, findtime=600, maxretry=5, banaction=ufw

## Verification Output

```
$ systemctl is-active fail2ban
active

$ sudo fail2ban-client status sshd
Status for the jail: sshd
|- Filter
|  |- Currently failed:  4
|  |- Total failed:      47
|  `- Journal matches:   _SYSTEMD_UNIT=sshd.service + _COMM=sshd
`- Actions
   |- Currently banned:  8
   |- Total banned:      8
   `- Banned IP list:    2.57.122.191 2.57.121.17 2.57.122.199 80.94.92.186
                         45.148.10.157 80.94.92.187 80.94.92.177 2.57.121.86

$ systemctl is-active auditd
active
```

## Decisions Made

- `banaction = ufw` retained as specified — UFW is the active firewall, using it as the ban backend keeps the firewall state consistent and avoids mixing iptables-direct rules with UFW-managed rules.
- Port list `22,2022` matches the two ports sshd was configured to listen on in plan 01-01.
- auditd left with default rules — no custom audit rules added in this plan. Custom rules (e.g., watch /etc/passwd, /etc/sudoers) are a Phase 1 extension if needed.

## Deviations from Plan

None — plan executed exactly as written. The Write tool was blocked by permissions on /etc/fail2ban/jail.local (expected, root-owned directory) so `sudo tee` was used instead — this is a tool limitation, not a plan deviation.

## Issues Encountered

None. fail2ban started immediately and picked up the jail.local config on first launch. auditd likewise required no intervention.

## Next Phase Readiness

- fail2ban sshd jail active and already banning live brute-force attempts
- auditd providing audit trail before Docker hardening begins
- Phase 2 (Docker UFW bypass fix) can proceed immediately
- No blockers

---
*Phase: 01-server-hardening-ssh*
*Completed: 2026-04-14*
