# Roadmap: Self-Hosted Radio Station

## Overview

Deploy a self-hosted internet radio station on the agent-stack box: Icecast2 + Liquidsoap in
Docker Compose, BPM/key-matched MP3 playout via dj_mixer.py, and a minimal dark web frontend
at `https://radio.calenwalshe.com` with HTML5 audio player and rotating webcam embed.

## Phases

### Phase 1: Services

**Goal**: Icecast2 + Liquidsoap running in Docker Compose on the agent-stack network, streaming
BPM/key-matched MP3s via dynamic M3U playlist written by `dj_mixer.py`.
**Depends on**: Nothing
**Requirements**: RADIO-01, RADIO-02
**Success Criteria** (what must be TRUE):
  1. `https://radio.calenwalshe.com/stream.mp3` streams MP3 audio continuously from the owner's library
  2. Stream uses BPM/key-matched queue — produced by `dj_mixer.py`, loaded by Liquidsoap via M3U
  3. Liquidsoap reconnects automatically if Icecast container restarts (tested manually)
**Research**: Unlikely — architecture fully resolved in research dossier
**Plans**: 0 plans

### Phase 2: Routing & Frontend

**Goal**: Caddy reverse proxy block live for `radio.calenwalshe.com`, Windy cam proxy endpoint
in `web/app.py`, and minimal dark `radio.html` frontend with audio player and webcam embed.
**Depends on**: Phase 1: Services
**Requirements**: RADIO-03, RADIO-04, RADIO-05
**Success Criteria** (what must be TRUE):
  1. Web page at `https://radio.calenwalshe.com` displays audio player and single webcam embed
  2. Webcam JPEG refreshes every 60 seconds without page reload
  3. HTTPS cert valid — browser shows no security warnings
**Research**: Unlikely
**Plans**: 0 plans

### Phase 3: Deploy & Verify

**Goal**: Containers running in production, Icecast private directory listing confirmed, 1-hour
unattended run test passes.
**Depends on**: Phase 2: Routing & Frontend
**Requirements**: RADIO-06, RADIO-07
**Success Criteria** (what must be TRUE):
  1. Icecast `<public>0</public>` confirmed — stream not discoverable via icecast.org or shoutcast directories
  2. Stream runs 1 hour unattended without interruption or silence gap
**Research**: Unlikely
**Plans**: 0 plans

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| Phase 1: Services | 0/0 | Not started | - |
| Phase 2: Routing & Frontend | 0/0 | Not started | - |
| Phase 3: Deploy & Verify | 0/0 | Not started | - |
