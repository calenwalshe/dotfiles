# Phase 1: SSH & Authentication Hardening - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Close the two SSH attack vectors (password auth + root login), identify and resolve port 2022, and install intrusion detection (fail2ban) and audit logging (auditd). This phase must complete before any network-level changes — key auth must be confirmed working before password auth is disabled.

</domain>

<decisions>
## Implementation Decisions

### SSH config file split
`PermitRootLogin` and `PasswordAuthentication` live in two separate files:
- `/etc/ssh/sshd_config.d/50-cloud-init.conf` — sets `PasswordAuthentication` (cloud-init override)
- `/etc/ssh/sshd_config` — sets `PermitRootLogin`, `X11Forwarding`, `GatewayPorts`, `LogLevel`

Edit both files; the cloud-init override takes precedence for PasswordAuthentication.

### Key auth verification first
Run `ssh -o PasswordAuthentication=no agent@149.28.12.120` from a **separate terminal** before saving sshd config changes. This must succeed before PasswordAuthentication is disabled — if it fails, stop and debug the key setup first.

### fail2ban banaction
Use `banaction = ufw` in `/etc/fail2ban/jail.local` so bans go through UFW (consistent with existing firewall management). Cover both ports 22 and 2022 in the sshd jail definition even before port 2022 is identified — fail2ban silently ignores ports with no listener.

### Port 2022 resolution
If port 2022 belongs to an internal service that should not be public: add a UFW rule restricting it to 127.0.0.1 or the Docker bridge CIDR, or close the listener. If no legitimate process owns it, close it. Either way, document the finding before proceeding to Phase 2.

### Claude's Discretion

- Exact `auditd.rules` configuration (default rules are sufficient for this spec)
- Whether to also install `logwatch` (optional dependency per spec)
- Order of fail2ban vs auditd installation (independent, can be sequential or parallel)

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/server-hardening/spec.md — Section 8 Sequencing steps 1–5
- docs/cortex/specs/server-hardening/gsd-handoff.md — Tasks 1–8
- docs/cortex/contracts/server-hardening/contract-001.md — Done Criteria 1–5
- docs/cortex/research/server-hardening/concept-20260414T033547Z.md — §[q1+q2+q3] SSH + §[q6] fail2ban/auditd
- docs/cortex/clarify/server-hardening/20260414T032326Z-clarify-brief.md

</canonical_refs>

<specifics>
## Specific Ideas

**SSH hardening commands:**
```bash
# Verify key auth first (run from separate terminal)
ssh -o PasswordAuthentication=no agent@149.28.12.120

# Edit cloud-init override
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config.d/50-cloud-init.conf

# Edit main sshd_config
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
# Also set: X11Forwarding no, GatewayPorts no, LogLevel VERBOSE

# Restart and verify
sudo systemctl restart sshd
sshd -T | grep -E "passwordauthentication|permitrootlogin|x11forwarding|gatewayports|loglevel"
```

**fail2ban jail.local:**
```ini
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
banaction = ufw

[sshd]
enabled = true
port    = 22,2022
logpath = /var/log/auth.log
```

**Port 2022 identification:**
```bash
sudo ss -tlnp | grep 2022
sudo lsof -i :2022
```

</specifics>

<deferred>
## Deferred Ideas

- Docker user namespace remapping (risk of breaking 40-container compose stack)
- AppArmor/seccomp custom profiles beyond Docker CE defaults
- CrowdSec (RAM overhead not justified)
- Content-Security-Policy headers
- Greenbone/OpenVAS

</deferred>

---

*Phase: 01-server-hardening-ssh*
*Context gathered: 2026-04-14 via /cortex-bridge*
