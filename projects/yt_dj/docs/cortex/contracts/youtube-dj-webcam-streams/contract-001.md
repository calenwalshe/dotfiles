# Contract: youtube-dj-webcam-streams — execute

**ID:** youtube-dj-webcam-streams-001
**Slug:** youtube-dj-webcam-streams
**Phase:** execute
**Created:** 20260408T140000Z
**Status:** draft
**Repair Budget:** max_repair_contracts: 3, cooldown_between_repairs: 1

---

## Objective

Build a self-hosted YouTube live streaming system that composites worldwide webcam feeds into a visual grid with DJ audio, controllable via chatbot commands through a Redis Pub/Sub command bus, running autonomously with self-healing on component failure.

---

## Deliverables

- `src/obs_controller.py` — OBS WebSocket controller
- `src/liquidsoap_controller.py` — Liquidsoap telnet controller
- `src/chatbot.py` — Discord bot / YouTube Chat poller with command parser
- `src/health_monitor.py` — Webcam feed health checker with auto-swap
- `src/stream_manager.py` — YouTube API stream health + 12-hour auto-restart
- `src/mubert_client.py` — Mubert API client for autonomous music
- `config/scenes.json` — OBS scene definitions
- `config/webcams.json` — Webcam source list with fallbacks
- `config/liquidsoap.liq` — Liquidsoap configuration
- `scripts/yt-dj.service` — Main systemd orchestrator unit
- `scripts/obs-headless.service` — OBS headless systemd unit
- `scripts/liquidsoap.service` — Liquidsoap systemd unit
- `docs/runbook.md` — Operational runbook

---

## Scope

### In Scope

- Live video compositing pipeline (4-9 webcam feeds in configurable grid layouts)
- Audio pipeline (DJ software input + Liquidsoap autonomous playout)
- RTMP output to YouTube Live with 12-hour auto-restart
- Chatbot interface (Discord or YouTube Chat) for real-time control
- Redis Pub/Sub command bus connecting chatbot to pipeline controllers
- OBS headless on Linux with obs-websocket for runtime scene/source control
- Liquidsoap audio playout with telnet control
- Webcam feed health monitoring with automatic fallback/swap
- Systemd service management with watchdog auto-restart
- Windy Webcams API integration
- Mubert API integration for autonomous/unattended sessions

### Out of Scope

- Music production or DAW functionality
- Post-production video editing
- Multi-platform simultaneous streaming
- Music licensing negotiation
- YouTube monetization optimization
- Mobile app or web dashboard
- Viewer interaction beyond chatbot commands
- Custom visual effects, shaders, or generative art

---

## Write Roots

- `src/`
- `config/`
- `scripts/`
- `tests/`
- `docs/`

---

## Done Criteria

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

## Validators

- [ ] [external] `systemctl is-active yt-dj` returns `active`
- [ ] [external] `curl -s http://localhost:4455` returns OBS WebSocket response (connection accepted)
- [ ] [external] `echo "help" | nc -q 1 localhost 3333` returns Liquidsoap telnet help output
- [ ] [external] `redis-cli ping` returns `PONG`
- [ ] [external] `python -m pytest tests/ -v` passes all tests
- [ ] [judgment] YouTube stream shows webcam grid with audio — visually verified by human
- [ ] [judgment] Chatbot commands produce visible/audible changes on stream — verified by human
- [ ] [judgment] Stream visual variety is sufficient to avoid YouTube "Repetitious Content" policy — assessed by human

---

## Eval Plan

docs/cortex/evals/youtube-dj-webcam-streams/eval-plan.md (pending)

---

## Approvals

- [x] Contract approval
- [ ] Evals approval

---

## Completion Promise

<!-- The executing agent MUST emit this signal when all done criteria are satisfied: -->
<!-- CORTEX_PROMISE: youtube-dj-webcam-streams-001 COMPLETE -->

---

## Failed Approaches

<!-- Initial contract — no prior attempts. -->

---

## Why Previous Approach Failed

N/A — initial contract

---

## Rollback Hints

- Delete `src/`, `config/`, `scripts/`, `tests/`, `docs/runbook.md`
- `systemctl stop yt-dj obs-headless liquidsoap` and `systemctl disable yt-dj obs-headless liquidsoap`
- Remove systemd unit files from `/etc/systemd/system/`
- `systemctl daemon-reload`
- Uninstall OBS, Liquidsoap, Redis if no longer needed

---

## Repair Budget

**max_repair_contracts:** 3
**cooldown_between_repairs:** 1
