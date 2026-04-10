# Spec: youtube-dj-webcam-streams

**Slug:** youtube-dj-webcam-streams
**Timestamp:** 20260408T140000Z
**Status:** draft

---

## 1. Problem

The owner wants to DJ live on YouTube with a distinctive visual identity: a mosaic of worldwide webcam feeds composited behind the audio stream. The system must run autonomously (stream stays up without manual intervention) while allowing the owner to influence music selection, visual layout, and mood via chatbot commands in real time. No existing tool combines live DJ audio, multi-source webcam video compositing, chatbot-driven control, and YouTube RTMP output in an integrated, self-hosted system. The owner accepts YouTube Content ID claims on commercial music (forfeiting ad revenue) in exchange for full creative freedom over track selection.

---

## 2. Scope

### In Scope

- Live video compositing pipeline that pulls 4-9 public webcam feeds and arranges them in configurable grid layouts
- Audio pipeline that accepts the owner's DJ audio (from DJ software or Liquidsoap playout) and mixes it into the video stream
- RTMP output to YouTube Live with auto-restart logic for the 12-hour stream limit
- Chatbot interface (Discord or YouTube Chat) that accepts commands to change music mood/genre, switch webcam scenes, and alter visual layout
- Redis Pub/Sub command bus connecting chatbot to pipeline controllers
- OBS headless (Linux + Xvfb) for video compositing with obs-websocket for runtime control
- Liquidsoap for autonomous audio playout (unattended mode) with telnet control
- Webcam feed health monitoring with automatic fallback/swap for offline feeds
- Systemd service management with watchdog auto-restart for all pipeline components
- Windy Webcams API integration for global scenic camera feeds
- Mubert API integration as fallback music source for autonomous/unattended sessions

### Out of Scope

- Music production or DAW functionality
- Post-production video editing
- Simultaneous multi-platform streaming (Twitch, Mixcloud — future work)
- Music licensing negotiation or rights management
- YouTube monetization optimization
- Mobile app or web dashboard for control (chatbot only for v1)
- Viewer interaction features beyond chatbot commands (no polls, no song requests from viewers in v1)
- Custom visual effects, shaders, or generative art overlays (plain grid layouts only for v1)

---

## 3. Architecture Decision

**Chosen approach:** OBS headless (video) + Liquidsoap (audio) + Redis Pub/Sub (command bus) + Python chatbot (control interface), outputting RTMP to YouTube Live.

**Rationale:** OBS headless provides the richest runtime scene manipulation via obs-websocket (add/remove/reposition webcam sources, switch between pre-configured layouts, control transitions) — critical for chatbot-driven visual changes. Liquidsoap is battle-tested for 24/7 audio playout with crossfading, playlist management, and runtime control via telnet. Redis Pub/Sub decouples the chatbot from pipeline internals, enabling independent scaling and multiple control surfaces. This hybrid approach was selected over FFmpeg-only (too rigid for runtime changes) and GStreamer (steeper learning curve, less community support for this use case).

### Alternatives Considered

- **FFmpeg-only pipeline:** Rejected as primary because `filter_complex` cannot add/remove sources at runtime without restart. Retained as prototype/fallback for fixed-layout streams.
- **GStreamer compositor:** Deferred. Best dynamic source management and GPU acceleration, but steep learning curve and less community tooling for OBS-style scene management. Revisit if OBS headless proves unstable.
- **Browser-based (Puppeteer + Canvas):** Rejected. Worst 24/7 reliability due to Chromium memory leaks. Only justified for complex HTML/CSS overlays not needed in v1.
- **AzuraCast (full stack):** Rejected as primary. Excellent for audio-only radio automation but video compositing is a bolt-on, not first-class. Audio scheduling concepts inform the Liquidsoap configuration.

---

## 4. Interfaces

- **YouTube Live Streaming API** (Google, read+write): Create/manage live broadcasts, get stream keys, monitor stream health, handle 12-hour auto-restart. OAuth2 authentication required.
- **YouTube Chat API** (Google, read): Poll live chat messages for chatbot commands. OAuth2 via same credentials.
- **OBS WebSocket v5** (local, port 4455, read+write): Scene switching, source management, stream start/stop. Python client via `obsws-python`.
- **Liquidsoap telnet** (local, port 3333, read+write): Track skip, playlist switch, crossfade control, metadata query. Plain TCP socket.
- **Redis Pub/Sub** (local, port 6379, read+write): Command bus channels `stream:audio`, `stream:video`, `stream:layout`. Fire-and-forget messaging.
- **Windy Webcams API v3** (Windy, read): Discover webcams by location/category, get HLS/JPEG stream URLs. REST API with API key header. URLs expire (10 min free, 24h pro).
- **Mubert API** (Mubert, read): Generate royalty-free music by mood/genre. REST API with API key. For autonomous/unattended sessions only.
- **Discord API** (Discord, read+write): Bot receives commands via WebSocket gateway, sends confirmations. Alternative to YouTube Chat with lower latency.
- **File system paths:**
  - `config/` — stream configuration, scene definitions, webcam lists
  - `src/` — Python source code for chatbot, controllers, health monitors
  - `scripts/` — systemd unit files, startup scripts, health checks

---

## 5. Dependencies

- **OBS Studio** (v30+) — headless video compositing with obs-websocket built-in
- **Xvfb** — virtual framebuffer for headless OBS on Linux
- **Liquidsoap** (v2.2+) — audio playout, crossfading, playlist management
- **Redis** (v7+) — Pub/Sub command bus
- **FFmpeg** (v6+) — used internally by OBS and as fallback compositing pipeline
- **Python** (3.11+) — chatbot, pipeline controllers, health monitors
- **obsws-python** — Python client for OBS WebSocket v5
- **discord.py** or **youtube-chat-api** — chatbot framework (decision pending: Discord vs YouTube Chat)
- **redis-py** — Python Redis client
- **requests** or **httpx** — HTTP client for Windy and Mubert APIs
- **systemd** — process management and watchdog for all services

---

## 6. Risks

- **OBS headless memory leaks on multi-day runs** — Mitigation: systemd watchdog with periodic health checks; auto-restart OBS every 12 hours (aligned with YouTube's stream limit) to reset memory.
- **Webcam feeds go offline unpredictably (10-30% at any time)** — Mitigation: feed health monitor polls each source every 60s; dead feeds auto-swap to alternates from a ranked backup list.
- **YouTube "Repetitious Content" policy flags the channel** — Mitigation: ensure meaningful visual variation (rotate webcam themes by time-of-day, overlay current track info, vary layouts); avoid pure static grids.
- **YouTube 12-hour stream auto-termination** — Mitigation: monitor stream health via YouTube API; detect termination and auto-create new broadcast + restart RTMP push within 60 seconds.
- **Content ID blocks ~1-5% of tracks entirely** — Mitigation: pre-test problematic tracks with unlisted uploads; maintain a blocklist of tracks that trigger full blocks rather than claims.
- **GDPR exposure from EU webcam feeds with identifiable individuals** — Mitigation: prefer low-resolution feeds, traffic cameras, and nature/scenic cams; avoid high-res city center cams in EU jurisdictions.
- **Redis Pub/Sub message loss (fire-and-forget)** — Mitigation: acceptable for this use case; commands are idempotent and the next command will correct state. Use Redis Streams if audit trail needed later.

---

## 7. Sequencing

1. **FFmpeg prototype** — Build a minimal FFmpeg pipeline: 2x2 webcam grid + test audio → RTMP to YouTube. Validates end-to-end stream path. Checkpoint: stream visible on YouTube with 4 webcam feeds and audio.

2. **OBS headless setup** — Install OBS + Xvfb on Linux, create base scenes (2x2, 3x3, single-focus), add webcam sources from Windy API. Checkpoint: OBS running headless, compositing webcam feeds, outputting to virtual display.

3. **OBS → YouTube RTMP** — Connect OBS output to YouTube Live via RTMP. Add systemd unit for OBS. Checkpoint: OBS streams to YouTube Live with webcam grid and test audio.

4. **Liquidsoap audio playout** — Configure Liquidsoap with a test playlist, crossfading, and telnet control. Pipe audio output into OBS as audio source. Checkpoint: Liquidsoap plays music with crossfades, controllable via telnet.

5. **Redis command bus** — Set up Redis, define channel schema (`stream:audio`, `stream:video`, `stream:layout`), build Python controller modules that subscribe to channels and call OBS WebSocket / Liquidsoap telnet. Checkpoint: publishing to Redis channels triggers OBS scene changes and Liquidsoap track skips.

6. **Chatbot** — Build Discord bot (or YouTube Chat poller) that parses commands ("play house", "night cams", "2x2 grid") and publishes structured messages to Redis. Checkpoint: chatbot command → Redis → pipeline change → visible on YouTube stream.

7. **Webcam health monitor** — Build feed health checker that polls each webcam source, detects offline feeds, and publishes swap commands to Redis. Checkpoint: deliberately kill a webcam source; system auto-replaces it within 120 seconds.

8. **12-hour auto-restart** — Implement YouTube API integration for stream health monitoring and auto-restart. Checkpoint: stream runs for 12+ hours without manual intervention across the auto-split boundary.

9. **Mubert autonomous mode** — Integrate Mubert API for unattended sessions when the owner isn't actively DJing. Checkpoint: system runs autonomously with AI-generated music and rotating webcam themes.

10. **Hardening** — Systemd watchdogs for all services, log aggregation, alerting on stream death, documented operational runbook. Checkpoint: kill any single component; system self-heals within 120 seconds.

---

## 8. Tasks

- [ ] Build FFmpeg 2x2 webcam grid prototype with test audio → YouTube RTMP
- [ ] Install and configure OBS Studio headless on Linux with Xvfb
- [ ] Create OBS scene collection: 2x2 grid, 3x3 grid, single-focus layouts
- [ ] Integrate Windy Webcams API: discover cameras, fetch HLS URLs, add as OBS sources
- [ ] Configure OBS RTMP output to YouTube Live with stream key
- [ ] Write systemd unit file for OBS headless service
- [ ] Install and configure Liquidsoap with test playlist and crossfade settings
- [ ] Configure Liquidsoap telnet server for runtime control
- [ ] Pipe Liquidsoap audio output into OBS as audio source
- [ ] Write systemd unit file for Liquidsoap service
- [ ] Install Redis and configure Pub/Sub channels (stream:audio, stream:video, stream:layout)
- [ ] Build Python OBS controller: subscribes to Redis, calls obs-websocket API
- [ ] Build Python Liquidsoap controller: subscribes to Redis, sends telnet commands
- [ ] Build Discord bot (or YouTube Chat poller) with command parser
- [ ] Define command schema: mood/genre, scene selection, layout changes
- [ ] Wire chatbot → Redis → controllers end-to-end
- [ ] Build webcam feed health monitor with polling and auto-swap logic
- [ ] Integrate YouTube Live Streaming API for stream health monitoring
- [ ] Implement 12-hour auto-restart logic (detect termination, create new broadcast, restart RTMP)
- [ ] Integrate Mubert API for autonomous/unattended music generation
- [ ] Build autonomous mode: Mubert music + timed webcam theme rotation
- [ ] Add systemd watchdog configuration for all services
- [ ] Write operational runbook (start, stop, troubleshoot, recover)
- [ ] End-to-end integration test: chatbot commands through to YouTube stream output

---

## 9. Acceptance Criteria

- [ ] YouTube live stream displays a composite grid of 4+ webcam feeds from different global locations with audio
- [ ] Chatbot command "play house" (or equivalent genre command) changes the music mood/genre within 5 seconds
- [ ] Chatbot command "night cams" (or equivalent scene command) switches the webcam layout/theme within 3 seconds
- [ ] Chatbot command "2x2" / "3x3" changes the grid layout within 3 seconds
- [ ] When a webcam feed goes offline, the system auto-replaces it with a backup feed within 120 seconds without stream interruption
- [ ] Stream survives the YouTube 12-hour auto-split boundary and auto-restarts within 60 seconds
- [ ] System self-heals when any single component (OBS, Liquidsoap, Redis) crashes — service restored within 120 seconds via systemd watchdog
- [ ] Autonomous mode runs for 4+ hours without human intervention using Mubert-generated music and rotating webcam themes
- [ ] All services start via `systemctl start yt-dj` and stop via `systemctl stop yt-dj`
- [ ] Content ID claims on commercial tracks result in claims only (not blocks or strikes) — verified with 10+ track test set
