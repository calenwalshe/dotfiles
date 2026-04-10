# Spec: automated-dj-mixing

**Slug:** automated-dj-mixing
**Timestamp:** 20260408T234500Z
**Status:** draft

---

## 1. Problem

The YouTube webcam stream needs continuous, high-quality music playback that sounds like a real DJ set — beat-matched transitions, harmonic compatibility, energy flow — running autonomously 24/7 without manual track selection. The current Liquidsoap playout does time-based crossfades that sound like radio, not like a DJ. The owner has a curated 42-track library spanning Berlin deep house, Burning Man organic house, and Anatolian electronic that needs to be mixed with musical intelligence.

---

## 2. Scope

### In Scope

- Mixxx headless installation and configuration on Linux with Xvfb
- rdircio/autodj controller script integration for beat-matched harmonic mixing
- Virtual MIDI loopback setup (`snd-virmidi`) for programmatic Mixxx control
- Python Redis-to-MIDI bridge for chatbot command relay to Mixxx
- PulseAudio null-sink audio routing from Mixxx to the stream pipeline
- essentia-based track library pre-analysis (BPM, key, energy) with metadata storage
- Smart queue builder that sequences tracks by BPM neighborhood, Camelot key compatibility, and energy curve
- Integration with existing Redis command bus (stream:audio channel)
- Systemd service for Mixxx headless

### Out of Scope

- Building a custom DJ mixing engine from scratch
- Stem separation or advanced audio effects processing
- Real-time beat detection during playback (pre-analysis only)
- Music recommendation or discovery (library is pre-curated)
- Mixxx GUI configuration or desktop usage
- Replacing the owner's ability to manually DJ (this is the autonomous mode)

---

## 3. Architecture Decision

**Chosen approach:** Mixxx headless (via Xvfb) as the mixing engine, controlled through a virtual MIDI bridge connected to the Redis command bus. Pre-analyze the track library with essentia, store metadata in a JSON database, and use a Python queue builder to sequence tracks intelligently before feeding them to Mixxx's Auto DJ.

**Rationale:** Mixxx is a mature, open-source DJ engine with built-in beat matching, BPM sync, and EQ. The rdircio/autodj script adds harmonic mixing and randomized transitions. Using Mixxx avoids building beat alignment and crossfade logic from scratch. The MIDI bridge is the only viable integration path since Mixxx lacks a network API.

### Alternatives Considered

- **Custom Python engine (essentia + pydub):** Rejected — too much work to achieve DJ-quality beat alignment and EQ crossfading. Reinvents what Mixxx already does.
- **Liquidsoap enhanced:** Rejected — fundamentally limited to volume-based crossfades, no beat matching possible.
- **Pre-generated sets:** Rejected — not dynamic, can't respond to chatbot commands, gets repetitive.

---

## 4. Interfaces

- **Mixxx** (local, Xvfb display :1): DJ mixing engine, controlled via virtual MIDI
- **Virtual MIDI** (`snd-virmidi`, `/dev/snd/midiC*D*`): Control channel from Python bridge to Mixxx
- **Redis Pub/Sub** (local, port 6379, channel `stream:audio`): Receives commands from chatbot
- **PulseAudio null-sink** (`mixxx_out`): Audio output from Mixxx, consumed by Liquidsoap or FFmpeg
- **Track metadata store** (`config/track_metadata.json`): BPM, key, energy for all tracks, produced by essentia analysis
- **Mixxx SQLite DB** (`~/.mixxx-headless/mixxxdb.sqlite`): Auto DJ playlist queue, written to by queue builder
- **File system** (`music/clips/*.mp3`): Track library read by Mixxx

---

## 5. Dependencies

- **Mixxx** (v2.4+) — DJ mixing engine with Auto DJ
- **Xvfb** — virtual framebuffer (already installed)
- **snd-virmidi** kernel module — virtual MIDI loopback
- **essentia** — audio analysis (BPM, key, energy)
- **mido** — Python MIDI library for sending CC messages to Mixxx
- **redis-py** — Python Redis client (already installed)
- **PulseAudio** — audio routing via null-sink
- **rdircio/autodj** — Mixxx Auto DJ controller script with harmonic mixing

---

## 6. Risks

- **Mixxx headless stability unknown for 24/7** — Mitigation: systemd watchdog with auto-restart, monitor memory usage, restart Mixxx every 12 hours aligned with YouTube stream restart.
- **Virtual MIDI reliability** — Mitigation: `snd-virmidi` is a kernel module, stable. Fall back to xdotool keyboard simulation if MIDI path fails.
- **PulseAudio routing complexity** — Mitigation: use `module-null-sink` which is well-documented. Test audio path before going live.
- **essentia BPM detection accuracy on downtempo/organic tracks** — Mitigation: manually verify BPM for first batch, flag tracks with low confidence for manual override.
- **rdircio/autodj script compatibility with Mixxx version** — Mitigation: pin Mixxx version, test script on first install.

---

## 7. Sequencing

1. **Install Mixxx + Xvfb setup** — Install Mixxx, verify it runs under Xvfb, configure `--settingsPath`. Checkpoint: Mixxx opens in Xvfb, loads a track, plays audio.

2. **Virtual MIDI + rdircio/autodj** — Load `snd-virmidi`, install autodj controller script, verify MIDI control works. Checkpoint: send MIDI CC from Python, Mixxx responds (skip track, toggle Auto DJ).

3. **Audio routing** — Configure PulseAudio null-sink, route Mixxx output to `mixxx_out`, verify Liquidsoap/FFmpeg can consume the monitor. Checkpoint: audio from Mixxx plays through to the stream pipeline.

4. **essentia library analysis** — Write analysis script, batch-analyze all 42 tracks, store results in `config/track_metadata.json`. Checkpoint: JSON file with BPM, key, energy for all tracks.

5. **Queue builder** — Write Python module that reads track metadata, sequences by BPM neighborhood + Camelot compatibility + energy curve, writes to Mixxx Auto DJ queue. Checkpoint: Mixxx Auto DJ plays a intelligently sequenced set.

6. **Redis bridge** — Write Python bridge that subscribes to `stream:audio`, translates commands to MIDI CC, sends to Mixxx. Checkpoint: chatbot "skip" command → Redis → MIDI → Mixxx skips track.

7. **Systemd service + integration** — Write systemd unit for Mixxx headless + bridge, integrate with existing yt-dj orchestrator. Checkpoint: `systemctl start mixxx-dj` starts everything, chatbot controls work end-to-end.

---

## 8. Tasks

- [ ] Install Mixxx on the server (`sudo apt install mixxx`)
- [ ] Configure Mixxx headless with Xvfb and isolated settings path
- [ ] Clone and install rdircio/autodj controller script
- [ ] Set up snd-virmidi kernel module and verify virtual MIDI ports
- [ ] Write MIDI mapping test script (Python + mido)
- [ ] Configure PulseAudio null-sink for Mixxx audio output
- [ ] Verify audio routing: Mixxx → null-sink → Liquidsoap/FFmpeg
- [ ] Install essentia and write `src/analyze_library.py` — batch BPM/key/energy analysis
- [ ] Run analysis on all 42 tracks, generate `config/track_metadata.json`
- [ ] Write `src/queue_builder.py` — intelligent track sequencing (BPM neighborhoods, Camelot, energy)
- [ ] Write `src/mixxx_bridge.py` — Redis subscriber → MIDI CC sender
- [ ] Define MIDI CC mapping for Auto DJ controls (skip, fade, enable, genre switch)
- [ ] Wire queue builder into Redis command handler (mood/genre commands rebuild queue)
- [ ] Write systemd unit `scripts/mixxx-dj.service`
- [ ] Integration test: chatbot command → Redis → bridge → Mixxx → audio output
- [ ] 4-hour unattended run test

---

## 9. Acceptance Criteria

- [ ] Mixxx runs headless under Xvfb and plays tracks with beat-matched transitions
- [ ] Track transitions are beat-synced (no audible tempo jumps during crossfade)
- [ ] Harmonic mixing is active — adjacent tracks are Camelot-compatible (+/-1 or same key)
- [ ] Chatbot command "skip" causes Mixxx to transition to next track within 5 seconds
- [ ] Chatbot command "play house" reorders the queue to prioritize house tracks (120-128 BPM)
- [ ] Audio from Mixxx routes through PulseAudio to the stream pipeline without glitches
- [ ] All 42 tracks have BPM, key, and energy metadata in `config/track_metadata.json`
- [ ] Queue builder produces a sequence where BPM changes by no more than 10 between adjacent tracks
- [ ] System runs unattended for 4+ hours without crashes or audio interruption
- [ ] `systemctl start mixxx-dj` starts Mixxx + bridge + queue builder
