"""
player_tracker.py — Frame-streaming ByteTrack-style player tracker.

Pipeline: YOLOv8n (ONNX) → OSNet Re-ID (ONNX) → EasyOCR → IoU tracker → player_ids.json

Usage:
    python3 player_tracker.py \
        --video ~/veo-g15a-match-7mar2026/standard-1920x1080-followcam.mp4 \
        --player-jersey 4 \
        --output ~/veo-clips/player-continuity-tracking/player_ids.json

    # Test frames (resilience):
    python3 player_tracker.py --test-frame black
    python3 player_tracker.py --test-frame blur
"""
import argparse
import json
import logging
import os
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import onnxruntime as ort
from tqdm import tqdm

warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

COSINE_CONFIDENT = 0.7   # Above this: confirmed match
COSINE_FALLBACK = 0.6    # Above this: candidate match (combined with IoU)
YOLO_IMGSZ = 640
YOLO_CONF = 0.3
NMS_IOU = 0.45
SAMPLE_EVERY = 3          # Process every Nth frame
PROFILE_WINDOW = 30.0     # Build player profile from first N seconds
TORSO_FRACTION = 0.40     # Top fraction of bbox for jersey OCR
MAX_GALLERY_SIZE = 20     # Max reference embeddings per profile
IOU_MATCH_THRESHOLD = 0.3 # Minimum IoU to associate detection to track
MAX_LOST_FRAMES = 10      # Frames before a tracklet is considered lost

# ── Utility functions ──────────────────────────────────────────────────────────


def letterbox(img: np.ndarray, target_size: int = 640):
    """Resize with letterbox padding to square. Returns (canvas, scale, pad_top, pad_left)."""
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h))
    pad_top = (target_size - new_h) // 2
    pad_left = (target_size - new_w) // 2
    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    canvas[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized
    return canvas, scale, pad_top, pad_left


def normalize_embedding(v: np.ndarray) -> np.ndarray:
    """Return L2-normalized vector; returns zeros if input is zero."""
    norm = np.linalg.norm(v)
    if norm < 1e-8:
        return np.zeros_like(v)
    return v / norm


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two unit vectors."""
    return float(np.dot(a, b))


def iou(box_a: list, box_b: list) -> float:
    """IoU between two [x1, y1, x2, y2] boxes."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def extract_torso_crop(frame: np.ndarray, bbox: tuple) -> np.ndarray:
    """Extract top TORSO_FRACTION of the person bounding box for jersey OCR."""
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(frame.shape[1], int(x2)), min(frame.shape[0], int(y2))
    h = y2 - y1
    torso_y2 = y1 + max(1, int(h * TORSO_FRACTION))
    torso_y2 = min(torso_y2, frame.shape[0])
    return frame[y1:torso_y2, x1:x2]


def preprocess_crop_for_osnet(crop_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Preprocess a BGR image crop for OSNet. Returns CHW float32 or None."""
    if crop_bgr is None or crop_bgr.size == 0:
        return None
    h, w = crop_bgr.shape[:2]
    if h < 8 or w < 8:
        return None
    img = cv2.resize(crop_bgr, (128, 256))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img = (img - mean) / std
    return img.transpose(2, 0, 1)  # CHW


def make_annotation(
    frame_idx: int,
    track_id: int,
    bbox: tuple,
    jersey_ocr: Optional[str],
    cosine_sim_val: float,
) -> dict:
    """Build a per-frame annotation dict."""
    return {
        "frame_idx": frame_idx,
        "track_id": track_id,
        "bbox": list(bbox),
        "jersey_ocr": jersey_ocr,
        "cosine_sim": round(cosine_sim_val, 4),
    }


# ── Player profile ─────────────────────────────────────────────────────────────


class PlayerProfile:
    """Stores reference embeddings and confirmed jersey number for the target player."""

    def __init__(self, jersey_number: Optional[str] = None):
        self.jersey_number = jersey_number
        self.reference_embeddings: list[np.ndarray] = []
        self._mean: Optional[np.ndarray] = None

    def add_reference_embedding(self, emb: np.ndarray) -> None:
        if len(self.reference_embeddings) < MAX_GALLERY_SIZE:
            self.reference_embeddings.append(emb)
            self._mean = None  # Invalidate cache

    def get_mean_embedding(self) -> Optional[np.ndarray]:
        if not self.reference_embeddings:
            return None
        if self._mean is None:
            mean = np.mean(self.reference_embeddings, axis=0)
            self._mean = normalize_embedding(mean)
        return self._mean

    def similarity_to(self, emb: np.ndarray) -> float:
        mean = self.get_mean_embedding()
        if mean is None:
            return 0.0
        return cosine_sim(emb, mean)

    def is_built(self) -> bool:
        return len(self.reference_embeddings) >= 3


# ── IoU Tracker (ByteTrack-style, CPU-only) ────────────────────────────────────


@dataclass
class Tracklet:
    track_id: int
    bbox: list        # [x1, y1, x2, y2]
    embedding: Optional[np.ndarray] = None
    lost_frames: int = 0
    confirmed: bool = False


class IoUTracker:
    """Simple IoU + cosine similarity multi-object tracker."""

    def __init__(self):
        self._next_id = 1
        self.tracklets: dict[int, Tracklet] = {}

    def update(
        self,
        detections: list[dict],
        embeddings: list[Optional[np.ndarray]],
    ) -> list[dict]:
        """
        Match detections to existing tracklets. Returns list of
        {track_id, bbox, embedding, is_new} for each detection.
        """
        # Mark all tracklets as potentially lost
        for t in self.tracklets.values():
            t.lost_frames += 1

        assigned = {}  # det_idx -> track_id
        used_tracks = set()

        # Match by IoU + cosine similarity
        if self.tracklets and detections:
            track_ids = list(self.tracklets.keys())
            for det_idx, det in enumerate(detections):
                best_track = None
                best_score = -1.0
                for tid in track_ids:
                    if tid in used_tracks:
                        continue
                    t = self.tracklets[tid]
                    iou_score = iou(det["bbox"], t.bbox)
                    if iou_score < IOU_MATCH_THRESHOLD:
                        continue
                    # Boost score with appearance similarity if both have embeddings
                    emb = embeddings[det_idx]
                    if emb is not None and t.embedding is not None:
                        cos = cosine_sim(emb, t.embedding)
                        score = 0.5 * iou_score + 0.5 * cos
                    else:
                        score = iou_score
                    if score > best_score:
                        best_score = score
                        best_track = tid
                if best_track is not None:
                    assigned[det_idx] = best_track
                    used_tracks.add(best_track)

        # Update matched tracklets
        results = []
        for det_idx, det in enumerate(detections):
            emb = embeddings[det_idx]
            if det_idx in assigned:
                tid = assigned[det_idx]
                t = self.tracklets[tid]
                t.bbox = det["bbox"]
                t.lost_frames = 0
                if emb is not None:
                    t.embedding = emb
                results.append({"track_id": tid, "bbox": det["bbox"], "is_new": False})
            else:
                # New tracklet
                tid = self._next_id
                self._next_id += 1
                self.tracklets[tid] = Tracklet(
                    track_id=tid,
                    bbox=det["bbox"],
                    embedding=emb,
                )
                results.append({"track_id": tid, "bbox": det["bbox"], "is_new": True})

        # Remove stale tracklets
        stale = [tid for tid, t in self.tracklets.items() if t.lost_frames > MAX_LOST_FRAMES]
        for tid in stale:
            del self.tracklets[tid]

        return results


# ── ONNX Inference ─────────────────────────────────────────────────────────────


def build_yolo_session(model_path: str) -> ort.InferenceSession:
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(model_path, sess_options=opts, providers=["CPUExecutionProvider"])


def build_osnet_session(model_path: str) -> ort.InferenceSession:
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(model_path, sess_options=opts, providers=["CPUExecutionProvider"])


def run_yolo(session: ort.InferenceSession, frame: np.ndarray, orig_h: int, orig_w: int) -> list:
    """Run YOLOv8n ONNX on frame. Returns list of {bbox, conf}."""
    lb, scale, pad_top, pad_left = letterbox(frame, YOLO_IMGSZ)
    inp = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    inp = inp.transpose(2, 0, 1)[np.newaxis, :]

    raw = session.run(None, {"images": inp})[0]  # (1, 84, 8400)
    preds = raw[0].T  # (8400, 84)
    boxes_xywh = preds[:, :4]
    person_scores = preds[:, 4]  # class 0 = person
    mask = person_scores > YOLO_CONF
    if not mask.any():
        return []

    bxywh = boxes_xywh[mask]
    bscores = person_scores[mask]
    x1 = (bxywh[:, 0] - bxywh[:, 2] / 2 - pad_left) / scale
    y1 = (bxywh[:, 1] - bxywh[:, 3] / 2 - pad_top) / scale
    x2 = (bxywh[:, 0] + bxywh[:, 2] / 2 - pad_left) / scale
    y2 = (bxywh[:, 1] + bxywh[:, 3] / 2 - pad_top) / scale

    x1 = np.clip(x1, 0, orig_w).astype(int)
    y1 = np.clip(y1, 0, orig_h).astype(int)
    x2 = np.clip(x2, 0, orig_w).astype(int)
    y2 = np.clip(y2, 0, orig_h).astype(int)

    bboxes_for_nms = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).tolist()
    indices = cv2.dnn.NMSBoxes(bboxes_for_nms, bscores.tolist(), YOLO_CONF, NMS_IOU)
    if len(indices) == 0:
        return []

    result = []
    for i in indices.flatten():
        result.append({"bbox": [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])], "conf": float(bscores[i])})
    return result


def run_osnet_batch(
    session: ort.InferenceSession, crops: list[np.ndarray]
) -> list[Optional[np.ndarray]]:
    """Run OSNet on a batch of preprocessed crop tensors. Returns normalized embeddings."""
    if not crops:
        return []
    valid_indices = [i for i, c in enumerate(crops) if c is not None]
    if not valid_indices:
        return [None] * len(crops)

    batch = np.stack([crops[i] for i in valid_indices], axis=0)
    raw = session.run(None, {"input": batch})[0]  # (N, 512)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1.0, norms)
    normed = list(raw / norms)

    result: list[Optional[np.ndarray]] = [None] * len(crops)
    for out_idx, orig_idx in enumerate(valid_indices):
        result[orig_idx] = normed[out_idx]
    return result


# ── Jersey OCR ─────────────────────────────────────────────────────────────────


def build_ocr_reader():
    """Build EasyOCR reader (lazy import to avoid slow startup)."""
    import easyocr
    return easyocr.Reader(["en"], gpu=False, verbose=False)


def ocr_jersey_number(reader, torso_crop: np.ndarray) -> Optional[str]:
    """Run EasyOCR on torso crop, return best numeric string or None."""
    if torso_crop is None or torso_crop.size == 0 or torso_crop.shape[0] < 10:
        return None
    try:
        results = reader.readtext(torso_crop, allowlist="0123456789", detail=1)
        if not results:
            return None
        # Pick highest-confidence result that looks like a jersey number (1-3 digits)
        best = max(results, key=lambda r: r[2])
        text = best[1].strip()
        if text.isdigit() and 1 <= len(text) <= 3:
            return text
    except Exception:
        logger.warning("OCR failed on crop", exc_info=False)
    return None


# ── Main tracking loop ─────────────────────────────────────────────────────────


def run_tracker(
    video_path: str,
    player_jersey: Optional[str],
    output_path: str,
    yolo_onnx: str,
    osnet_onnx: str,
    end_time: Optional[float] = None,
    sample_rate: int = SAMPLE_EVERY,
) -> None:
    cap = cv2.VideoCapture(video_path)
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    end_frame = int(end_time * fps_video) if end_time is not None else total_frames
    end_frame = min(end_frame, total_frames)
    profile_end_frame = int(PROFILE_WINDOW * fps_video)

    yolo_sess = build_yolo_session(yolo_onnx)
    osnet_sess = build_osnet_session(osnet_onnx)
    ocr_reader = build_ocr_reader()
    tracker = IoUTracker()

    player_profile = PlayerProfile(jersey_number=player_jersey)
    annotations: list[dict] = []

    frames_to_process = len(range(0, end_frame, sample_rate))
    logger.info(
        "Starting tracker: %d video frames, processing every %d, ~%d processed frames",
        end_frame, sample_rate, frames_to_process,
    )

    with tqdm(total=frames_to_process, desc="Tracking") as pbar:
        frame_idx = 0
        while frame_idx < end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_rate == 0:
                detections = run_yolo(yolo_sess, frame, orig_h, orig_w)

                # Prepare OSNet crops for all detections
                crops = []
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    crop = frame[y1:y2, x1:x2]
                    crops.append(preprocess_crop_for_osnet(crop))

                embeddings = run_osnet_batch(osnet_sess, crops)

                # Update tracker
                tracked = tracker.update(detections, embeddings)

                # Build player profile during first PROFILE_WINDOW seconds
                building_profile = frame_idx < profile_end_frame and not player_profile.is_built()

                for i, t in enumerate(tracked):
                    emb = embeddings[i] if i < len(embeddings) else None
                    bbox = t["bbox"]
                    torso = extract_torso_crop(frame, tuple(bbox))
                    jersey = ocr_jersey_number(ocr_reader, torso)

                    # Profile construction: match by jersey number
                    if building_profile and player_jersey and jersey == player_jersey and emb is not None:
                        player_profile.add_reference_embedding(emb)

                    # Compute similarity to target player profile
                    sim = 0.0
                    if emb is not None and player_profile.is_built():
                        sim = player_profile.similarity_to(emb)

                    annotations.append(make_annotation(
                        frame_idx=frame_idx,
                        track_id=t["track_id"],
                        bbox=tuple(bbox),
                        jersey_ocr=jersey,
                        cosine_sim_val=sim,
                    ))

                pbar.update(1)

            frame_idx += 1

    cap.release()

    logger.info("Writing %d annotations to %s", len(annotations), output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(annotations, f, indent=None, separators=(",", ":"))

    logger.info(
        "Done. Profile built: %s, reference embeddings: %d",
        player_profile.is_built(),
        len(player_profile.reference_embeddings),
    )


# ── Test frame mode ────────────────────────────────────────────────────────────


def run_test_frame(mode: str, yolo_onnx: str, osnet_onnx: str) -> None:
    """Process a synthetic test frame without crashing (resilience check)."""
    if mode == "black":
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        logger.info("Test frame: black (no persons expected)")
    elif mode == "blur":
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        frame = cv2.GaussianBlur(frame, (51, 51), 0)
        logger.info("Test frame: blur (unreadable jersey expected)")
    else:
        raise ValueError(f"Unknown test frame mode: {mode}")

    yolo_sess = build_yolo_session(yolo_onnx)
    osnet_sess = build_osnet_session(osnet_onnx)
    ocr_reader = build_ocr_reader()

    orig_h, orig_w = frame.shape[:2]
    detections = run_yolo(yolo_sess, frame, orig_h, orig_w)
    logger.info("Detections on %s frame: %d", mode, len(detections))

    crops = []
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        crop = frame[y1:y2, x1:x2]
        crops.append(preprocess_crop_for_osnet(crop))

    embeddings = run_osnet_batch(osnet_sess, crops)
    for i, det in enumerate(detections):
        torso = extract_torso_crop(frame, tuple(det["bbox"]))
        jersey = ocr_jersey_number(ocr_reader, torso)
        logger.info("Det %d: bbox=%s jersey=%s emb_norm=%s", i, det["bbox"], jersey,
                    f"{np.linalg.norm(embeddings[i]):.3f}" if embeddings[i] is not None else "None")

    logger.info("Test frame %s completed without exception.", mode)


# ── CLI ────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Player continuity tracker")
    parser.add_argument("--video", default=os.path.expanduser(
        "~/veo-g15a-match-7mar2026/standard-1920x1080-followcam.mp4"
    ))
    parser.add_argument("--player-jersey", default=None,
                        help="Target player jersey number (e.g. '4')")
    parser.add_argument("--output", default=os.path.expanduser(
        "~/veo-clips/player-continuity-tracking/player_ids.json"
    ))
    parser.add_argument("--end-time", type=float, default=None,
                        help="Stop after this many seconds of video")
    parser.add_argument("--sample-rate", type=int, default=SAMPLE_EVERY,
                        help="Process every Nth frame")
    parser.add_argument("--yolo-onnx", default=os.path.expanduser("~/yolov8n.onnx"))
    parser.add_argument("--osnet-onnx", default=os.path.expanduser("~/osnet_ain_x1_0.onnx"))
    parser.add_argument("--test-frame", choices=["black", "blur"], default=None,
                        help="Run synthetic test frame (resilience check)")
    args = parser.parse_args()

    if args.test_frame:
        run_test_frame(args.test_frame, args.yolo_onnx, args.osnet_onnx)
        return

    run_tracker(
        video_path=args.video,
        player_jersey=args.player_jersey,
        output_path=args.output,
        yolo_onnx=args.yolo_onnx,
        osnet_onnx=args.osnet_onnx,
        end_time=args.end_time,
        sample_rate=args.sample_rate,
    )


if __name__ == "__main__":
    main()
