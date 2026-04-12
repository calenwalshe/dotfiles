"""Analyze track library with essentia — BPM, key, energy, loudness."""
import json
import glob
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import essentia.standard as es

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

PROJECT = Path(__file__).parent.parent
CLIPS_DIR = PROJECT / "music" / "clips"
LIBRARY_DIR = PROJECT / "music" / "library"
OUTPUT = PROJECT / "config" / "track_metadata.json"
DB_PATH = PROJECT / "music" / "library.db"

# Camelot wheel mapping
KEY_TO_CAMELOT = {
    "C major": "8B", "G major": "9B", "D major": "10B", "A major": "11B",
    "E major": "12B", "B major": "1B", "F# major": "2B", "Db major": "3B",
    "Ab major": "4B", "Eb major": "5B", "Bb major": "6B", "F major": "7B",
    "A minor": "8A", "E minor": "9A", "B minor": "10A", "F# minor": "11A",
    "C# minor": "12A", "G# minor": "1A", "D# minor": "2A", "Bb minor": "3A",
    "F minor": "4A", "C minor": "5A", "G minor": "6A", "D minor": "7A",
}


def analyze_track(filepath: str) -> dict:
    """Analyze a single track for BPM, key, energy."""
    audio = es.MonoLoader(filename=filepath, sampleRate=44100)()

    # BPM
    bpm, beats, confidence, _, _ = es.RhythmExtractor2013()(audio)

    # Key
    key, scale, key_strength = es.KeyExtractor()(audio)
    key_str = f"{key} {scale}"
    camelot = KEY_TO_CAMELOT.get(key_str, "?")

    # Energy & loudness
    energy = float(es.Energy()(audio))
    loudness = float(es.Loudness()(audio))

    # Duration
    duration = len(audio) / 44100.0

    return {
        "file": filepath,
        "filename": Path(filepath).name,
        "bpm": round(bpm, 1),
        "bpm_confidence": round(float(confidence), 3),
        "key": key_str,
        "camelot": camelot,
        "key_strength": round(float(key_strength), 3),
        "energy": round(energy, 2),
        "loudness": round(loudness, 2),
        "duration_s": round(duration, 1),
    }


def upsert_library_tracks(results: list) -> None:
    """Upsert library_tracks table from analysis results. Soft-deletes removed files."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        for r in results:
            conn.execute(
                """
                INSERT INTO library_tracks
                    (file_path, filename, bpm, camelot, duration_s, first_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    filename   = excluded.filename,
                    bpm        = excluded.bpm,
                    camelot    = excluded.camelot,
                    duration_s = excluded.duration_s,
                    removed_at = NULL
                """,
                (r["file"], r["filename"], r.get("bpm"), r.get("camelot"), r.get("duration_s"), now),
            )
        # Soft-delete files no longer in the scan
        current_paths = {r["file"] for r in results}
        rows = conn.execute(
            "SELECT file_path FROM library_tracks WHERE removed_at IS NULL"
        ).fetchall()
        for (fp,) in rows:
            if fp not in current_paths:
                conn.execute(
                    "UPDATE library_tracks SET removed_at = ? WHERE file_path = ?",
                    (now, fp),
                )
        conn.commit()
        log.info(f"Upserted {len(results)} tracks into library_tracks")
    finally:
        conn.close()


def main():
    tracks = sorted(glob.glob(str(CLIPS_DIR / "*.mp3")))
    tracks += sorted(glob.glob(str(LIBRARY_DIR / "*.mp3")))
    if not tracks:
        log.error(f"No tracks found in {CLIPS_DIR} or {LIBRARY_DIR}")
        sys.exit(1)

    # Load existing metadata to skip already-analyzed tracks
    existing = {}
    if OUTPUT.exists():
        with open(OUTPUT) as f:
            for entry in json.load(f):
                existing[entry["file"]] = entry

    new_tracks = [t for t in tracks if t not in existing]
    log.info(f"Analyzing {len(new_tracks)} new tracks ({len(existing)} already cached)...")
    results = list(existing.values())
    for i, t in enumerate(new_tracks):
        try:
            info = analyze_track(t)
            results.append(info)
            log.info(f"  [{i+1}/{len(new_tracks)}] {info['filename'][:50]} — {info['bpm']} BPM, {info['camelot']}, energy={info['energy']:.0f}")
        except Exception as e:
            log.error(f"  [{i+1}/{len(new_tracks)}] FAILED {Path(t).name}: {e}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)

    log.info(f"Wrote {len(results)} tracks to {OUTPUT}")

    upsert_library_tracks(results)

    # Summary stats
    bpms = [r["bpm"] for r in results]
    log.info(f"BPM range: {min(bpms):.0f} - {max(bpms):.0f}")
    keys = {}
    for r in results:
        keys[r["camelot"]] = keys.get(r["camelot"], 0) + 1
    top_keys = sorted(keys.items(), key=lambda x: -x[1])[:5]
    log.info(f"Top keys: {', '.join(f'{k}({n})' for k,n in top_keys)}")


if __name__ == "__main__":
    main()
