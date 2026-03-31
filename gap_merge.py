"""
gap_merge.py — Post-process tracker annotations to merge fragmented tracklets.

For the target player, any gap < GAP_THRESHOLD_S seconds between consecutive
detected segments is treated as an occlusion and the segments are merged.

Usage:
    python3 gap_merge.py \
        --input ~/veo-clips/player-continuity-tracking/player_ids_raw.json \
        --output ~/veo-clips/player-continuity-tracking/player_ids.json \
        --player-jersey 4 \
        --fps 29.97 \
        --gap-threshold 5.0
"""
import argparse
import json
import logging
import os
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GAP_THRESHOLD_S = 5.0   # Merge gaps shorter than this (seconds)
COSINE_TARGET_THRESH = 0.7  # Similarity threshold to flag as target player


def find_target_track_ids(
    annotations: list[dict],
    player_jersey: Optional[str],
    fps: float,
) -> set[int]:
    """
    Identify which track_ids belong to the target player.

    Strategy: collect tracks where jersey_ocr matches player_jersey OR
    where cosine_sim >= COSINE_TARGET_THRESH. Use majority vote if both signals available.
    """
    jersey_track_counts: dict[int, int] = {}
    cosine_track_counts: dict[int, int] = {}

    for ann in annotations:
        tid = ann["track_id"]
        if player_jersey and ann.get("jersey_ocr") == player_jersey:
            jersey_track_counts[tid] = jersey_track_counts.get(tid, 0) + 1
        if ann.get("cosine_sim", 0.0) >= COSINE_TARGET_THRESH:
            cosine_track_counts[tid] = cosine_track_counts.get(tid, 0) + 1

    target_ids = set()

    if jersey_track_counts:
        # Pick the track with most jersey matches
        best_jersey_track = max(jersey_track_counts, key=jersey_track_counts.get)
        target_ids.add(best_jersey_track)
        logger.info(
            "Target player track by jersey '%s': track_id=%d (%d matches)",
            player_jersey, best_jersey_track, jersey_track_counts[best_jersey_track],
        )

    if cosine_track_counts:
        best_cosine_track = max(cosine_track_counts, key=cosine_track_counts.get)
        target_ids.add(best_cosine_track)
        logger.info(
            "Target player track by cosine sim: track_id=%d (%d frames above %.2f)",
            best_cosine_track, cosine_track_counts[best_cosine_track], COSINE_TARGET_THRESH,
        )

    return target_ids


def build_frame_segments(
    annotations: list[dict],
    target_track_ids: set[int],
) -> list[tuple[int, int]]:
    """
    Build list of (start_frame, end_frame) segments where target player is present.
    Sorted by start_frame.
    """
    target_frames = sorted(set(
        ann["frame_idx"]
        for ann in annotations
        if ann["track_id"] in target_track_ids
    ))
    if not target_frames:
        return []

    segments = []
    seg_start = target_frames[0]
    seg_end = target_frames[0]

    for f in target_frames[1:]:
        if f == seg_end + 1 or f == seg_end:
            seg_end = f
        else:
            segments.append((seg_start, seg_end))
            seg_start = f
            seg_end = f
    segments.append((seg_start, seg_end))
    return segments


def merge_segments(
    segments: list[tuple[int, int]],
    gap_threshold_frames: int,
) -> list[tuple[int, int]]:
    """
    Merge consecutive segments where the gap is < gap_threshold_frames.
    Returns merged list of (start, end) tuples.
    """
    if not segments:
        return []

    merged = [segments[0]]
    for seg in segments[1:]:
        prev_start, prev_end = merged[-1]
        gap = seg[0] - prev_end
        if gap < gap_threshold_frames:
            # Merge: extend previous segment
            merged[-1] = (prev_start, seg[1])
        else:
            merged.append(seg)
    return merged


def apply_gap_merge(
    annotations: list[dict],
    raw_segments: list[tuple[int, int]],
    merged_segments: list[tuple[int, int]],
    target_track_ids: set[int],
) -> list[dict]:
    """
    Return annotations with gap_merged=True added to annotations in merged ranges
    that were previously gaps (i.e., target player not detected but now included).
    """
    # Build set of frames in merged ranges but NOT in original target frames
    merged_frame_ranges = set()
    for start, end in merged_segments:
        merged_frame_ranges.update(range(start, end + 1))

    raw_frame_ranges = set()
    for start, end in raw_segments:
        raw_frame_ranges.update(range(start, end + 1))

    gap_filled_frames = merged_frame_ranges - raw_frame_ranges

    # Add gap_merged flag to all annotations
    result = []
    for ann in annotations:
        ann_copy = dict(ann)
        if ann["frame_idx"] in gap_filled_frames and ann["track_id"] not in target_track_ids:
            ann_copy["gap_merged"] = True
        else:
            ann_copy["gap_merged"] = False
        result.append(ann_copy)

    return result


def run_gap_merge(
    input_path: str,
    output_path: str,
    player_jersey: Optional[str],
    fps: float,
    gap_threshold_s: float,
) -> dict:
    logger.info("Loading annotations from %s", input_path)
    with open(input_path) as f:
        annotations = json.load(f)
    logger.info("Loaded %d annotations", len(annotations))

    gap_threshold_frames = int(gap_threshold_s * fps)
    logger.info("Gap threshold: %.1fs = %d frames at %.2f fps", gap_threshold_s, gap_threshold_frames, fps)

    target_ids = find_target_track_ids(annotations, player_jersey, fps)
    if not target_ids:
        logger.warning("No target player tracks found — output will be unmodified")
        merged_annotations = [{**ann, "gap_merged": False} for ann in annotations]
        target_frames_merged = []
    else:
        raw_segments = build_frame_segments(annotations, target_ids)
        logger.info("Raw segments: %d, covering %d frames",
                    len(raw_segments), sum(e - s + 1 for s, e in raw_segments))

        merged_segments = merge_segments(raw_segments, gap_threshold_frames)
        gaps_merged = len(raw_segments) - len(merged_segments)
        logger.info("After gap-merge: %d segments (merged %d gaps)",
                    len(merged_segments), gaps_merged)

        merged_annotations = apply_gap_merge(annotations, raw_segments, merged_segments, target_ids)
        target_frames_merged = [{"start_frame": s, "end_frame": e} for s, e in merged_segments]

    result = {
        "annotations": merged_annotations,
        "target_player": {
            "jersey": player_jersey,
            "track_ids": list(target_ids),
            "frame_segments": target_frames_merged,
            "total_target_frames": sum(
                seg["end_frame"] - seg["start_frame"] + 1 for seg in target_frames_merged
            ),
        },
        "video_fps": fps,
        "gap_threshold_s": gap_threshold_s,
        "gap_threshold_frames": gap_threshold_frames,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=None, separators=(",", ":"))

    logger.info(
        "Gap-merge complete: %d target frame segments, %d total target frames",
        len(target_frames_merged),
        result["target_player"]["total_target_frames"],
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="Tracklet gap-merge post-processor")
    parser.add_argument("--input", default=os.path.expanduser(
        "~/veo-clips/player-continuity-tracking/player_ids_raw.json"
    ))
    parser.add_argument("--output", default=os.path.expanduser(
        "~/veo-clips/player-continuity-tracking/player_ids.json"
    ))
    parser.add_argument("--player-jersey", default="4")
    parser.add_argument("--fps", type=float, default=29.97)
    parser.add_argument("--gap-threshold", type=float, default=GAP_THRESHOLD_S,
                        help="Merge gaps shorter than this (seconds)")
    args = parser.parse_args()
    run_gap_merge(args.input, args.output, args.player_jersey, args.fps, args.gap_threshold)


if __name__ == "__main__":
    main()
