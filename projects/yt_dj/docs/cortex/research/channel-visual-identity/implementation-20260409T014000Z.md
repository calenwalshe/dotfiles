# Research Dossier: channel-visual-identity — implementation

**Slug:** channel-visual-identity
**Phase:** implementation
**Timestamp:** 20260409T014000Z
**Depth:** standard

---

## Summary

The sun-chasing visual pipeline uses a Python controller that ranks camera feeds by solar position (pvlib), fetches JPEG snapshots, generates dissolve transitions by alpha-blending frames in numpy, and writes raw RGB to a named pipe (FIFO) that FFmpeg reads for continuous RTMP encoding. Text overlays update dynamically via FFmpeg's `drawtext reload=1` reading from a file the controller overwrites on each feed switch. NASA ISS feed is accessible via yt-dlp HLS extraction.

---

## Findings

- **FIFO architecture** solves the continuous-dissolve problem — Python controls frame timing, FFmpeg just encodes
- **pvlib** scores cameras by solar elevation: golden hour (0-6 deg) = 1.0, twilight = 0.4, night = 0.0
- **drawtext reload=1** re-reads overlay text file every frame — zero FFmpeg restarts needed
- **Dissolve** implemented as numpy alpha-blend: `(1-alpha)*old + alpha*new` over 90 frames (3s at 30fps)
- **NASA ISS** accessible via `yt-dlp -g` to extract HLS URL from YouTube stream
- **Main loop**: pick cam → update overlay file → fetch frame → dissolve → hold 45s → repeat

---

## Sources

- pvlib documentation — pvlib-python.readthedocs.io
- FFmpeg drawtext filter — ffmpeg.org/ffmpeg-filters.html
- NASA ISS YouTube stream
