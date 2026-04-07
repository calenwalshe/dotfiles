# Spec: whole-house-audio-llm-control

## 1. Problem

The user has a home full of Google Cast speakers (Nest Minis, Nest Audio, possibly Home Max) on a Google Mesh network, plus a vinyl turntable and upcoming CD player connected through a phono amp to physical speakers via an A/B selector. There is no way to: (a) distribute vinyl/CD audio beyond the two physical speaker zones, (b) control any of these speakers via natural language from the CLI, or (c) unify Spotify, YouTube Music, YouTube, local files, and physical media into a single control surface. The user works from a remote VPS running Claude Code and has a Raspberry Pi at home that hasn't been set up. This spec defines the full system — hardware setup instructions for the user, and software architecture for the Pi home agent and Claude Code skills.

## 2. Scope

### In Scope

- **Hardware setup guide**: Shopping list, wiring diagram, Pi OS flash + headless config, Tailscale install, Docker install, audio interface setup, vinyl/CD capture wiring
- **Pi home agent**: Python service running on the Pi that controls Cast devices, captures analog audio, serves music files, and exposes an API for the VPS
- **Analog audio capture**: Vinyl turntable and CD player audio → UCA202 → Pi → Icecast HTTP stream → Cast
- **Cast device control**: Discover, play, pause, stop, volume, seek, queue, multi-room groups via pychromecast
- **Spotify integration**: SpotifyController launch + spotipy playback control on Cast devices
- **YouTube / YT Music integration**: YouTubeController for video/music playback on Cast devices
- **Local music library**: Index, search, and serve local audio files (MP3, FLAC, AAC, OGG, WAV) to Cast via HTTP
- **Claude Code skill**: Natural language → structured API call translation, installed as a Claude Code skill on the VPS
- **Tailscale tunnel**: VPS ↔ Pi encrypted connectivity

### Out of Scope

- Replacing the existing turntable/amp/speaker setup (additive only)
- AirPlay, Bluetooth point-to-point, or Sonos native targets
- Video output to TVs (audio only; YouTube shows video on Nest Hub as a side effect, not a feature)
- Music recommendation engine or AI playlist generation
- Multi-user profiles or per-person preferences
- Home automation beyond audio
- Music acquisition, ripping, or library management tools

## 3. Architecture Decision

**Chosen approach: Custom Pi agent with pychromecast + Icecast, Claude Code skill on VPS**

Build a lightweight Python service on the Pi that:
1. Runs pychromecast for all Cast device control (discovery, playback, groups)
2. Runs Icecast + ffmpeg for live analog audio streaming (vinyl/CD → Cast)
3. Serves local music files via a built-in HTTP server
4. Uses spotipy + SpotifyController for Spotify Cast integration
5. Uses YouTubeController for YouTube/YT Music Cast integration
6. Exposes a JSON API (FastAPI) for the VPS to call over Tailscale

A Claude Code skill on the VPS translates natural language into structured API calls to the Pi.

**Rationale:** Music Assistant was considered but rejected as the primary path because: (a) its API surface hasn't been validated for fine-grained LLM control, (b) its vinyl Audio-In provider is still beta, (c) adding a large Docker dependency (MA) on a Pi that may be a 3B+ is risky for performance. A custom agent is ~500 lines of Python, gives us full control, and can be extended without waiting on upstream. If we later want MA, the agent's API is compatible — we can swap the backend.

**Alternatives considered:**
- **Music Assistant**: Handles 80% out of the box but adds heavyweight dependency, unvalidated API for NL control, beta vinyl support. Rejected as primary; remains a future migration option.
- **Home Assistant + Cast integration**: Full smart home platform with REST API. Overkill — we only need audio. Rejected.
- **Direct pychromecast from VPS via Tailscale**: mDNS doesn't relay over Tailscale, so Cast discovery fails. Rejected — Pi must be the Cast controller.
- **catt CLI wrapper**: Simple but no programmatic API, hard to integrate with Spotify/YouTube controllers. Rejected as primary; useful for prototyping.

## 4. Interfaces

### Pi Agent API (FastAPI, port 8080)

| Endpoint | Method | Purpose | Owner |
|----------|--------|---------|-------|
| `/devices` | GET | List discovered Cast devices and groups | Pi agent |
| `/play` | POST | Play media (file, URL, Spotify URI, YouTube ID) on a device | Pi agent |
| `/transport/{action}` | POST | pause, resume, stop, next, previous | Pi agent |
| `/volume` | POST | Set or adjust volume on a device | Pi agent |
| `/status` | GET | Current playback status on active device(s) | Pi agent |
| `/vinyl/start` | POST | Start Icecast capture + cast vinyl stream to device/group | Pi agent |
| `/vinyl/stop` | POST | Stop vinyl streaming | Pi agent |
| `/library/search` | GET | Search local music library by query | Pi agent |
| `/groups` | GET/POST | List or create Cast speaker groups | Pi agent |

### Claude Code Skill (on VPS)

| File | Purpose |
|------|---------|
| `~/.claude/skills/cast-control/SKILL.md` | Skill definition — NL parsing, API dispatch |

Reads: user natural language input
Writes: JSON POST/GET to Pi agent API over Tailscale

### Icecast Stream (on Pi, port 8000)

| Mount | Format | Purpose |
|-------|--------|---------|
| `/vinyl.mp3` | MP3 128kbps | Live analog audio stream (vinyl or CD) |

### Local Music HTTP Server (on Pi, port 8080)

Serves files from `/home/pi/music/` (or configured path) as static HTTP.

### Tailscale

| Device | Tailscale IP | Role |
|--------|-------------|------|
| VPS | 100.x.x.x | Client — sends commands |
| Pi | 100.y.y.y | Server — receives commands, controls Cast |

## 5. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| pychromecast | 14.0.5+ | Cast device discovery and control |
| spotipy | 2.x | Spotify Web API client |
| FastAPI | 0.100+ | Pi agent HTTP API |
| uvicorn | 0.20+ | ASGI server for FastAPI |
| ffmpeg | system package | Analog audio capture and encoding |
| icecast2 | system package | HTTP audio streaming server |
| Tailscale | latest | VPN tunnel between VPS and Pi |
| Docker | latest | Container runtime on Pi (for Icecast) |
| yt-dlp | latest | YouTube URL resolution |
| mutagen | 1.47+ | Audio file metadata reading (ID3, etc.) |
| Raspberry Pi OS Lite | Bookworm (64-bit) | Pi operating system |
| Behringer UCA202 | hardware | USB audio interface for vinyl/CD capture |

## 6. Risks

- **Spotify first-launch chicken-and-egg** — SpotifyController may time out on first cast to a device. Mitigation: document as one-time manual setup step; user casts once from Spotify app to "wake up" each device.
- **Pi model too weak** — If Pi is a 3B+, Docker + Icecast + FastAPI + pychromecast may be tight. Mitigation: run Icecast natively (not Docker); profile memory usage early; fall back to lighter setup if needed.
- **Phono amp has no spare output** — Y-splitter may need to go between amp and A/B switch, or user may need an RCA switch. Mitigation: Y-splitter is the default; RCA switch ($12) as backup.
- **Cast device names unknown** — Can't hardcode device names until `catt scan` runs on the Pi. Mitigation: device discovery is dynamic; skill uses fuzzy matching on device names.
- **Icecast vinyl stream latency** — ~1-2 second delay inherent to Cast buffering. Mitigation: acceptable for non-same-room listening; document clearly so user has correct expectations.
- **Music collection not on Pi** — If music files are elsewhere, need a transfer plan. Mitigation: USB SSD or network mount; defer until Pi is set up.

## 7. Sequencing

### Stage 1: Hardware Setup (user does this)

1. **Buy hardware** — Order UCA202, Y-splitter, RCA cables, any missing Pi accessories
2. **Flash Pi** — Raspberry Pi OS Lite (64-bit Bookworm), enable SSH, set hostname
3. **Connect Pi to network** — Ethernet to Google Mesh router (preferred) or WiFi
4. **Install Tailscale on Pi** — `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`
5. **Install Tailscale on VPS** — Same command, join same tailnet
6. **Verify tunnel** — Ping Pi from VPS via Tailscale IP
7. **Wire audio** — Phono amp → Y-splitter → UCA202 → Pi USB
8. **Verify audio capture** — `arecord -D hw:1,0 -f cd -d 5 test.wav && aplay test.wav`

**Checkpoint**: Pi is on network, reachable from VPS, audio capture works.

### Stage 2: Audio Infrastructure (software, I build this)

9. **Install system packages** — ffmpeg, icecast2, python3-venv
10. **Set up Icecast** — Configure icecast.xml, start service
11. **Build vinyl capture service** — ffmpeg ALSA → Icecast pipeline, start/stop control
12. **Verify vinyl stream** — Play record, open `http://pi:8000/vinyl.mp3` in browser

**Checkpoint**: Vinyl audio streams to HTTP URL.

### Stage 3: Cast Control (software, I build this)

13. **Build Pi agent** — FastAPI app with pychromecast device discovery
14. **Implement `/devices`** — List all Cast devices on the network
15. **Implement `/play` (local files)** — HTTP serve + cast media
16. **Implement `/play` (YouTube)** — YouTubeController integration
17. **Implement `/play` (Spotify)** — SpotifyController + spotipy integration
18. **Implement `/vinyl/start` and `/vinyl/stop`** — Icecast stream → Cast
19. **Implement transport controls** — pause, resume, stop, volume, seek
20. **Implement `/status`** — Current playback info
21. **Implement `/library/search`** — Fuzzy search on local music metadata

**Checkpoint**: All Cast operations work via API calls from VPS.

### Stage 4: Claude Code Skill (software, I build this)

22. **Build skill definition** — `SKILL.md` with trigger patterns and NL parsing
23. **Implement NL → API translation** — Parse intent, device target, source type, query
24. **Implement response formatting** — Playback status, device lists, error messages
25. **Test end-to-end** — Natural language → skill → API → Cast → audio plays

**Checkpoint**: "play some jazz in the kitchen" from Claude Code plays music on the kitchen speaker.

### Stage 5: Polish & Documentation

26. **Cast group management** — Create/list multi-room groups
27. **Error handling** — Device not found, stream failed, Spotify auth expired
28. **Setup guide** — Complete hardware + software setup doc for user reference
29. **Systemd services** — Pi agent and Icecast auto-start on boot

**Checkpoint**: System survives Pi reboot, all features documented.

## 8. Tasks

### Stage 1: Hardware Setup (user)
- [ ] Order Behringer UCA202 (~$25)
- [ ] Order RCA Y-splitter pair (~$6)
- [ ] Order short RCA cables if needed (~$6)
- [ ] Acquire microSD 32GB+, USB-C power supply, case if not owned
- [ ] Flash Raspberry Pi OS Lite (64-bit Bookworm) to SD card with SSH enabled
- [ ] Boot Pi, connect to network (ethernet preferred)
- [ ] Install Tailscale on Pi and join tailnet
- [ ] Install Tailscale on VPS and join same tailnet
- [ ] Verify VPS can reach Pi over Tailscale (`ping 100.y.y.y`)
- [ ] Wire: phono amp RCA out → Y-splitter → UCA202 RCA in → Pi USB
- [ ] Verify audio capture: `arecord -D hw:1,0 -f cd -d 5 test.wav`

### Stage 2: Audio Infrastructure (software)
- [ ] Install ffmpeg, icecast2 on Pi
- [ ] Configure icecast.xml (port 8000, mount /vinyl.mp3, source password)
- [ ] Build vinyl capture script (ffmpeg ALSA → Icecast)
- [ ] Test vinyl stream plays in browser

### Stage 3: Cast Control (software)
- [ ] Create Pi agent project (`cast-agent/`)
- [ ] Implement Cast device discovery and caching
- [ ] Implement `/devices` endpoint
- [ ] Implement `/play` endpoint (local files — HTTP serve + cast)
- [ ] Implement `/play` endpoint (YouTube — YouTubeController)
- [ ] Implement `/play` endpoint (Spotify — SpotifyController + spotipy)
- [ ] Implement `/vinyl/start` and `/vinyl/stop` endpoints
- [ ] Implement `/transport/{action}` endpoint (pause, resume, stop, next, prev)
- [ ] Implement `/volume` endpoint
- [ ] Implement `/status` endpoint
- [ ] Implement `/library/search` endpoint (mutagen metadata indexing + fuzzy search)
- [ ] Implement `/groups` endpoint (list and create Cast groups)

### Stage 4: Claude Code Skill (software)
- [ ] Create `~/.claude/skills/cast-control/SKILL.md`
- [ ] Implement NL intent parsing (play, pause, volume, vinyl, status, move)
- [ ] Implement device target resolution (fuzzy match room names)
- [ ] Implement source type detection (Spotify, YouTube, local, vinyl)
- [ ] Implement API dispatch (POST/GET to Pi agent over Tailscale)
- [ ] Implement response formatting for user

### Stage 5: Polish
- [ ] Systemd unit file for Pi agent (auto-start on boot)
- [ ] Systemd unit file for Icecast (auto-start on boot)
- [ ] Error handling: device not found, auth expired, stream failed
- [ ] Write hardware setup guide (standalone reference doc)
- [ ] End-to-end test: NL command → Cast playback for all 5 sources

## 9. Acceptance Criteria

- [ ] VPS can reach Pi over Tailscale and Pi agent API responds to `/devices`
- [ ] `arecord` captures audio from UCA202 on the Pi (vinyl/CD path works)
- [ ] Vinyl/CD audio streams to Cast speaker group via Icecast + pychromecast
- [ ] Local music file plays on a named Cast device via `/play` API
- [ ] YouTube video plays audio on a Cast device via YouTubeController
- [ ] Spotify track plays on a Cast device via SpotifyController + spotipy
- [ ] Transport controls (pause, resume, stop, volume) work on active device
- [ ] Claude Code skill translates "play [query] in [room]" to correct API call and music plays
- [ ] Claude Code skill translates "vinyl everywhere" to Icecast stream on Cast group
- [ ] System survives Pi reboot (services auto-start via systemd)
- [ ] Existing turntable → amp → speaker path is unaffected (analog signal unchanged)
- [ ] Total hardware cost is under $200
