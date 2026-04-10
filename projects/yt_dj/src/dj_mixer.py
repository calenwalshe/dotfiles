"""DJ Mixer — builds a mixed set from analyzed tracks with beat-aware crossfades.

Uses track metadata (BPM, key/Camelot, energy) to sequence tracks intelligently,
then uses FFmpeg to create crossfaded transitions between them.
"""
import json
import logging
import math
import os
import random
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

PROJECT = Path(__file__).parent.parent
METADATA_PATH = PROJECT / "config" / "track_metadata.json"
OUTPUT_DIR = Path("/tmp/yt_dj_mixed")
PLAYLIST_PATH = Path("/home/agent/projects/yt_dj/queue/playlist.m3u")


def load_metadata() -> list[dict]:
    with open(METADATA_PATH) as f:
        return json.load(f)


def camelot_distance(a: str, b: str) -> int:
    """Distance between two Camelot codes. 0 = same key, 1 = compatible, 2+ = clash."""
    if a == "?" or b == "?":
        return 2
    if a == b:
        return 0

    num_a, letter_a = int(a[:-1]), a[-1]
    num_b, letter_b = int(b[:-1]), b[-1]

    # Same number, different letter (relative major/minor) = compatible
    if num_a == num_b and letter_a != letter_b:
        return 1

    # Same letter, adjacent number = compatible
    if letter_a == letter_b:
        diff = abs(num_a - num_b)
        if diff == 1 or diff == 11:  # wrap around 12 → 1
            return 1

    return 2


def bpm_compatible(a: float, b: float, threshold: float = 0.08) -> bool:
    """Check if two BPMs are within threshold ratio (default 8%)."""
    if a == 0 or b == 0:
        return False
    ratio = max(a, b) / min(a, b)
    return ratio <= (1 + threshold)


def sequence_tracks(tracks: list[dict]) -> list[dict]:
    """Sequence tracks for smooth mixing using BPM neighborhoods + Camelot compatibility."""
    if len(tracks) <= 1:
        return tracks

    # Group into BPM neighborhoods
    tracks_by_bpm = sorted(tracks, key=lambda t: t["bpm"])

    # Greedy nearest-neighbor with Camelot preference
    remaining = list(tracks_by_bpm)
    random.shuffle(remaining)  # randomize starting point within BPM groups
    sequence = [remaining.pop(0)]

    while remaining:
        current = sequence[-1]
        best = None
        best_score = float("inf")

        for candidate in remaining:
            # Score: lower is better
            bpm_diff = abs(candidate["bpm"] - current["bpm"])
            camelot_dist = camelot_distance(candidate["camelot"], current["camelot"])
            energy_diff = abs(candidate.get("energy", 0) - current.get("energy", 0))

            # Weighted score
            score = (bpm_diff * 2) + (camelot_dist * 15) + (energy_diff * 0.001)

            if score < best_score:
                best_score = score
                best = candidate

        remaining.remove(best)
        sequence.append(best)

    return sequence


def crossfade_duration(bpm_a: float, bpm_b: float) -> float:
    """Calculate crossfade duration based on BPM compatibility."""
    if bpm_compatible(bpm_a, bpm_b, threshold=0.05):
        # Similar BPM — longer blend (8 beats at avg BPM)
        avg_bpm = (bpm_a + bpm_b) / 2
        return (8 / avg_bpm) * 60  # 8 beats in seconds
    elif bpm_compatible(bpm_a, bpm_b, threshold=0.10):
        # Moderate difference — shorter blend (4 beats)
        avg_bpm = (bpm_a + bpm_b) / 2
        return (4 / avg_bpm) * 60
    else:
        # Large BPM jump — quick crossfade
        return 2.0


def build_mixed_set(tracks: list[dict], output_path: str):
    """Build a DJ-mixed audio file using FFmpeg crossfades between sequenced tracks."""
    if len(tracks) < 2:
        log.error("Need at least 2 tracks")
        return

    sequence = sequence_tracks(tracks)

    log.info("Sequenced track order:")
    for i, t in enumerate(sequence):
        log.info(f"  {i+1}. {t['filename'][:50]} — {t['bpm']} BPM, {t['camelot']}")

    # Build FFmpeg command with acrossfade filters
    # Strategy: chain pairwise crossfades
    # [track1] -acrossfade-> [track2] -acrossfade-> [track3] ...
    n = len(sequence)

    # For FFmpeg, we need to chain acrossfade filters
    cmd = ["ffmpeg", "-y"]

    # Add all inputs
    for t in sequence:
        cmd.extend(["-i", t["file"]])

    # Build filter chain
    # acrossfade syntax: [a][b]acrossfade=d=DURATION:c1=tri:c2=tri[out]
    filters = []
    current_label = "0:a"

    for i in range(1, n):
        xfade_dur = crossfade_duration(sequence[i-1]["bpm"], sequence[i]["bpm"])
        xfade_dur = min(xfade_dur, 8.0)  # cap at 8 seconds
        xfade_dur = round(xfade_dur, 1)

        next_input = f"{i}:a"
        out_label = f"mix{i}" if i < n - 1 else "mixed"

        # Use equal-power crossfade curve
        filters.append(
            f"[{current_label}][{next_input}]acrossfade=d={xfade_dur}:c1=tri:c2=tri[{out_label}]"
        )
        current_label = out_label

    cmd.extend(["-filter_complex", ";".join(filters)])
    cmd.extend(["-map", f"[mixed]"])
    cmd.extend(["-c:a", "libmp3lame", "-q:a", "2", output_path])

    log.info(f"Mixing {n} tracks with crossfades...")
    log.info(f"Output: {output_path}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        log.error(f"FFmpeg failed: {result.stderr[-500:]}")
        return False

    # Verify output
    duration = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", output_path],
        capture_output=True, text=True
    ).stdout.strip()

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    log.info(f"Mixed set complete: {duration}s, {size_mb:.1f}MB")
    return True


def write_m3u_playlist(tracks: list[dict], path: Path | None = None) -> Path:
    """Write a BPM/key-sequenced M3U playlist for Liquidsoap to consume.

    Sequences tracks intelligently then writes an extended M3U at `path`
    (defaults to PLAYLIST_PATH). Liquidsoap reloads the file on the next
    track boundary when using playlist.reloadable(reload_mode="watch").
    """
    sequence = sequence_tracks(tracks)
    out = path or PLAYLIST_PATH
    out.parent.mkdir(parents=True, exist_ok=True)

    tmp = out.with_suffix(".m3u.tmp")
    with open(tmp, "w") as f:
        f.write("#EXTM3U\n")
        for t in sequence:
            duration = int(t.get("duration_s", -1))
            artist_title = t["filename"].replace(".mp3", "")
            f.write(f"#EXTINF:{duration},{artist_title}\n")
            f.write(f"{t['file']}\n")

    tmp.replace(out)  # atomic rename
    log.info(f"Playlist written: {out} ({len(sequence)} tracks)")
    log.info("Track order:")
    for i, t in enumerate(sequence):
        log.info(f"  {i+1}. {t['filename'][:60]} — {t['bpm']} BPM, {t['camelot']}")
    return out


def main():
    if not METADATA_PATH.exists():
        log.error(f"No metadata at {METADATA_PATH}. Run analyze_library.py first.")
        sys.exit(1)

    tracks = load_metadata()
    log.info(f"Loaded {len(tracks)} tracks")

    # Write Liquidsoap M3U playlist (primary path for radio streaming)
    write_m3u_playlist(tracks)

    # Legacy: also build FFmpeg-mixed set for non-Liquidsoap use
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = str(OUTPUT_DIR / "dj_mix.mp3")

    success = build_mixed_set(tracks, output_path)
    if success:
        log.info(f"DJ mix ready: {output_path}")
        # Also copy to the standard location for the streamer
        merged_path = "/tmp/yt_dj_merged.mp3"
        os.replace(output_path, merged_path)
        log.info(f"Replaced {merged_path} with DJ mix")


if __name__ == "__main__":
    main()
