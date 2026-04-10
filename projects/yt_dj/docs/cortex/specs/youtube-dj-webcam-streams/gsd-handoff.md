# GSD Handoff: youtube-dj-webcam-streams

**Slug:** youtube-dj-webcam-streams
**Timestamp:** 20260408T140000Z
**Status:** draft

---

## Objective

Build a self-hosted live streaming system that composites worldwide webcam feeds into a visual grid, mixes in DJ audio, streams to YouTube Live via RTMP, and accepts real-time control commands via chatbot (Discord or YouTube Chat) through a Redis Pub/Sub command bus — running autonomously 24/7 with self-healing on component failure.

---

## Deliverables

- `src/obs_controller.py` — OBS WebSocket controller (subscribes to Redis, manages scenes/sources)
- `src/liquidsoap_controller.py` — Liquidsoap telnet controller (subscribes to Redis, manages audio playout)
- `src/chatbot.py` — Discord bot or YouTube Chat poller with command parser
- `src/health_monitor.py` — Webcam feed health checker with auto-swap logic
- `src/stream_manager.py` — YouTube API integration for stream health monitoring and 12-hour auto-restart
- `src/mubert_client.py` — Mubert API client for autonomous music generation
- `config/scenes.json` — OBS scene definitions (2x2, 3x3, single-focus)
- `config/webcams.json` — Webcam source list with fallbacks, sourced from Windy API
- `config/liquidsoap.liq` — Liquidsoap configuration with playlists and crossfade settings
- `scripts/yt-dj.service` — Main systemd unit (orchestrates all services)
- `scripts/obs-headless.service` — OBS headless systemd unit
- `scripts/liquidsoap.service` — Liquidsoap systemd unit
- `docs/runbook.md` — Operational runbook (start, stop, troubleshoot, recover)

---

## Requirements

- None formalized

---

## Tasks

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

## Acceptance Criteria

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

---

## Contract Link

docs/cortex/contracts/youtube-dj-webcam-streams/contract-001.md
