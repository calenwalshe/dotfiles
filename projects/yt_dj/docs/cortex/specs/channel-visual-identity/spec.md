# Spec: channel-visual-identity

**Slug:** channel-visual-identity
**Timestamp:** 20260409T014500Z
**Status:** draft

---

## 1. Problem

The current stream uses a static 2x2 webcam grid that feels like CCTV surveillance rather than an ambient portal. Research shows the strongest ambient streams use single full-screen views with slow transitions. The channel needs a visual identity: a sun-chasing single-cam pipeline that follows golden hour around the globe, minimal text overlays, and a diverse feed pool beyond Windy webcams. The channel also needs a name, description, and philosophy that communicates "anonymous portal to the world right now" without branding.

---

## 2. Scope

### In Scope

- Sun-chasing feed selector using pvlib solar position (prefer golden hour feeds)
- Single full-screen cam display with 3-5s dissolve transitions
- Python frame mixer writing raw RGB to a named pipe (FIFO), FFmpeg reads for RTMP encoding
- Dynamic text overlay: location name + local time (thin sans-serif, 60% opacity) via drawtext reload
- Pulsing "LIVE" indicator (upper-right)
- Diverse feed pool: Windy API cams + NASA ISS + DOT cams
- Feed health checking with automatic skip on failure
- Camera database with lat/lon, timezone, source URL, category (city/nature/ocean/space)
- Channel name, description, and YouTube channel setup
- Integration with existing DJ-mixed audio pipeline

### Out of Scope

- Grid layout (deprecated for primary view; may return as occasional beat in v2)
- Music-visual mood pairing automation (v2)
- OBS-based compositing (staying with FFmpeg pipeline for now)
- Viewer interaction features
- Custom animations or motion graphics
- Ambient audio from feeds layered under music

---

## 3. Architecture Decision

**Chosen approach:** Python frame mixer writing to a FIFO, read by FFmpeg for continuous RTMP encoding. The controller handles feed selection (pvlib solar scoring), image fetching, dissolve transitions (numpy alpha-blend), and overlay text updates. FFmpeg handles encoding and streaming only.

**Rationale:** FFmpeg's xfade filter requires finite inputs and cannot handle dynamic feed rotation. The FIFO decouples frame generation from encoding — Python controls timing and transitions, FFmpeg just encodes. drawtext reload=1 enables dynamic text without FFmpeg restarts. This is simpler than OBS headless and doesn't require Xvfb.

### Alternatives Considered

- **FFmpeg xfade slideshow:** Rejected — requires all inputs known at launch, cannot add/remove feeds at runtime.
- **OBS headless with scene switching:** Rejected for now — adds Xvfb dependency, memory leak risk, more complex. Revisit if FIFO approach proves insufficient.
- **Browser-based (Puppeteer + canvas):** Rejected — worst reliability for 24/7, highest resource usage.

---

## 4. Interfaces

- **Named pipe (FIFO)** (`/tmp/yt_dj_video_feed`): Raw RGB24 1920x1080 frames at 30fps from Python mixer to FFmpeg
- **Overlay text file** (`/tmp/yt_dj_overlay.txt`): Location + local time, overwritten by controller on each feed switch
- **Windy Webcams API v3** (read): Camera discovery, JPEG snapshot download
- **NASA ISS YouTube stream** (read): HLS URL extraction via yt-dlp for ISS frames
- **pvlib** (local computation): Solar position calculation for feed ranking
- **Camera database** (`config/cameras.json`): Feed pool with lat/lon, timezone, source URL, category
- **Merged audio file** (`/tmp/yt_dj_merged.mp3`): DJ-mixed audio from the automated-dj-mixing pipeline
- **YouTube RTMP** (write): Stream output

---

## 5. Dependencies

- **pvlib** — solar position calculation
- **Pillow** (PIL) — image loading and resizing
- **numpy** — frame alpha-blending for dissolve transitions
- **pytz** — timezone-aware local time for overlays
- **FFmpeg** (v6+) — encoding and RTMP streaming with drawtext overlay
- **yt-dlp** — NASA ISS HLS URL extraction
- **httpx** — webcam image fetching (already installed)

---

## 6. Risks

- **FIFO throughput:** Raw RGB24 at 1920x1080x30fps = ~186 MB/s through the pipe. Mitigation: this is local I/O, well within tmpfs bandwidth. If CPU-bound on numpy blending, reduce dissolve fps to 15 during transition only.
- **Windy API rate limits:** Free tier is 1000 requests/day. At one image per 45 seconds = ~1920/day. Mitigation: use Windy Pro tier, or cache images and rotate less frequently (every 2-3 minutes).
- **NASA ISS stream URL changes:** yt-dlp extraction depends on YouTube video ID staying stable. Mitigation: refresh URL every hour, fallback to surface cams if ISS unavailable.
- **Feed quality inconsistency:** Windy preview images are 400x224 — upscaling to 1080p will be blurry. Mitigation: use Ken Burns (slow pan/zoom) to mask low resolution. Prefer HLS video feeds where available.

---

## 7. Sequencing

1. **Camera database** — Build `config/cameras.json` with 30+ feeds from Windy, DOT, ISS, categorized by type and location. Checkpoint: JSON file with lat/lon, timezone, source URL for all feeds.

2. **Solar position scorer** — Implement pvlib-based feed ranking. Checkpoint: given current time, returns ranked list of feeds with golden-hour preference.

3. **Frame mixer** — Python script that fetches images, resizes to 1920x1080, writes dissolve frames to FIFO. Checkpoint: FIFO outputs valid raw RGB frames viewable with ffplay.

4. **FFmpeg RTMP pipeline** — FFmpeg reads FIFO + audio, applies drawtext overlay, streams to YouTube. Checkpoint: stream visible on YouTube with single cam + overlay text.

5. **Dynamic overlay** — Controller writes location + local time to overlay text file on each feed switch. Checkpoint: overlay text updates on stream when feed changes.

6. **Feed health checking** — Probe each feed before displaying, skip dead feeds. Checkpoint: dead feed URL is skipped, next-best feed selected.

7. **Integration** — Wire sun-chaser into existing go_live.py, merge with DJ audio pipeline. Checkpoint: full system streams DJ mix + sun-chasing visuals to YouTube.

---

## 8. Tasks

- [ ] Install pvlib, Pillow, numpy (`pip install pvlib Pillow numpy`)
- [ ] Build `config/cameras.json` with 30+ diverse feeds (cities, nature, ISS, coasts)
- [ ] Write `src/solar_scorer.py` — rank cameras by solar position, prefer golden hour
- [ ] Write `src/frame_mixer.py` — FIFO writer with dissolve transitions and hold periods
- [ ] Write `src/overlay.py` — dynamic text file writer (location, local time, LIVE dot)
- [ ] Update `src/go_live.py` to use frame mixer instead of static image grid
- [ ] Add NASA ISS feed integration (yt-dlp HLS extraction, frame capture)
- [ ] Add feed health probe (check image URL before displaying)
- [ ] Test dissolve transition quality (3-5s dissolve at 30fps)
- [ ] Test full pipeline: sun-chaser + DJ mix + YouTube RTMP
- [ ] Set up YouTube channel: name, description, avatar (minimal/abstract)
- [ ] 4-hour unattended run test

---

## 9. Acceptance Criteria

- [ ] Stream displays single full-screen cam view (not grid) with location + local time overlay
- [ ] Feed rotates every 2-5 minutes with smooth 3-5 second dissolve transition
- [ ] Feed selection prefers golden hour locations — solar elevation 0-10 degrees scored highest
- [ ] Overlay shows city name and local time in thin white text at 60% opacity, lower-left
- [ ] "LIVE" indicator visible in upper-right
- [ ] Camera database contains 30+ feeds across at least 10 countries
- [ ] Dead feeds are skipped within 10 seconds, next-best feed selected automatically
- [ ] NASA ISS feed appears in rotation when available
- [ ] System runs unattended for 4+ hours without stream interruption
- [ ] DJ-mixed audio plays continuously alongside the visual feed
