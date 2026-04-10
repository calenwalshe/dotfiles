# Contract: self-hosted-radio — execute

**ID:** self-hosted-radio-001
**Slug:** self-hosted-radio
**Phase:** execute
**Created:** 20260410T130000Z
**Status:** approved
**Repair Budget:** max_repair_contracts: 3, cooldown_between_repairs: 1

---

## Objective

Deploy a self-hosted internet radio station on the agent-stack box: Icecast2 + Liquidsoap in
Docker Compose, BPM/key-matched playout via dj_mixer.py, and a minimal dark web frontend at
`https://radio.calenwalshe.com` with HTML5 audio player and rotating webcam embed.

---

## Deliverables

- `agent-stack/icecast/icecast.xml` — Icecast2 server config
- `agent-stack/liquidsoap/radio.liq` — Liquidsoap playout script
- Updated `agent-stack/docker-compose.yml` — icecast + liquidsoap services added
- Updated `agent-stack/caddy/Caddyfile` — radio.calenwalshe.com block added
- Updated `src/web/app.py` — /cam-url/<cam_id> route added
- `src/web/static/radio.html` — minimal dark radio frontend
- Updated `src/dj_mixer.py` — M3U playlist write after queue build

---

## Scope

### In Scope
- Icecast2 + Liquidsoap Docker services on agent-stack network
- BPM/key smart queue via dj_mixer.py → M3U playlist file
- Minimal dark frontend: audio player + webcam embed
- Windy API cam proxy endpoint (server-side, CORS-safe)
- Caddy reverse proxy block for radio.calenwalshe.com
- Icecast internal-only on port 8000 (moul/icecast default), proxied by Caddy
- `<public>0</public>` Icecast config — no public directory listing

### Out of Scope
- YouTube Live streaming, OBS, Xvfb, FFmpeg video pipeline
- AzuraCast, multi-user access, scheduled playlist GUI
- Listener analytics beyond Icecast built-in status JSON
- Music licensing compliance

---

## Write Roots

- `agent-stack/icecast/` (new directory)
- `agent-stack/liquidsoap/` (new directory)
- `agent-stack/docker-compose.yml` (add services only)
- `agent-stack/caddy/Caddyfile` (add block only)
- `src/web/app.py`
- `src/web/static/`
- `src/dj_mixer.py`

---

## Done Criteria

- [ ] `https://radio.calenwalshe.com/stream.mp3` streams MP3 audio continuously from the owner's library
- [ ] Stream uses BPM/key-matched queue — produced by `dj_mixer.py`, loaded by Liquidsoap via M3U
- [ ] Web page at `https://radio.calenwalshe.com` displays audio player and single webcam embed
- [ ] Webcam JPEG refreshes every 60 seconds without page reload
- [ ] Icecast `<public>0</public>` confirmed — stream not discoverable via icecast.org or shoutcast directories
- [ ] Liquidsoap reconnects automatically if Icecast container restarts (tested manually)
- [ ] Stream runs 1 hour unattended without interruption or silence gap
- [ ] HTTPS cert valid — browser shows no security warnings

---

## Validators

- [ ] [external] `curl -sf https://radio.calenwalshe.com/stream.mp3 | head -c 1024 | file -` returns `MPEG` or `Audio`
- [ ] [external] `curl -sf https://radio.calenwalshe.com/status-json.xsl | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['icestats']['source']['title'])"` prints a track title
- [ ] [external] `curl -sf https://radio.calenwalshe.com/cam-url/$(python3 -c "import json; c=json.load(open('config/cameras.json')); print(c[0].get('id',''))")` returns a JSON object with a `url` key
- [ ] [external] `docker compose -f /home/agent/agent-stack/docker-compose.yml ps icecast liquidsoap` shows both as `running`
- [ ] [judgment] Web page looks minimal and dark — audio plays on load, webcam image visible and refreshes
- [ ] [judgment] Icecast directory check confirms stream is NOT listed publicly

---

## Eval Plan

docs/cortex/evals/self-hosted-radio/eval-plan.md (pending)

---

## Approvals

- [x] Contract approval
- [ ] Evals approval

---

## Completion Promise

<!-- CORTEX_PROMISE: self-hosted-radio-001 COMPLETE -->

---

## Failed Approaches

<!-- Initial contract — no prior attempts. -->

---

## Why Previous Approach Failed

N/A — initial contract

---

## Rollback Hints

- `docker compose -f /home/agent/agent-stack/docker-compose.yml stop icecast liquidsoap`
- Remove `icecast` and `liquidsoap` service blocks from `agent-stack/docker-compose.yml`
- Remove `radio.calenwalshe.com` block from `agent-stack/caddy/Caddyfile`, then `caddy reload`
- Revert `src/web/app.py` to remove `/cam-url` route
- Revert `src/dj_mixer.py` to remove M3U write
- Delete `agent-stack/icecast/`, `agent-stack/liquidsoap/`, `src/web/static/radio.html`

---

## Repair Budget

**max_repair_contracts:** 3
**cooldown_between_repairs:** 1
