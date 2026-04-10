# Contract: channel-visual-identity — execute

**ID:** channel-visual-identity-001
**Slug:** channel-visual-identity
**Phase:** execute
**Created:** 20260409T014500Z
**Status:** approved
**Repair Budget:** max_repair_contracts: 3, cooldown_between_repairs: 1

---

## Objective

Build a sun-chasing single-cam visual pipeline with dissolve transitions, dynamic overlays, and diverse feed sources — replacing the webcam grid — integrated with the DJ audio pipeline for 24/7 YouTube streaming.

---

## Deliverables

- `src/solar_scorer.py` — feed ranking by solar position
- `src/frame_mixer.py` — FIFO writer with dissolve
- `src/overlay.py` — dynamic text overlay controller
- `config/cameras.json` — 30+ feed database
- Updated `src/go_live.py` — sun-chasing pipeline

---

## Scope

### In Scope
- Sun-chasing feed selector (pvlib)
- Single cam full-screen with 3-5s dissolve
- FIFO-based frame mixer
- Dynamic drawtext overlay (location + local time)
- Diverse feed pool (Windy + ISS + DOT)
- Feed health checking
- Camera database
- YouTube channel setup

### Out of Scope
- Grid layout, music-visual mood pairing, OBS, viewer interaction, animations

---

## Write Roots
- `src/`
- `config/`
- `scripts/`
- `tests/`

---

## Done Criteria

- [ ] Single full-screen cam view with dissolve transitions
- [ ] Feed rotates every 2-5 min, prefers golden hour
- [ ] Overlay: city + local time, 60% opacity, lower-left
- [ ] "LIVE" indicator upper-right
- [ ] 30+ feeds across 10+ countries in cameras.json
- [ ] Dead feeds skipped within 10s
- [ ] NASA ISS in rotation
- [ ] 4+ hours unattended without interruption
- [ ] DJ audio plays continuously

---

## Validators

- [ ] [external] `python -c "import pvlib, PIL, numpy; print('ok')"` succeeds
- [ ] [external] `cat config/cameras.json | python -c "import json,sys; print(len(json.load(sys.stdin)))"` returns 30+
- [ ] [external] `python -m pytest tests/ -v` passes
- [ ] [judgment] Dissolve transitions look smooth — verified by human
- [ ] [judgment] Sun-chasing feed selection follows golden hour — verified by human
- [ ] [judgment] Overall visual aesthetic matches "anonymous portal" concept — verified by human

---

## Eval Plan

docs/cortex/evals/channel-visual-identity/eval-plan.md (pending)

---

## Approvals

- [x] Contract approval
- [ ] Evals approval

---

## Completion Promise

<!-- CORTEX_PROMISE: channel-visual-identity-001 COMPLETE -->

---

## Failed Approaches

<!-- Initial contract — no prior attempts. -->

---

## Why Previous Approach Failed

N/A — initial contract

---

## Rollback Hints

- Revert src/go_live.py to grid-based version (git checkout)
- Delete src/solar_scorer.py, src/frame_mixer.py, src/overlay.py
- Delete config/cameras.json
- Remove /tmp/yt_dj_video_feed FIFO

---

## Repair Budget

**max_repair_contracts:** 3
**cooldown_between_repairs:** 1
