"""
validate_tracker_output.py — Validate player_tracker.py JSON output schema and coverage.

Usage:
    python3 validate_tracker_output.py \
        --input ~/veo-clips/player-continuity-tracking/player_ids.json \
        --expected-duration 300 \
        --fps 29.97
"""
import argparse
import json
import os
import sys
from pathlib import Path


REQUIRED_FIELDS = {"frame_idx", "track_id", "bbox", "jersey_ocr", "cosine_sim"}
MIN_COVERAGE_FRACTION = 0.50  # At least 50% of expected frames must have annotations


def validate(input_path: str, expected_duration_s: float, fps: float) -> bool:
    path = Path(input_path)
    if not path.exists():
        print(f"FAIL: {input_path} does not exist")
        return False

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"FAIL: Invalid JSON: {e}")
        return False

    # Handle both raw list format and gap_merge output format
    if isinstance(data, list):
        annotations = data
    elif isinstance(data, dict) and "annotations" in data:
        annotations = data["annotations"]
    else:
        print(f"FAIL: Unexpected format: {type(data)}")
        return False

    if not annotations:
        print("FAIL: No annotations found")
        return False

    print(f"Total annotations: {len(annotations)}")

    # Check schema on sample
    for i, ann in enumerate(annotations[:10]):
        missing = REQUIRED_FIELDS - set(ann.keys())
        if missing:
            print(f"FAIL: Annotation {i} missing fields: {missing}")
            return False

    print(f"Schema: OK (all required fields present in sample)")

    # Check frame coverage
    frame_idxs = set(ann["frame_idx"] for ann in annotations)
    expected_frames = int(expected_duration_s * fps)
    processed_frames = len(range(0, expected_frames, 3))  # SAMPLE_EVERY=3
    coverage = len(frame_idxs) / processed_frames if processed_frames > 0 else 0
    print(f"Frame coverage: {len(frame_idxs)} unique frames / {processed_frames} expected processed = {coverage:.1%}")

    if coverage < MIN_COVERAGE_FRACTION:
        print(f"FAIL: Coverage {coverage:.1%} < {MIN_COVERAGE_FRACTION:.0%} threshold")
        return False

    # Check track diversity
    track_ids = set(ann["track_id"] for ann in annotations)
    print(f"Unique tracks: {len(track_ids)}")

    # Check for OCR results
    ocr_results = [ann["jersey_ocr"] for ann in annotations if ann["jersey_ocr"] is not None]
    print(f"Frames with jersey OCR: {len(ocr_results)} / {len(annotations)} ({len(ocr_results)/len(annotations):.1%})")

    print("\nPASS: All validation checks passed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate tracker output JSON")
    parser.add_argument("--input", required=True)
    parser.add_argument("--expected-duration", type=float, default=300.0,
                        help="Expected video duration that was processed (seconds)")
    parser.add_argument("--fps", type=float, default=29.97)
    args = parser.parse_args()

    ok = validate(args.input, args.expected_duration, args.fps)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
