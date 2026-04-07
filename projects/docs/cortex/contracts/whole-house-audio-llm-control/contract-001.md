# Contract: whole-house-audio-llm-control-001

| Field | Value |
|-------|-------|
| ID | `whole-house-audio-llm-control-001` |
| Slug | `whole-house-audio-llm-control` |
| Phase | `execute` |
| Status | `pending` |

## Objective

Build the Pi home agent (Cast control + audio capture + music serving + API) and the Claude Code skill (NL → API translation), so that the user can control all audio sources across their Google Cast speakers via natural language from Claude Code.

## Deliverables

- `cast-agent/main.py` — FastAPI application (Pi agent)
- `cast-agent/cast_controller.py` — pychromecast wrapper (discover, play, transport, groups)
- `cast-agent/vinyl_capture.py` — ffmpeg → Icecast pipeline management
- `cast-agent/music_library.py` — Local file index + search + HTTP serve
- `cast-agent/spotify_handler.py` — SpotifyController + spotipy integration
- `cast-agent/youtube_handler.py` — YouTubeController integration
- `cast-agent/config.yaml` — Configuration (Tailscale IP, Icecast port, music path, Spotify creds)
- `cast-agent/requirements.txt` — Python dependencies
- `~/.claude/skills/cast-control/SKILL.md` — Claude Code skill definition
- `docs/setup-guide.md` — Hardware setup guide for user
- Systemd unit files for cast-agent and icecast2

## Scope

### In Scope
- Pi agent with all API endpoints (devices, play, transport, volume, status, vinyl, library, groups)
- Spotify, YouTube, local file, and vinyl/CD Cast playback
- Claude Code skill with NL parsing and API dispatch
- Hardware setup guide
- Systemd auto-start configuration

### Out of Scope
- AirPlay, Bluetooth, Sonos targets
- Video output
- Music recommendation/AI playlists
- Physical hardware setup (user responsibility)

## Write Roots

- `cast-agent/` (on Pi, via SSH/Tailscale)
- `~/.claude/skills/cast-control/`
- `docs/setup-guide.md`
- `/etc/icecast2/icecast.xml` (on Pi)
- `/etc/systemd/system/cast-agent.service` (on Pi)

## Done Criteria

- [ ] VPS reaches Pi over Tailscale; Pi agent API responds to GET /devices
- [ ] Vinyl/CD audio streams to Cast speaker group via Icecast + pychromecast
- [ ] Local music file plays on a named Cast device via POST /play
- [ ] YouTube video plays audio on a Cast device via YouTubeController
- [ ] Spotify track plays on a Cast device via SpotifyController + spotipy
- [ ] Transport controls (pause, resume, stop, volume) work on active device
- [ ] Claude Code skill: "play [query] in [room]" → correct API call → music plays
- [ ] Claude Code skill: "vinyl everywhere" → Icecast stream on Cast group
- [ ] System survives Pi reboot (systemd services auto-start)
- [ ] Analog turntable → amp → speaker path is unaffected
- [ ] Total hardware cost under $200

## Validators

- `curl http://100.y.y.y:8080/devices` returns JSON list of Cast devices
- `curl -X POST http://100.y.y.y:8080/vinyl/start` starts Icecast stream; verify with `curl http://100.y.y.y:8000/vinyl.mp3`
- `curl -X POST http://100.y.y.y:8080/play -d '{"source":"youtube","query":"dQw4w9WgXcQ","device":"Kitchen"}'` plays on Kitchen speaker
- Run Claude Code skill with test commands; verify audio output on Cast devices
- `sudo systemctl restart cast-agent && curl http://100.y.y.y:8080/devices` — still responds after restart

## Eval Plan

`docs/cortex/evals/whole-house-audio-llm-control/eval-plan.md` (pending)

## Repair Budget

| Field | Value |
|-------|-------|
| max_repair_contracts | 3 |
| cooldown_between_repairs | 1 |

## Failed Approaches

(empty — initial contract)

## Why Previous Approach Failed

N/A — initial contract.

## Approvals

- [ ] Contract approved for execution
- [ ] Evals approved

## Rollback Hints

- Delete `cast-agent/` directory on Pi
- Delete `~/.claude/skills/cast-control/` on VPS
- `sudo systemctl disable cast-agent && sudo systemctl stop cast-agent`
- `sudo apt remove icecast2` (if installed for this project)
- Tailscale can remain (useful for other things)
