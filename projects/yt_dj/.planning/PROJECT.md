# Self-Hosted Radio Station

## What This Is

The owner runs a YouTube live stream that received a Community Guidelines warning due to
unmonitored third-party content in a 24/7 autonomous broadcast. Rather than adapt to YouTube's
structural requirement for active monitoring, this project pivots to a self-hosted internet
radio station: streaming a personal DJ-curated MP3 library over Icecast2, paired with a minimal
web page embedding public webcam feeds, running on the owner's agent-stack server.

## Core Value

Full aesthetic and technical control over a 24/7 music stream — no platform dependency, no
Content ID, no active-monitoring requirement — reachable at `https://radio.calenwalshe.com`
for a small private audience.

## Requirements

### Active

- [ ] **RADIO-01**: Icecast2 + Liquidsoap Docker Compose services running on agent-stack network
- [ ] **RADIO-02**: BPM/key-matched MP3 queue via `dj_mixer.py` → M3U playlist → Liquidsoap
- [ ] **RADIO-03**: Minimal dark web frontend at `https://radio.calenwalshe.com` with HTML5 audio player
- [ ] **RADIO-04**: Single rotating webcam embed (Windy API, server-proxied JPEG refresh)
- [ ] **RADIO-05**: Caddy reverse proxy block for `radio.calenwalshe.com` with automatic HTTPS
- [ ] **RADIO-06**: Icecast `<public>0</public>` — not discoverable via public streaming directories
- [ ] **RADIO-07**: 1-hour unattended run without stream interruption

### Out of Scope

- YouTube Live streaming, OBS, Xvfb, FFmpeg video pipeline
- AzuraCast or any managed radio platform
- Multi-user access, scheduled playlist GUI, live DJ hand-off
- Listener analytics beyond Icecast built-in status JSON
- Mobile app or native client
- Music licensing compliance

## Context

**Baseline:** Existing yt_dj codebase with `dj_mixer.py` (BPM/key queue), `src/web/app.py`
(Flask), `config/cameras.json` (30+ cams), `config/track_metadata.json`.

**Target:** Self-hosted radio live at `https://radio.calenwalshe.com` with audio + webcam.

**Ownership:** Contract `docs/cortex/contracts/self-hosted-radio/contract-001.md`.

## Constraints

- Icecast runs on internal port 8100 only — never exposed to host; Caddy proxies it
- `<public>0</public>` mandatory in all Icecast mount configs
- All new Docker services join existing `agent-stack` external network
- Windy API calls go server-side only — browser never touches the API directly
- Dynamic M3U playlist file is the only control interface between `dj_mixer.py` and Liquidsoap in v1
- Do not modify existing `docker-compose.yml` service definitions — add new services only
- Do not modify existing Caddyfile blocks — add new virtual host block only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Icecast internal-only, Caddy proxy | Caddy already owns 80/443 + Let's Encrypt; free HTTPS | radio.calenwalshe.com with valid TLS cert |
| Liquidsoap TCP push, no PulseAudio | File-based playlist needs no sound card; cleaner server setup | moul/icecast + savonet/liquidsoap:2.2 |
| Extend web/app.py for cam proxy | Already exists; no justification for separate sidecar | /cam-url/<cam_id> route in Flask |
| Dynamic M3U file, not harbor HTTP | Simpler than a new control protocol for v1 | dj_mixer.py writes /queue/playlist.m3u |
| AzuraCast rejected | 10-container overhead for features not needed | Bare two-container stack |
