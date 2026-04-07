# GSD Handoff: whole-house-audio-llm-control

## Objective

Build a unified whole-house audio system: a Raspberry Pi home agent that controls Google Cast speakers via pychromecast, captures vinyl/CD audio via USB interface + Icecast, integrates Spotify and YouTube, and exposes an API that a Claude Code skill on the VPS translates natural language commands into. The user handles all hardware setup; Claude builds all software.

## Deliverables

| Artifact | Path | Description |
|----------|------|-------------|
| Pi agent | `cast-agent/` (on Pi) | FastAPI service: Cast control, audio capture, music serving |
| Claude Code skill | `~/.claude/skills/cast-control/SKILL.md` | NL → API translation skill |
| Icecast config | `/etc/icecast2/icecast.xml` (on Pi) | Audio streaming server config |
| Vinyl capture script | `cast-agent/vinyl_capture.py` (on Pi) | ffmpeg ALSA → Icecast pipeline |
| Systemd units | `/etc/systemd/system/cast-agent.service` | Auto-start on boot |
| Hardware setup guide | `docs/setup-guide.md` | Step-by-step for user |

## Requirements

None formalized — this is a personal project with clarify brief as the requirements source.

## Tasks

1. [ ] **[USER]** Order hardware (UCA202, Y-splitter, cables, Pi accessories)
2. [ ] **[USER]** Flash Pi OS Lite, connect to network, install Tailscale
3. [ ] **[USER]** Install Tailscale on VPS, verify tunnel
4. [ ] **[USER]** Wire audio: phono amp → Y-splitter → UCA202 → Pi
5. [ ] **[USER]** Verify audio capture with `arecord`
6. [ ] Install ffmpeg, icecast2 on Pi; configure Icecast
7. [ ] Build vinyl capture service (ffmpeg → Icecast)
8. [ ] Build Pi agent (FastAPI + pychromecast)
9. [ ] Implement all API endpoints: /devices, /play, /transport, /volume, /status, /vinyl, /library/search, /groups
10. [ ] Implement Spotify integration (SpotifyController + spotipy)
11. [ ] Implement YouTube integration (YouTubeController)
12. [ ] Build Claude Code skill (SKILL.md + NL parsing + API dispatch)
13. [ ] Set up systemd services for auto-start
14. [ ] Write hardware setup guide
15. [ ] End-to-end test all 5 audio sources

## Acceptance Criteria

- [ ] VPS reaches Pi over Tailscale; Pi agent API responds
- [ ] Vinyl/CD audio streams to Cast speakers via Icecast
- [ ] Local music file plays on named Cast device
- [ ] YouTube video/music plays on Cast device
- [ ] Spotify track plays on Cast device
- [ ] Transport controls work (pause, resume, stop, volume)
- [ ] "play [query] in [room]" from Claude Code plays music
- [ ] "vinyl everywhere" streams vinyl to Cast group
- [ ] System survives Pi reboot
- [ ] Analog speaker path unchanged
- [ ] Hardware cost under $200

## Contract Link

`docs/cortex/contracts/whole-house-audio-llm-control/contract-001.md`
