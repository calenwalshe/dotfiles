# Phase 2: Routing & Frontend — Context

**Gathered:** 2026-04-10
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Add `radio.calenwalshe.com` Caddyfile block (reverse proxying to `icecast:8000`), extend
`src/web/app.py` with a `/cam-url/<cam_id>` Windy API proxy endpoint, and write
`src/web/static/radio.html` — a minimal dark page with HTML5 audio player and rotating
webcam embed. Phase complete when browser can load the page, audio plays, and webcam image
updates every 60 seconds.

</domain>

<decisions>
## Implementation Decisions

**Caddy block structure:** Caddy is already running and owns 80/443 on `calenwalshe.com`.
Active config file is `agent-stack/caddy/Caddyfile` (note: `Caddyfile.new` is what was read
in research — confirm which is the live file before editing). Add:
```
radio.calenwalshe.com {
  handle /stream.mp3 {
    reverse_proxy icecast:8000
  }
  handle /status-json.xsl {
    reverse_proxy icecast:8000
  }
  handle /cam-url/* {
    reverse_proxy web-app:PORT
  }
  handle {
    root * /path/to/static
    file_server
  }
}
```
Run `caddy validate --config Caddyfile` before `caddy reload`. Keep a `.bak` of the
current file.

**Cam proxy endpoint:** Extend `src/web/app.py`. Windy v3 API endpoint:
`GET https://api.windy.com/webcams/api/v3/webcams/{id}`. API key from `config/webcams.json`.
Return the signed JPEG URL as `{"url": "..."}`. Log each call (count for rate monitoring).
On Windy API error, return 503 so the frontend's `onerror` handler triggers gracefully.

**Windy rate limit:** Free tier is 1000 req/day. At 8-min signed-URL refreshes for 1 cam
= ~180/day. Log a warning if daily count exceeds 700 (70% threshold).

**Frontend design (`radio.html`):**
- Background `#0a0a0a`, text `#e0e0e0`, accent `#ff4444` (red dot for live feel)
- `<audio controls autoplay>` pointing at `/stream.mp3` (relative — same domain via Caddy)
- Current track: poll `fetch('/status-json.xsl')` every 15s, show `icestats.source.title`
- Webcam: `<img id="cam">` updated by two setIntervals:
  - Every 60s: swap `img.src` to force JPEG refresh (append `?t=timestamp` to bust cache)
  - Every 8 min: `fetch('/cam-url/{id}')` to get a fresh signed URL (before 10-min expiry)
- `img.onerror`: hide cam, show "no feed" text in same box
- No framework — plain HTML/CSS/JS, under 200 lines total

**Cam selection for v1:** Pick one camera from `config/cameras.json` hardcoded to start
(e.g., a scenic city cam). Rotation across multiple cams can be added in v2.

### Claude's Discretion

- Exact Caddyfile path (verify `Caddyfile` vs `Caddyfile.new` is the live file)
- How `web/app.py` is exposed in Docker (port, service name for Caddy reverse_proxy target)
- Whether `radio.html` is served by Caddy `file_server` directly or through Flask
- Font choice for the minimal dark UI (system font stack is fine)
- Whether to show listener count from Icecast status JSON

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/self-hosted-radio/spec.md (sections 4, 7 steps 4–6)
- docs/cortex/specs/self-hosted-radio/gsd-handoff.md (tasks 4–6)
- docs/cortex/contracts/self-hosted-radio/contract-001.md
- docs/cortex/research/self-hosted-radio/concept-20260410T123000Z.md (q6 findings, adjacent findings)
- agent-stack/caddy/Caddyfile.new (reference for existing block structure)

</canonical_refs>

<specifics>
## Specific Ideas

From research (q6 — webcam embed):
- Windy API CORS is blocked from browser — must proxy server-side
- Image CDN URLs (the actual JPEG) allow cross-origin `<img src>` without CORS headers
- DOT cams need no proxy — plain `<img src="DOT_URL">` + setInterval works
- `onerror` on img is the correct dead-feed handler pattern

Adjacent finding from research:
- Icecast `<public>0</public>` should already be set in Phase 1, but verify in Caddy phase
  that the Icecast status page doesn't show the stream as public

</specifics>

<deferred>
## Deferred Ideas

- Multiple webcam rotation with solar scoring (channel-visual-identity work, now stashed)
- Music-visual mood pairing
- Now-playing artwork from track metadata
- Viewer count display (could pull from `/status-json.xsl` easily — low effort v2 add)

</deferred>

---

*Phase: 02-self-hosted-radio*
*Context gathered: 2026-04-10 via /cortex-bridge*
