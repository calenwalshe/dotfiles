# GSD Handoff: self-hosted-radio

**Slug:** self-hosted-radio
**Contract:** docs/cortex/contracts/self-hosted-radio/contract-001.md
**Status:** approved

---

## Objective

Deploy a self-hosted internet radio station on the agent-stack box: Icecast2 + Liquidsoap as
Docker Compose services, BPM/key-matched MP3 playout via the existing dj_mixer.py, and a
minimal dark web frontend at `https://radio.calenwalshe.com` with an HTML5 audio player and
rotating public webcam embed. No YouTube dependency. Small private audience only.

---

## Deliverables

- `agent-stack/icecast/icecast.xml` — Icecast2 server config (new)
- `agent-stack/liquidsoap/radio.liq` — Liquidsoap playout script (new)
- `agent-stack/docker-compose.yml` — add icecast + liquidsoap services
- `agent-stack/caddy/Caddyfile` — add radio.calenwalshe.com block
- `src/web/app.py` — add `/cam-url/<cam_id>` Windy proxy route
- `src/web/static/radio.html` — minimal dark radio frontend (new)
- `src/dj_mixer.py` — add M3U playlist write after queue build

---

## Tasks

1. **Icecast service**
   - Add `icecast` to `agent-stack/docker-compose.yml`:
     ```yaml
     icecast:
       image: moul/icecast
       container_name: icecast
       restart: unless-stopped
       environment:
         ICECAST_SOURCE_PASSWORD: ${ICECAST_SOURCE_PASSWORD}
         ICECAST_ADMIN_PASSWORD: ${ICECAST_ADMIN_PASSWORD}
         ICECAST_RELAY_PASSWORD: ${ICECAST_RELAY_PASSWORD}
       volumes:
         - ./icecast/icecast.xml:/etc/icecast2/icecast.xml:ro
       networks:
         - agent-stack
       healthcheck:
         test: ["CMD", "curl", "-sf", "http://localhost:8000/status-json.xsl"]
         interval: 30s
         timeout: 5s
         retries: 3
     ```
     Note: `moul/icecast` binds internally on 8000; Caddy proxy uses service name `icecast:8000`.
   - Write `agent-stack/icecast/icecast.xml` with `<public>0</public>` on the `/stream.mp3` mount.

2. **Liquidsoap service**
   - Add `liquidsoap` to `docker-compose.yml` with `depends_on: icecast`, music volume mount, and a shared `queue` volume for the playlist file.
   - Write `agent-stack/liquidsoap/radio.liq`:
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

3. **Smart queue wiring**
   - In `src/dj_mixer.py`, after building the ordered track list, write it as `/queue/playlist.m3u` (absolute paths, one track per line with `#EXTM3U` header).
   - The queue volume is shared with the Liquidsoap container.

4. **Caddy block**
   - Append to `agent-stack/caddy/Caddyfile`:
     ```
     radio.calenwalshe.com {
       handle /stream.mp3 {
         reverse_proxy icecast:8000
       }
       handle /status-json.xsl {
         reverse_proxy icecast:8000
       }
       handle /cam-url/* {
         reverse_proxy web-app:5000
       }
       handle {
         root * /srv/radio
         file_server
       }
     }
     ```
   - Alternatively route all non-stream traffic to Flask app if static file serving is simpler via Flask.
   - Run `caddy validate` then `caddy reload`.

5. **Cam proxy endpoint**
   - In `src/web/app.py`, add:
     ```python
     @app.route('/cam-url/<int:cam_id>')
     def cam_url(cam_id):
         api_key = load_windy_api_key()
         resp = httpx.get(
             f"https://api.windy.com/webcams/api/v3/webcams/{cam_id}",
             headers={"x-windy-api-key": api_key}
         )
         resp.raise_for_status()
         data = resp.json()
         return jsonify({"url": data["webcams"][0]["images"]["current"]["preview"]})
     ```
   - Log each call with a counter for rate-limit monitoring.

6. **Web frontend**
   - Write `src/web/static/radio.html`:
     - Background: `#0a0a0a` (near-black)
     - HTML5 `<audio controls autoplay>` pointing at `https://radio.calenwalshe.com/stream.mp3`
     - `<img id="cam">` updated every 60s via `setInterval` fetching `/cam-url/{cam_id}`
     - Signed URL refreshed every 8 minutes (separate interval, before 10-min expiry)
     - Current track from `fetch('/status-json.xsl')` polled every 15s — show artist + title
     - `onerror` on `<img>`: hide and show "no cam" placeholder

7. **Deploy and verify**
   - `cd /home/agent/agent-stack && docker compose up -d icecast liquidsoap`
   - Confirm stream: `curl -I https://radio.calenwalshe.com/stream.mp3`
   - Confirm Icecast not public: check `https://dir.xiph.org/` for the stream name
   - Run 1-hour unattended test

---

## Acceptance Criteria

- [ ] `https://radio.calenwalshe.com/stream.mp3` streams MP3 audio continuously from the owner's library
- [ ] Stream uses BPM/key-matched queue — produced by `dj_mixer.py`, loaded by Liquidsoap via M3U
- [ ] Web page at `https://radio.calenwalshe.com` displays audio player and single webcam embed
- [ ] Webcam JPEG refreshes every 60 seconds without page reload
- [ ] Icecast `<public>0</public>` confirmed — stream not discoverable via icecast.org or shoutcast directories
- [ ] Liquidsoap reconnects automatically if Icecast container restarts (tested manually)
- [ ] Stream runs 1 hour unattended without interruption or silence gap
- [ ] HTTPS cert valid — browser shows no security warnings
