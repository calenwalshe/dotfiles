# Spec: self-hosted-radio

**Slug:** self-hosted-radio
**Timestamp:** 20260410T130000Z
**Status:** draft

---

## 1. Problem

The owner runs a YouTube live stream ("Live Views From Around the World") that was halted and
received a first Community Guidelines warning on 2026-04-09 due to unmonitored third-party
content in a live stream. The platform's policy requires active monitoring of all live
broadcasts — structurally incompatible with a 24/7 autonomous stream. Rather than adapt to
YouTube's constraints, the owner is pivoting to a self-hosted internet radio station: streaming
their personal DJ-curated MP3 library over Icecast2, paired with a minimal web page embedding
public webcam feeds, running on their own server for a small private audience. No platform
dependency, full aesthetic control.

---

## 2. Scope

### In Scope

- Icecast2 + Liquidsoap as Docker Compose services joined to the existing `agent-stack` network
- BPM/key smart queue via existing `dj_mixer.py` writing a dynamic M3U playlist file
- Minimal dark web frontend: HTML5 `<audio>` player + single rotating webcam embed
- Server-side `/cam-url/<cam_id>` proxy endpoint extending `src/web/app.py` (avoids Windy API CORS + hides API key)
- Caddy reverse proxy block for `radio.calenwalshe.com` — HTTPS via Let's Encrypt (automatic)
- Icecast internal on port 8100, not exposed to host directly — accessed via Caddy only
- `<public>0</public>` in Icecast mount config — stream not listed in public directories
- Webcam feed rotation using `config/cameras.json` (existing 30+ cam database)

### Out of Scope

- YouTube Live streaming (pivot away — complete)
- OBS, Xvfb, frame_mixer, solar_scorer, FFmpeg video pipeline (all dropped)
- AzuraCast or any managed radio platform
- Multi-user access, scheduled playlist GUI, live DJ hand-off
- Listener analytics beyond Icecast's built-in `/status-json.xsl`
- Mobile app or native client
- Music licensing compliance (owner's informed choice)
- Simultaneous multi-platform streaming

---

## 3. Architecture Decision

**Chosen approach:** Icecast2 (HTTP audio server) + Liquidsoap (encoder/playout) as two Docker
Compose services on the existing `agent-stack` network. Liquidsoap reads from a dynamic
`/queue/playlist.m3u` file written by `dj_mixer.py`, encodes to MP3 128kbps, and pushes via
TCP to Icecast (`output.icecast`). The existing `src/web/app.py` Flask app is extended with a
`/cam-url/<cam_id>` proxy endpoint for Windy API calls. Static `radio.html` frontend served
directly by Caddy. Caddy proxies `radio.calenwalshe.com` to Icecast (stream + status) and the
Flask app (cam proxy).

**Rationale:** Icecast's TCP push (`output.icecast`) requires no PulseAudio or ALSA for a
file-based playlist setup — cleanest possible server deployment. Liquidsoap is already in the
codebase and configured; adapting is trivial. Caddy already owns 80/443 with automatic Let's
Encrypt — adding a virtual host is one Caddyfile block. Extending `web/app.py` reuses existing
infrastructure instead of introducing a new sidecar service. The dynamic playlist file pattern
decouples `dj_mixer.py` from Liquidsoap with no new control protocol.

### Alternatives Considered

- **Nginx reverse proxy:** Caddy already running and handles certs automatically. Nginx would be
  a redundant second proxy for no benefit.
- **AzuraCast:** 10-container stack (~1-2 GB images, 300-500 MB RAM idle) for a fixed-theme UI
  and multi-user features the owner doesn't need. Over-engineering.
- **Liquidsoap harbor HTTP for playlist control:** More complex than a shared playlist file for
  v1. Revisit if real-time track control is needed later.
- **New Python sidecar for cam proxy:** `src/web/app.py` already exists in the repo. No
  justification for a separate service.
- **Port 8000 for Icecast:** Occupied by `magmalab-api` on the agent-stack box. Port 8100 is
  free and within the internal-only network.

---

## 4. Interfaces

- **Icecast2 HTTP** (internal, `icecast:8100`): stream at `/stream.mp3`, status at
  `/status-json.xsl`. Read by Caddy (proxy) and frontend JavaScript (metadata).
- **Caddy Caddyfile** (`/home/agent/agent-stack/caddy/Caddyfile`): new
  `radio.calenwalshe.com` block. Write target — update in agent-stack repo.
- **`agent-stack/docker-compose.yml`**: add `icecast` and `liquidsoap` services. Write target.
- **`agent-stack/icecast/icecast.xml`**: Icecast configuration (passwords, mount, `<public>0</public>`). Write target — new file.
- **`agent-stack/liquidsoap/radio.liq`**: Liquidsoap script (playlist, encoder, output). Write target — new file.
- **`/queue/playlist.m3u`** (Docker volume, shared): written by `dj_mixer.py`, read by
  Liquidsoap. Interface between the smart queue and the playout engine.
- **`src/web/app.py`** (extend): add `/cam-url/<cam_id>` route. Read Windy v3 API, return
  signed JPEG URL. Write target.
- **`src/web/static/radio.html`**: new static frontend. Write target.
- **Windy Webcams API v3** (external, read): `GET /webcams/api/v3/webcams/{id}` returns signed
  JPEG URL. Called server-side only — API key never exposed to browser.
- **`config/cameras.json`** (read): existing 30+ cam database used by cam proxy for cam selection.
- **`config/webcams.json`** (read): Windy API key stored here.

---

## 5. Dependencies

- **`moul/icecast`** Docker image — Icecast2 audio streaming server, env-var configurable
- **`savonet/liquidsoap:2.2`** Docker image — Liquidsoap 2.x encoder and playout engine
- **`agent-stack` Docker network** (external) — existing shared network all services join
- **Caddy v2** — existing reverse proxy, already running on ports 80/443
- **`src/dj_mixer.py`** — existing BPM/key-matched queue builder; needs M3U write added
- **`src/web/app.py`** — existing Flask app; needs `/cam-url` route added
- **`config/cameras.json`** — existing 30+ camera database
- **`config/track_metadata.json`** — per-track BPM/key/energy from offline essentia analysis
- **`httpx`** — already installed; used for Windy API calls in cam proxy
- **Windy Webcams API v3 key** — already stored in `config/webcams.json`

---

## 6. Risks

- **Liquidsoap startup race** (starts before Icecast is ready) — Mitigation: `depends_on: icecast` in Compose + Liquidsoap's built-in `output.icecast` reconnect loop retries automatically; add a `fallback(single("/music/silence.ogg"), ...)` safety track so Liquidsoap never dies waiting.
- **Empty playlist crash** (`/queue/playlist.m3u` missing or empty on start) — Mitigation: `dj_mixer.py` writes the playlist before Liquidsoap container starts; Compose healthcheck on Liquidsoap waits for playlist file.
- **Windy API rate limit** (1000 req/day on free tier) — Mitigation: log each `/cam-url` call with a counter; at single-cam 8-min refresh the load is ~180/day, well within limit; alert if approaching ceiling.
- **Icecast public listing** (default ON) — Mitigation: `<public>0</public>` set in `icecast.xml` from day one; verified as part of acceptance criteria.
- **Caddy config conflict** — Mitigation: validate with `caddy validate --config Caddyfile` before `caddy reload`; keep a `.bak` of the current Caddyfile.
- **Liquidsoap 2.x syntax differences** — Mitigation: pin image to `savonet/liquidsoap:2.2`; run `liquidsoap --check radio.liq` inside container before starting.

---

## 7. Sequencing

1. **Icecast2 service** — Add `icecast` to `agent-stack/docker-compose.yml` with `icecast.xml`
   config. Checkpoint: `curl http://localhost:8100/status-json.xsl` returns JSON.

2. **Liquidsoap service** — Add `liquidsoap` to Compose with `radio.liq` and music volume.
   Write initial `radio.liq` with a test playlist. Checkpoint: stream audible at
   `http://localhost:8100/stream.mp3`.

3. **Smart queue wiring** — Update `dj_mixer.py` to write `/queue/playlist.m3u` after each
   queue build. Switch Liquidsoap to `playlist.reloadable("/queue/playlist.m3u")`. Checkpoint:
   playlist file populated with BPM/key-ordered tracks; Liquidsoap picks them up.

4. **Caddy block** — Add `radio.calenwalshe.com` block to Caddyfile proxying to `icecast:8100`.
   Reload Caddy. Checkpoint: `https://radio.calenwalshe.com/stream.mp3` serves the stream with
   valid TLS cert.

5. **Cam proxy endpoint** — Add `/cam-url/<cam_id>` to `src/web/app.py`. Checkpoint:
   `curl https://radio.calenwalshe.com/cam-url/123` returns a fresh Windy JPEG URL.

6. **Web frontend** — Write `src/web/static/radio.html`: dark minimal page, `<audio>` element,
   img-tag webcam with 60s setInterval, metadata from `/status-json.xsl`. Checkpoint: page
   loads in browser, audio plays, webcam image updates every 60s.

7. **Security & hardening** — Confirm `<public>0</public>` active; verify stream not in
   Icecast directory. Run 1-hour unattended test. Checkpoint: all acceptance criteria pass.

---

## 8. Tasks

- [ ] Add `icecast` service to `agent-stack/docker-compose.yml` (image: `moul/icecast`, internal port 8100, `agent-stack` network)
- [ ] Write `agent-stack/icecast/icecast.xml` (passwords, mount `/stream.mp3`, `<public>0</public>`, bitrate 128k)
- [ ] Add `liquidsoap` service to `agent-stack/docker-compose.yml` (image: `savonet/liquidsoap:2.2`, depends_on: icecast, music + queue volumes)
- [ ] Write `agent-stack/liquidsoap/radio.liq` (playlist.reloadable, output.icecast TCP push, fallback silence track)
- [ ] Update `src/dj_mixer.py` to write `/queue/playlist.m3u` after queue build
- [ ] Add `/cam-url/<cam_id>` route to `src/web/app.py` (httpx call to Windy v3 API, return signed URL, log call count)
- [ ] Write `src/web/static/radio.html` (dark minimal, `<audio>` → stream, img-tag + setInterval 60s, metadata poll from Icecast status JSON)
- [ ] Add `radio.calenwalshe.com` block to `agent-stack/caddy/Caddyfile` (reverse_proxy icecast:8100 for `/stream.mp3` and `/status-json.xsl`; proxy to Flask app for `/cam-url`)
- [ ] Run `caddy validate` then `caddy reload`
- [ ] Start Icecast + Liquidsoap via `docker compose up -d icecast liquidsoap`
- [ ] Verify `<public>0</public>` by checking Icecast directory lookup
- [ ] 1-hour unattended run test — confirm no stream drop, webcam refreshes, metadata updates

---

## 9. Acceptance Criteria

- [ ] `https://radio.calenwalshe.com/stream.mp3` streams MP3 audio continuously from the owner's library
- [ ] Stream uses BPM/key-matched queue — produced by `dj_mixer.py`, loaded by Liquidsoap via M3U
- [ ] Web page at `https://radio.calenwalshe.com` displays audio player and single webcam embed
- [ ] Webcam JPEG refreshes every 60 seconds without page reload
- [ ] Icecast `<public>0</public>` confirmed — stream not discoverable via icecast.org or shoutcast directories
- [ ] Liquidsoap reconnects automatically if Icecast container restarts (tested manually)
- [ ] Stream runs 1 hour unattended without interruption or silence gap
- [ ] HTTPS cert valid — browser shows no security warnings
