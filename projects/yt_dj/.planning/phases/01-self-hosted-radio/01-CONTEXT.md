# Phase 1: Services — Context

**Gathered:** 2026-04-10
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Add `icecast` and `liquidsoap` services to `agent-stack/docker-compose.yml`, write their
configs, and wire `dj_mixer.py` to produce a `/queue/playlist.m3u` file that Liquidsoap reads.
Phase is complete when `curl http://icecast:8100/status-json.xsl` returns JSON with an active
source, and `dj_mixer.py` outputs a populated M3U playlist.

</domain>

<decisions>
## Implementation Decisions

**Icecast image:** `moul/icecast` — community image, env-var driven, well-maintained. Source
password, admin password, and relay password passed as environment variables. Config file
mounted at `/etc/icecast2/icecast.xml`.

**Liquidsoap image:** `savonet/liquidsoap:2.2` — official upstream, pin to 2.2 to avoid
syntax drift. Liquidsoap 2.x uses `%mp3(bitrate=128)` not `%mp3.fxp`.

**No PulseAudio:** Liquidsoap `output.icecast` is a pure TCP push. Do not mount `/dev/snd`
or use `--privileged`. File-based playlist needs no sound card.

**Port:** `moul/icecast` binds internally on port 8000 (its default). Caddy will proxy to
`icecast:8000`. Do NOT use 8100 externally — the port mapping in docker-compose.yml should
NOT expose 8000 to the host (internal-only via Docker network).

**Startup race mitigation:** `depends_on: icecast` in Compose + Liquidsoap's built-in
`output.icecast` reconnect loop. Add `fallback([radio, blank()])` in `radio.liq` so
Liquidsoap never dies on an empty playlist or lost connection.

**Smart queue wiring:** `dj_mixer.py` already builds a BPM/key-ordered track list. After
building, write it as `/queue/playlist.m3u` with `#EXTM3U` header and absolute paths to MP3
files. Liquidsoap reads this with `playlist.reloadable("/queue/playlist.m3u")`. The
`/queue/` path is a Docker volume shared between the `liquidsoap` container and any container
running `dj_mixer.py` (or the host if running dj_mixer.py directly).

**Icecast public listing:** `<public>0</public>` in the mount config inside `icecast.xml`.
Set this from day one — do not leave it as a Phase 3 afterthought.

**Passwords:** Store in `agent-stack/.env` as `ICECAST_SOURCE_PASSWORD`, `ICECAST_ADMIN_PASSWORD`,
`ICECAST_RELAY_PASSWORD`. Reference via `${VAR}` in docker-compose.yml.

### Claude's Discretion

- Exact Icecast XML structure (maxlisteners, limits, logging verbosity)
- Whether to expose a healthcheck endpoint via Icecast's `/status-json.xsl` or a custom script
- Volume naming for the shared `/queue/` path
- Whether `dj_mixer.py` is invoked manually first or via a one-shot container/script

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/self-hosted-radio/spec.md (sections 3, 5, 6, 7)
- docs/cortex/specs/self-hosted-radio/gsd-handoff.md (tasks 1–3)
- docs/cortex/contracts/self-hosted-radio/contract-001.md
- docs/cortex/research/self-hosted-radio/concept-20260410T123000Z.md (q5 findings)
- docs/cortex/clarify/self-hosted-radio/20260410T120000Z-clarify-brief.md

</canonical_refs>

<specifics>
## Specific Ideas

From research (q5 — Icecast + Liquidsoap Docker):
- Standard `radio.liq` pattern:
  ```
  settings.server.telnet.set(false)
  radio = playlist.reloadable("/queue/playlist.m3u")
  radio = fallback([radio, blank()])
  output.icecast(%mp3(bitrate=128),
    host="icecast", port=8000,
    password=getenv("ICECAST_SOURCE_PASSWORD"),
    mount="/stream.mp3",
    name="radio", description="",
    public=false,
    radio)
  ```
- Run `liquidsoap --check radio.liq` inside the container before starting to catch syntax errors
- `dj_mixer.py` already in `src/` — add M3U write at end of `build_queue()` or equivalent method

</specifics>

<deferred>
## Deferred Ideas

- Liquidsoap harbor HTTP for runtime track control (v2)
- Multiple mount points / bitrate variants (v2)
- Listener count monitoring beyond Icecast status JSON (v2)
- AzuraCast GUI (explicitly rejected — not deferred)

</deferred>

---

*Phase: 01-self-hosted-radio*
*Context gathered: 2026-04-10 via /cortex-bridge*
