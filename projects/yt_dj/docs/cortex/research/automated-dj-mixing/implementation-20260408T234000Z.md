# Research Dossier: automated-dj-mixing — implementation

**Slug:** automated-dj-mixing
**Phase:** implementation
**Timestamp:** 20260408T234000Z
**Depth:** standard

---

## Summary

Mixxx runs headless via Xvfb (no native `--headless` flag). Control flows through a virtual MIDI loopback (`snd-virmidi`) bridged to Redis via a Python script using `mido`. Audio routes from Mixxx through PulseAudio null-sink to Liquidsoap/FFmpeg. The `rdircio/autodj` controller script drops into `~/.mixxx/controllers/`. Track library pre-analysis uses essentia's `RhythmExtractor2013` + `KeyExtractor` to populate a JSON/Redis metadata store that informs queue ordering.

---

## Findings

### Mixxx Headless Setup
- No native `--headless` — use `Xvfb :1 -screen 0 1024x768x24` + `DISPLAY=:1 mixxx`
- Isolate config with `--settingsPath ~/.mixxx-headless`
- rdircio/autodj: copy `AutoDJ.js` + `AutoDJ.midi.xml` to `~/.mixxx-headless/controllers/`
- Virtual MIDI via `sudo modprobe snd-virmidi`

### Redis-to-Mixxx Bridge
- Python `mido` library sends MIDI CC to virtual port
- Map Redis commands to MIDI CC values: skip, fade_now, enable/disable Auto DJ
- Auto DJ controls: `[AutoDJ],enabled`, `[AutoDJ],skip_next`, `[AutoDJ],fade_now`
- No REST API — MIDI bridge is the integration path

### Audio Routing
- PulseAudio null-sink: `pactl load-module module-null-sink sink_name=mixxx_out`
- Liquidsoap: `input.pulseaudio(device="mixxx_out.monitor")`
- FFmpeg: `-f pulse -i mixxx_out.monitor`
- JACK/PipeWire also viable but more complex

### Queue Management
- Direct SQLite: insert into `PlaylistTracks` in `mixxxdb.sqlite`
- MIDI-mapped controls for Auto DJ enable/skip/fade
- No external queue API — SQLite + library rescan is the path

### Essentia Pre-Analysis
- `RhythmExtractor2013` for BPM, `KeyExtractor` for key, `Energy` + `Loudness` for energy
- Batch-analyze all tracks, store in JSON file alongside library
- Feed metadata into queue ordering logic

---

## Sources

- Mixxx documentation — mixxx.org/manual/latest/
- rdircio/autodj — github.com/rdircio/autodj
- essentia documentation — essentia.upf.edu
- mido MIDI library — mido.readthedocs.io
- PulseAudio module-null-sink — freedesktop.org/wiki/Software/PulseAudio
