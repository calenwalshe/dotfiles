# Phase 3: Deploy & Verify — Context

**Gathered:** 2026-04-10
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Bring Icecast and Liquidsoap containers up in production (`docker compose up -d`), verify
`<public>0</public>` is active (stream not appearing in public directories), and run a
1-hour unattended test confirming no silence gaps or stream interruptions. Phase complete
when all 8 done criteria in `contract-001.md` pass.

</domain>

<decisions>
## Implementation Decisions

**Deploy command:**
```bash
cd /home/agent/agent-stack
docker compose up -d icecast liquidsoap
```

**Stream verification:**
```bash
curl -sf https://radio.calenwalshe.com/stream.mp3 | head -c 1024 | file -
# Should return: MPEG ADTS, layer III (MP3)
```

**Public listing check:**
- Visit `https://dir.xiph.org/` and search for the stream name
- Alternatively: check Icecast status page — `<public>` field should be `0`
- If stream appears in directory: stop containers, fix `<public>0</public>` in icecast.xml,
  restart

**Restart resilience test:**
```bash
docker compose restart icecast
# Wait 10-15 seconds
curl -sf https://radio.calenwalshe.com/stream.mp3 | head -c 1024
# Liquidsoap should have reconnected automatically
```

**1-hour unattended test:**
- Start stream, walk away
- Check after 1 hour: `curl -sf https://radio.calenwalshe.com/status-json.xsl` should show
  an active source with a current track
- Monitor `docker compose logs --tail=50 liquidsoap icecast` for errors

**Rollback (if needed):**
```bash
docker compose stop icecast liquidsoap
# Revert Caddyfile, reload Caddy
```

### Claude's Discretion

- Whether to use a simple `curl` loop or a proper uptime script for the 1-hour test
- Log rotation setup for Icecast and Liquidsoap (optional for v1)

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/self-hosted-radio/spec.md (section 9 acceptance criteria)
- docs/cortex/specs/self-hosted-radio/gsd-handoff.md (task 7)
- docs/cortex/contracts/self-hosted-radio/contract-001.md (validators)

</canonical_refs>

<specifics>
## Specific Ideas

Contract validators (run these to confirm done):
```bash
# Stream audio
curl -sf https://radio.calenwalshe.com/stream.mp3 | head -c 1024 | file -

# Current track metadata
curl -sf https://radio.calenwalshe.com/status-json.xsl | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d['icestats']['source']['title'])"

# Cam proxy
curl -sf https://radio.calenwalshe.com/cam-url/FIRST_CAM_ID

# Container health
docker compose -f /home/agent/agent-stack/docker-compose.yml ps icecast liquidsoap
```

</specifics>

<deferred>
## Deferred Ideas

- systemd service wrapper for docker compose (auto-start on reboot)
- Alerting on stream death (Telegram notification via existing health-monitor service)
- Listener count logging / analytics
- SSL cert auto-renewal monitoring (Caddy handles this automatically)

</deferred>

---

*Phase: 03-self-hosted-radio*
*Context gathered: 2026-04-10 via /cortex-bridge*
