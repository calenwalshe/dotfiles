# Phase 2: Network Exposure Closure - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Eliminate the Docker UFW bypass by rebinding all internal service ports from `0.0.0.0:PORT:PORT` to `127.0.0.1:PORT:PORT` in all agent-stack docker-compose files. Apply sysctl network hardening and upgrade UFW logging to medium. Phase 1 (SSH hardened, fail2ban active) must be complete first so there is a brute-force defense in place during any restart operations.

</domain>

<decisions>
## Implementation Decisions

### 127.0.0.1 rebind approach (not DOCKER-USER iptables)
Docker port rebinding in docker-compose is the chosen approach over DOCKER-USER iptables DROP rules. Rationale: iptables rules are lost on reboot without iptables-persistent; docker-compose config changes survive container and host restarts. Editing compose files and running `docker compose up -d` is the durable fix.

### Caddy stays on 0.0.0.0
Caddy's `:80` and `:443` bindings MUST remain on `0.0.0.0` — those are the public-facing ports Cloudflare sends traffic to. Every other service moves to `127.0.0.1`.

### One compose file at a time
Edit and restart one compose file at a time. After each `docker compose up -d`, run:
```bash
curl -sI https://radio.calenwalshe.com/stream
```
If response is not 200/302 within 30 seconds, rollback that file (`git checkout <file> && docker compose up -d`) before moving to the next.

### sysctl drop file
Create `/etc/sysctl.d/99-hardening.conf` — never edit `/etc/sysctl.conf` directly. The drop file approach survives OS upgrades. Do NOT set `net.ipv4.ip_forward = 0` — Docker requires it = 1.

### rp_filter=1 and Docker networking
Docker sets `net.ipv4.conf.docker0.rp_filter=0` independently. After running `sudo sysctl --system`, verify the Docker bridge retains its value:
```bash
sysctl net.ipv4.conf.docker0.rp_filter
# Should still be 0 (Docker manages this interface)
```

### Claude's Discretion

- Which docker-compose files exist in `/home/agent/agent-stack/` (must discover at runtime with `ls *.yml`)
- Order of compose file updates (should prioritize non-radio services first)
- Whether to batch compose files that belong to the same `docker compose` project

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/server-hardening/spec.md — Section 8 Sequencing steps 6–8
- docs/cortex/specs/server-hardening/gsd-handoff.md — Tasks 9–15
- docs/cortex/contracts/server-hardening/contract-001.md — Done Criteria 6–9
- docs/cortex/research/server-hardening/concept-20260414T033547Z.md — §[q5] Docker UFW bypass + §[q4] sysctl
- docs/cortex/clarify/server-hardening/20260414T032326Z-clarify-brief.md

</canonical_refs>

<specifics>
## Specific Ideas

**Discover all 0.0.0.0 bindings:**
```bash
grep -rn "0.0.0.0:" /home/agent/agent-stack/*.yml
```

**sysctl hardening file content:**
```ini
# /etc/sysctl.d/99-hardening.conf
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_rfc1337 = 1
# NOTE: Do NOT set net.ipv4.ip_forward = 0 — Docker requires it = 1
```

**Verify nmap after rebind:**
```bash
nmap -p 9090,9091,9092,9095,9098,9099 149.28.12.120
# All should be filtered or closed
```

**UFW logging:**
```bash
sudo ufw logging medium
ufw status verbose | grep Logging
```

</specifics>

<deferred>
## Deferred Ideas

- DOCKER-USER iptables DROP rule approach (rejected: not durable)
- Docker user namespace remapping (rejected: risk to 40-container stack)
- iptables-persistent installation (not needed with rebind approach)

</deferred>

---

*Phase: 02-server-hardening-network*
*Context gathered: 2026-04-14 via /cortex-bridge*
