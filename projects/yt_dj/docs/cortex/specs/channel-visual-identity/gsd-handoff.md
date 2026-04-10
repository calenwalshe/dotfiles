# GSD Handoff: channel-visual-identity

**Slug:** channel-visual-identity
**Timestamp:** 20260409T014500Z
**Status:** draft

---

## Objective

Replace the webcam grid with a single full-screen sun-chasing visual pipeline that follows golden hour around the globe, displaying one camera at a time with slow dissolve transitions, minimal text overlays (location + local time), and diverse feed sources including NASA ISS — integrated with the DJ-mixed audio pipeline for a 24/7 anonymous ambient YouTube stream.

---

## Deliverables

- `src/solar_scorer.py` — pvlib-based feed ranking by solar position
- `src/frame_mixer.py` — FIFO writer with dissolve transitions
- `src/overlay.py` — dynamic drawtext overlay controller
- `config/cameras.json` — 30+ feed database with lat/lon, timezone, URL, category
- Updated `src/go_live.py` — sun-chasing pipeline replacing grid

---

## Requirements

- None formalized

---

## Tasks

- [ ] Install pvlib, Pillow, numpy
- [ ] Build config/cameras.json with 30+ diverse feeds
- [ ] Write src/solar_scorer.py
- [ ] Write src/frame_mixer.py with FIFO and dissolve
- [ ] Write src/overlay.py
- [ ] Update src/go_live.py to use frame mixer
- [ ] Add NASA ISS feed integration
- [ ] Add feed health probe
- [ ] Test dissolve transition quality
- [ ] Test full pipeline end-to-end
- [ ] Set up YouTube channel identity
- [ ] 4-hour unattended run test

---

## Acceptance Criteria

- [ ] Single full-screen cam view with dissolve transitions (not grid)
- [ ] Feed rotates every 2-5 min, prefers golden hour locations
- [ ] Overlay: city + local time, thin white 60% opacity, lower-left
- [ ] "LIVE" indicator upper-right
- [ ] 30+ feeds across 10+ countries
- [ ] Dead feeds skipped automatically
- [ ] NASA ISS in rotation
- [ ] 4+ hours unattended
- [ ] DJ audio plays continuously

---

## Contract Link

docs/cortex/contracts/channel-visual-identity/contract-001.md
