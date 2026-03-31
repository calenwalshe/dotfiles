#!/usr/bin/env python3
"""
clip_extractor.py — Extract player clips from soccer match footage using Gemini.

Usage:
    python clip_extractor.py \
        --source ~/veo-g15a-match-7mar2026/standard-1920x1080-followcam.mp4 \
        --players 4,10 \
        --kit-colour black \
        --output-dir ~/veo-clips/gemini-player-clip-extraction
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# ── Environment ──────────────────────────────────────────────────────────────

def load_api_key(api_keys_path: Path) -> str:
    """Load GEMINI_API_KEY from ~/.api-keys."""
    if not api_keys_path.exists():
        sys.exit(f"ERROR: {api_keys_path} not found")
    text = api_keys_path.read_text()
    match = re.search(r'GEMINI_API_KEY\s*=\s*["\']?([A-Za-z0-9_\-]+)["\']?', text)
    if not match:
        sys.exit(f"ERROR: GEMINI_API_KEY not found in {api_keys_path}")
    key = match.group(1)
    masked = key[:8] + "..." + key[-4:]
    print(f"  GEMINI_API_KEY: {masked}")
    return key


def check_environment(source: Path, api_keys_path: Path) -> str:
    print("── Environment check ────────────────────────────────────────")
    if not Path("/usr/bin/ffmpeg").exists():
        sys.exit("ERROR: /usr/bin/ffmpeg not found")
    print("  FFmpeg: /usr/bin/ffmpeg ✓")
    if not source.exists():
        sys.exit(f"ERROR: source file not found: {source}")
    size_mb = source.stat().st_size / 1024 / 1024
    print(f"  Source: {source} ({size_mb:.0f} MB) ✓")
    api_key = load_api_key(api_keys_path)
    print("── Environment OK ───────────────────────────────────────────\n")
    return api_key


# ── FFmpeg helpers ────────────────────────────────────────────────────────────

def cut_test_clip(source: Path, duration_minutes: int, output_path: Path) -> None:
    """Cut first N minutes from source using stream copy (fast)."""
    duration_secs = duration_minutes * 60
    cmd = [
        "/usr/bin/ffmpeg", "-y",
        "-ss", "0",
        "-i", str(source),
        "-t", str(duration_secs),
        "-c", "copy",
        str(output_path),
    ]
    print(f"Cutting {duration_minutes}-min test clip...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ERROR: FFmpeg clip cut failed:\n{result.stderr}")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"  Test clip: {output_path} ({size_mb:.1f} MB)\n")


def cut_event_clip(source: Path, start_s: float, end_s: float,
                   buffer_s: float, clip_duration_s: float,
                   output_path: Path) -> None:
    """Cut a single event clip from source with pre/post buffer."""
    t_start = max(0.0, start_s - buffer_s)
    t_end = min(clip_duration_s, end_s + buffer_s)
    duration = t_end - t_start
    cmd = [
        "/usr/bin/ffmpeg", "-y",
        "-ss", f"{t_start:.3f}",
        "-i", str(source),
        "-t", f"{duration:.3f}",
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  WARNING: clip cut failed for {output_path.name}: {result.stderr[-200:]}")


# ── Gemini ────────────────────────────────────────────────────────────────────

def upload_clip(api_key: str, clip_path: Path):
    """Upload clip to Gemini File API and wait until ACTIVE."""
    from google import genai

    client = genai.Client(api_key=api_key)

    print(f"Uploading {clip_path.name} to Gemini File API...")
    uploaded = client.files.upload(
        file=str(clip_path),
        config={"mime_type": "video/mp4"},
    )
    print(f"  File URI: {uploaded.uri}")
    print(f"  Polling for ACTIVE status...", end="", flush=True)

    for _ in range(60):
        f = client.files.get(name=uploaded.name)
        if f.state.name == "ACTIVE":
            print(" ACTIVE\n")
            return client, f
        if f.state.name == "FAILED":
            sys.exit(f"\nERROR: Gemini file processing failed for {uploaded.name}")
        print(".", end="", flush=True)
        time.sleep(3)

    sys.exit("\nERROR: Timed out waiting for file to become ACTIVE")


def load_tracker_output(tracker_path: str) -> list[dict]:
    """
    Load gap-merged tracker output. Returns list of frame_segments dicts or empty list.

    Expected format (from gap_merge.py):
      {"target_player": {"frame_segments": [{"start_frame": N, "end_frame": M}, ...]}, ...}

    Falls back to empty list if file is absent, malformed, or has no segments.
    """
    if not tracker_path or not Path(tracker_path).exists():
        return []
    try:
        with open(tracker_path) as f:
            data = json.load(f)
        segments = data.get("target_player", {}).get("frame_segments", [])
        if isinstance(segments, list):
            return segments
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"  WARNING: Could not parse tracker output from {tracker_path}")
    return []


def frames_to_seconds(frame_idx: int, fps: float = 29.97) -> float:
    """Convert frame index to elapsed seconds."""
    return round(frame_idx / fps, 2)


def build_tracker_context(frame_segments: list[dict], fps: float = 29.97) -> str:
    """
    Build a natural-language description of when the target player appears,
    derived from tracker frame segments.
    """
    if not frame_segments:
        return ""
    ranges = []
    for seg in frame_segments:
        t_start = frames_to_seconds(seg["start_frame"], fps)
        t_end = frames_to_seconds(seg["end_frame"], fps)
        ranges.append(f"{t_start:.1f}s–{t_end:.1f}s")
    joined = ", ".join(ranges)
    return (
        f"\n\nTracker context: Pre-processing analysis has identified the target player "
        f"in the following time ranges: {joined}. "
        f"Use these ranges to focus your search, but still apply your own visual judgment "
        f"for confirmation — include an event only if you are visually confident."
    )


def build_prompt(players: list[int], kit_colour: str, min_duration: float,
                 tracker_context: str = "") -> str:
    numbers_str = " and ".join(str(p) for p in players)
    return f"""Watch this soccer match clip carefully.

Identify ALL moments where players wearing jersey number {numbers_str} in {kit_colour} kit are actively involved in play. Active involvement includes: touching the ball, making a run to receive a pass, defending, heading, shooting, tackling, or any notable movement directly related to the play.

Return ONLY a valid JSON array — no markdown, no explanation, no surrounding text. Each element must have exactly these fields:
{{
  "player": <jersey number as integer>,
  "start_s": <total elapsed seconds as a decimal float>,
  "end_s": <total elapsed seconds as a decimal float>,
  "action": "<one short phrase describing the action>"
}}

IMPORTANT — timestamp format: start_s and end_s must be TOTAL ELAPSED SECONDS from the beginning of the clip, as a plain decimal number.
- Do NOT use MM:SS or M.SS notation.
- Example: something happening at 2 minutes 30 seconds = 150.0, NOT 2.30 or 2:30.
- Example: something at 47 seconds = 47.0. Something at 1 minute 15 seconds = 75.0.

Rules:
- Only include moments where the jersey number is visible and you are confident in the identification
- Minimum event duration: {min_duration} seconds — each event must span at least {min_duration}s (end_s - start_s >= {min_duration})
- If a player appears multiple times, create a separate entry for each distinct moment
- If neither player {numbers_str} is clearly visible in the clip, return an empty array: []{tracker_context}

Respond with the JSON array only.
"""


def detect_events(client, uploaded_file, prompt: str, raw_output_path: Path) -> list[dict]:
    """Call Gemini and return parsed event list."""
    from google.genai import types

    print("Sending detection prompt to Gemini 2.5 Flash...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(parts=[
                types.Part(
                    file_data=types.FileData(
                        file_uri=uploaded_file.uri,
                        mime_type="video/mp4",
                    )
                ),
                types.Part(text=prompt),
            ])
        ],
    )

    raw_text = response.text.strip()

    # Write raw response to disk before any parsing
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text(raw_text)
    print(f"  Raw response written to: {raw_output_path}")

    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        events = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"\nERROR: Could not parse Gemini response as JSON: {e}")
        print(f"Raw response:\n{raw_text[:500]}")
        sys.exit(1)

    if not isinstance(events, list):
        sys.exit(f"ERROR: Expected JSON array, got {type(events).__name__}")

    # Validate schema
    required_fields = {"player", "start_s", "end_s"}
    for i, ev in enumerate(events):
        missing = required_fields - set(ev.keys())
        if missing:
            sys.exit(f"ERROR: Event {i} missing fields: {missing}\nEvent: {ev}")

    print(f"  {len(events)} event(s) detected\n")
    return events


def delete_file_api_upload(client, uploaded_file) -> None:
    """Delete a Gemini File API upload immediately after use."""
    try:
        client.files.delete(name=uploaded_file.name)
        print(f"  File API upload deleted: {uploaded_file.name}")
    except Exception as e:
        print(f"  WARNING: Could not delete File API upload {uploaded_file.name}: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract player clips from soccer footage using Gemini."
    )
    parser.add_argument("--source", required=True, type=Path,
                        help="Path to source MP4 file")
    parser.add_argument("--players", required=True,
                        help="Comma-separated jersey numbers, e.g. 4,10")
    parser.add_argument("--kit-colour", required=True,
                        help="Kit colour, e.g. black")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="Output directory for clips and logs")
    parser.add_argument("--clip-length", type=int, default=5,
                        help="Test clip length in minutes (default: 5)")
    parser.add_argument("--buffer", type=float, default=5.0,
                        help="Seconds of buffer before/after each event (default: 5)")
    parser.add_argument("--min-duration", type=float, default=2.0,
                        help="Minimum event duration to keep in seconds (default: 2)")
    parser.add_argument("--api-keys", type=Path,
                        default=Path.home() / ".api-keys",
                        help="Path to api-keys file (default: ~/.api-keys)")
    parser.add_argument("--tracker-output", type=str, default=None,
                        help="Path to gap-merged player_ids.json from player_tracker.py")
    parser.add_argument("--no-tracker-output", action="store_true",
                        help="Explicitly disable tracker context (baseline/regression mode)")
    args = parser.parse_args()

    players = [int(p.strip()) for p in args.players.split(",")]
    source = args.source.expanduser()
    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load tracker output (if provided and not explicitly disabled)
    tracker_context = ""
    if not args.no_tracker_output and args.tracker_output:
        tracker_path = str(Path(args.tracker_output).expanduser())
        frame_segments = load_tracker_output(tracker_path)
        if frame_segments:
            tracker_context = build_tracker_context(frame_segments)
            print(f"  Tracker output loaded: {len(frame_segments)} target player segments")
        else:
            print(f"  Tracker output: no segments found (baseline mode)")

    # Phase 1: Environment check
    api_key = check_environment(source, args.api_keys.expanduser())

    # Phase 2: Cut test clip
    with tempfile.TemporaryDirectory() as tmpdir:
        test_clip = Path(tmpdir) / "test_clip.mp4"
        cut_test_clip(source, args.clip_length, test_clip)
        clip_duration_s = args.clip_length * 60.0

        # Phase 3: Upload to Gemini
        client, uploaded_file = upload_clip(api_key, test_clip)

        # Phase 4: Detect events
        prompt = build_prompt(players, args.kit_colour, args.min_duration, tracker_context)
        raw_path = output_dir / "raw-response.json"
        events = detect_events(client, uploaded_file, prompt, raw_path)

        # Phase 4b: Delete File API upload immediately (privacy + eval requirement)
        delete_file_api_upload(client, uploaded_file)

    # Phase 5: Filter short events
    before_filter = len(events)
    events = [
        ev for ev in events
        if (float(ev["end_s"]) - float(ev["start_s"])) >= args.min_duration
    ]
    filtered_count = before_filter - len(events)
    if filtered_count:
        print(f"Filtered {filtered_count} event(s) shorter than {args.min_duration}s\n")

    skipped_oob = 0  # initialised here; updated after out-of-bounds filter below

    if not events:
        print("No events remaining after filtering.")
        print(f"\nSUMMARY: 0 clips written | {filtered_count} too-short filtered | dir: {output_dir}")
        return

    # Phase 6: Cut clips — skip events that start beyond the clip length
    valid_events = [ev for ev in events if float(ev["start_s"]) < clip_duration_s]
    skipped_oob = len(events) - len(valid_events)
    if skipped_oob:
        print(f"Skipped {skipped_oob} event(s) with timestamps beyond clip length ({clip_duration_s:.0f}s)\n")

    print(f"Cutting {len(valid_events)} clip(s) with {args.buffer}s buffer...")
    clips_written = 0
    total_duration = 0.0

    for ev in valid_events:
        player = int(ev["player"])
        start_s = float(ev["start_s"])
        end_s = float(ev["end_s"])
        action = ev.get("action", "")

        mins = int(start_s) // 60
        secs = int(start_s) % 60
        ts_str = f"{mins:02d}m{secs:02d}s"
        filename = f"{player}-{ts_str}.mp4"
        out_path = output_dir / filename

        cut_event_clip(source, start_s, end_s, args.buffer, clip_duration_s, out_path)

        t_start = max(0.0, start_s - args.buffer)
        t_end = min(clip_duration_s, end_s + args.buffer)
        clipped_duration = max(0.0, t_end - t_start)
        total_duration += clipped_duration
        clips_written += 1
        print(f"  [{player}] {ts_str}  {action}  → {filename}")

    print(f"\nSUMMARY: {clips_written} clip(s) written | "
          f"{filtered_count} too-short filtered | "
          f"{skipped_oob} out-of-bounds skipped | "
          f"total output: {total_duration:.1f}s | "
          f"dir: {output_dir}")


if __name__ == "__main__":
    main()
