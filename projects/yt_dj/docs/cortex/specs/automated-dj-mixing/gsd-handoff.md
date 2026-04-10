# GSD Handoff: automated-dj-mixing

**Slug:** automated-dj-mixing
**Timestamp:** 20260408T234500Z
**Status:** draft

---

## Objective

Add automated DJ mixing to the YouTube webcam stream by running Mixxx headless with the rdircio/autodj script for beat-matched harmonic transitions, controlled via a Redis-to-MIDI bridge from the chatbot, with tracks pre-analyzed by essentia and sequenced by a smart queue builder.

---

## Deliverables

- `src/analyze_library.py` — essentia batch analysis script (BPM, key, energy)
- `src/queue_builder.py` — intelligent track sequencer (BPM neighborhoods, Camelot, energy curves)
- `src/mixxx_bridge.py` — Redis-to-MIDI bridge for Mixxx control
- `config/track_metadata.json` — pre-analyzed track metadata
- `scripts/mixxx-dj.service` — systemd unit for Mixxx headless + bridge
- `scripts/setup-mixxx.sh` — installation and configuration script

---

## Requirements

- None formalized

---

## Tasks

- [ ] Install Mixxx on the server
- [ ] Configure Mixxx headless with Xvfb and isolated settings path
- [ ] Clone and install rdircio/autodj controller script
- [ ] Set up snd-virmidi kernel module and verify virtual MIDI ports
- [ ] Write MIDI mapping test script (Python + mido)
- [ ] Configure PulseAudio null-sink for Mixxx audio output
- [ ] Verify audio routing: Mixxx → null-sink → Liquidsoap/FFmpeg
- [ ] Install essentia and write `src/analyze_library.py`
- [ ] Run analysis on all 42 tracks, generate `config/track_metadata.json`
- [ ] Write `src/queue_builder.py`
- [ ] Write `src/mixxx_bridge.py`
- [ ] Define MIDI CC mapping for Auto DJ controls
- [ ] Wire queue builder into Redis command handler
- [ ] Write systemd unit `scripts/mixxx-dj.service`
- [ ] Integration test: chatbot → Redis → bridge → Mixxx → audio
- [ ] 4-hour unattended run test

---

## Acceptance Criteria

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

## Contract Link

docs/cortex/contracts/automated-dj-mixing/contract-001.md
