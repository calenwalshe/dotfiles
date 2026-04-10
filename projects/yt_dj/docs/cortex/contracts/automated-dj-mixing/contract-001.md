# Contract: automated-dj-mixing — execute

**ID:** automated-dj-mixing-001
**Slug:** automated-dj-mixing
**Phase:** execute
**Created:** 20260408T234500Z
**Status:** approved
**Repair Budget:** max_repair_contracts: 3, cooldown_between_repairs: 1

---

## Objective

Build an automated DJ mixing system using Mixxx headless with beat-matched harmonic transitions, controllable via chatbot through a Redis-to-MIDI bridge, with the track library pre-analyzed by essentia and sequenced by a smart queue builder.

---

## Deliverables

- `src/analyze_library.py` — essentia batch BPM/key/energy analysis
- `src/queue_builder.py` — track sequencer (BPM, Camelot, energy)
- `src/mixxx_bridge.py` — Redis → MIDI CC bridge
- `config/track_metadata.json` — analyzed track metadata
- `scripts/mixxx-dj.service` — systemd unit
- `scripts/setup-mixxx.sh` — install/config script

---

## Scope

### In Scope

- Mixxx headless via Xvfb with rdircio/autodj
- Virtual MIDI loopback for programmatic control
- Redis-to-MIDI bridge (Python + mido)
- PulseAudio null-sink audio routing
- essentia library pre-analysis
- Smart queue builder with BPM/key/energy sequencing
- Systemd service integration

### Out of Scope

- Custom DJ mixing engine
- Stem separation
- Real-time beat detection
- Music recommendation
- Mixxx GUI usage

---

## Write Roots

- `src/`
- `config/`
- `scripts/`
- `tests/`

---

## Done Criteria

- [ ] Mixxx runs headless and plays tracks with beat-matched transitions
- [ ] Transitions are beat-synced (no audible tempo jumps)
- [ ] Harmonic mixing active — adjacent tracks Camelot-compatible
- [ ] Chatbot "skip" transitions within 5 seconds
- [ ] Chatbot "play house" reorders queue to prioritize house tracks
- [ ] Audio routes through PulseAudio to stream pipeline without glitches
- [ ] All 42 tracks have BPM/key/energy metadata
- [ ] Queue builder limits BPM change to <=10 between adjacent tracks
- [ ] 4+ hours unattended without crashes
- [ ] `systemctl start mixxx-dj` starts everything

---

## Validators

- [ ] [external] `systemctl is-active mixxx-dj` returns `active`
- [ ] [external] `python -c "import essentia"` succeeds
- [ ] [external] `cat config/track_metadata.json | python -c "import json,sys; d=json.load(sys.stdin); print(len(d))"` returns 42+
- [ ] [external] `pactl list short sinks | grep mixxx_out` returns a result
- [ ] [external] `python -m pytest tests/ -v` passes
- [ ] [judgment] Beat-matched transitions sound musical — verified by human listening
- [ ] [judgment] Track sequencing flows naturally without jarring genre/energy jumps — verified by human

---

## Eval Plan

docs/cortex/evals/automated-dj-mixing/eval-plan.md (pending)

---

## Approvals

- [x] Contract approval
- [ ] Evals approval

---

## Completion Promise

<!-- CORTEX_PROMISE: automated-dj-mixing-001 COMPLETE -->

---

## Failed Approaches

<!-- Initial contract — no prior attempts. -->

---

## Why Previous Approach Failed

N/A — initial contract

---

## Rollback Hints

- `systemctl stop mixxx-dj` and `systemctl disable mixxx-dj`
- Remove `scripts/mixxx-dj.service` from `/etc/systemd/system/`
- Delete `src/analyze_library.py`, `src/queue_builder.py`, `src/mixxx_bridge.py`
- Delete `config/track_metadata.json`
- `sudo apt remove mixxx` if no longer needed
- `pactl unload-module module-null-sink`

---

## Repair Budget

**max_repair_contracts:** 3
**cooldown_between_repairs:** 1
