"""
Benchmark tracker stack on first N minutes of Veo footage.

Uses ONNX Runtime for both YOLOv8n and OSNet (CPU-optimized path).
Measures: FPS, peak RAM, OSNet cosine similarity distribution.
Outputs: veo-clips/player-continuity-tracking/benchmark_results.json
"""
import argparse
import json
import os
import time
import tracemalloc
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from tqdm import tqdm


SAMPLE_EVERY = 3       # Process every Nth frame
YOLO_IMGSZ = 640       # YOLOv8 input size (square)
CONF_THRESHOLD = 0.3   # Minimum detection confidence
NMS_THRESHOLD = 0.45   # NMS IoU threshold


def build_yolo_session(model_path: str) -> ort.InferenceSession:
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(model_path, sess_options=opts, providers=["CPUExecutionProvider"])


def build_osnet_session(model_path: str) -> ort.InferenceSession:
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(model_path, sess_options=opts, providers=["CPUExecutionProvider"])


def letterbox(img: np.ndarray, target_size: int = 640):
    """Resize with letterbox padding to square."""
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h))
    pad_top = (target_size - new_h) // 2
    pad_left = (target_size - new_w) // 2
    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    canvas[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized
    return canvas, scale, pad_top, pad_left


def run_yolo(session: ort.InferenceSession, frame: np.ndarray, orig_h: int, orig_w: int):
    """Run YOLOv8n ONNX and return person bounding boxes in original frame coords."""
    lb, scale, pad_top, pad_left = letterbox(frame, YOLO_IMGSZ)
    inp = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    inp = inp.transpose(2, 0, 1)[np.newaxis, :]

    raw = session.run(None, {"images": inp})[0]  # shape: (1, 84, 8400)
    preds = raw[0].T  # (8400, 84)

    # Columns: cx, cy, w, h, cls0..cls79
    boxes_xywh = preds[:, :4]
    scores_all = preds[:, 4:]
    # Person class is index 0
    person_scores = scores_all[:, 0]
    mask = person_scores > CONF_THRESHOLD
    if not mask.any():
        return []

    bxywh = boxes_xywh[mask]
    bscores = person_scores[mask]

    # Convert cx,cy,w,h -> x1,y1,x2,y2 (in letterboxed coords)
    x1 = bxywh[:, 0] - bxywh[:, 2] / 2
    y1 = bxywh[:, 1] - bxywh[:, 3] / 2
    x2 = bxywh[:, 0] + bxywh[:, 2] / 2
    y2 = bxywh[:, 1] + bxywh[:, 3] / 2

    # Unletterbox: remove padding, undo scale
    x1 = (x1 - pad_left) / scale
    y1 = (y1 - pad_top) / scale
    x2 = (x2 - pad_left) / scale
    y2 = (y2 - pad_top) / scale

    # Clip to original frame
    x1 = np.clip(x1, 0, orig_w)
    y1 = np.clip(y1, 0, orig_h)
    x2 = np.clip(x2, 0, orig_w)
    y2 = np.clip(y2, 0, orig_h)

    # NMS
    bboxes_for_nms = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).tolist()
    scores_list = bscores.tolist()
    indices = cv2.dnn.NMSBoxes(bboxes_for_nms, scores_list, CONF_THRESHOLD, NMS_THRESHOLD)
    if len(indices) == 0:
        return []

    result = []
    for i in indices.flatten():
        result.append({
            "bbox": [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])],
            "conf": float(bscores[i]),
        })
    return result


def preprocess_crop_for_osnet(crop_bgr: np.ndarray) -> np.ndarray | None:
    """Resize and normalize an image crop for OSNet input."""
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


def run_osnet_batch(session: ort.InferenceSession, crops: list[np.ndarray]) -> list[np.ndarray]:
    """Run OSNet on a batch of preprocessed crop tensors. Returns normalized embeddings."""
    if not crops:
        return []
    batch = np.stack(crops, axis=0)  # (N, 3, 256, 128)
    raw = session.run(None, {"input": batch})[0]  # (N, 512)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1.0, norms)
    return list(raw / norms)


def run_benchmark(video_path: str, end_time: float, output_path: str,
                  yolo_onnx: str, osnet_onnx: str):
    cap = cv2.VideoCapture(video_path)
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end_frame = int(end_time * fps_video)
    end_frame = min(end_frame, total_video_frames)
    frames_to_process = len(range(0, end_frame, SAMPLE_EVERY))

    yolo_sess = build_yolo_session(yolo_onnx)
    osnet_sess = build_osnet_session(osnet_onnx)

    embeddings = []
    frames_processed = 0
    frames_read = 0
    detections_total = 0
    wall_start = time.time()
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    tracemalloc.start()

    with tqdm(total=frames_to_process, desc="Benchmark") as pbar:
        while frames_read < end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            if frames_read % SAMPLE_EVERY == 0:
                detections = run_yolo(yolo_sess, frame, orig_h, orig_w)

                crops_ready = []
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    crop = frame[y1:y2, x1:x2]
                    tensor = preprocess_crop_for_osnet(crop)
                    if tensor is not None:
                        crops_ready.append(tensor)

                batch_embs = run_osnet_batch(osnet_sess, crops_ready)
                embeddings.extend(batch_embs)
                detections_total += len(detections)
                frames_processed += 1
                pbar.update(1)

            frames_read += 1

    cap.release()

    wall_elapsed = time.time() - wall_start
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    measured_fps = frames_processed / wall_elapsed if wall_elapsed > 0 else 0.0
    video_duration_s = total_video_frames / fps_video
    projected_full_s = (wall_elapsed / end_time) * video_duration_s if end_time > 0 else None

    cosine_sims = []
    if len(embeddings) >= 2:
        sample = embeddings[:min(500, len(embeddings))]
        for i in range(0, len(sample) - 1, 2):
            cosine_sims.append(float(np.dot(sample[i], sample[i + 1])))

    results_data = {
        "video": video_path,
        "benchmark_end_time_s": end_time,
        "sample_every_n_frames": SAMPLE_EVERY,
        "frames_read": frames_read,
        "frames_processed": frames_processed,
        "total_detections": detections_total,
        "wall_time_s": round(wall_elapsed, 2),
        "processing_fps": round(measured_fps, 3),
        "peak_ram_mb": round(peak_mem / 1024 / 1024, 1),
        "embeddings_extracted": len(embeddings),
        "projected_full_video_h": round(projected_full_s / 3600, 2) if projected_full_s else None,
        "cosine_sim_stats": {
            "count": len(cosine_sims),
            "mean": round(float(np.mean(cosine_sims)), 4) if cosine_sims else None,
            "std": round(float(np.std(cosine_sims)), 4) if cosine_sims else None,
            "min": round(float(np.min(cosine_sims)), 4) if cosine_sims else None,
            "max": round(float(np.max(cosine_sims)), 4) if cosine_sims else None,
            "p25": round(float(np.percentile(cosine_sims, 25)), 4) if cosine_sims else None,
            "p75": round(float(np.percentile(cosine_sims, 75)), 4) if cosine_sims else None,
        },
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results_data, f, indent=2)

    print(f"\n=== Benchmark Results ===")
    print(f"Frames read: {frames_read} | Processed (every {SAMPLE_EVERY}): {frames_processed}")
    print(f"Wall time: {wall_elapsed:.1f}s ({wall_elapsed/60:.1f} min)")
    print(f"Processing FPS: {measured_fps:.3f} frames/s")
    print(f"Peak RAM: {peak_mem / 1024 / 1024:.1f} MB")
    print(f"Total detections: {detections_total}")
    print(f"Embeddings extracted: {len(embeddings)}")
    if projected_full_s:
        print(f"Projected full video time: {projected_full_s/3600:.2f}h")
    if cosine_sims:
        print(f"Cosine sim (mean ± std): {np.mean(cosine_sims):.4f} ± {np.std(cosine_sims):.4f}")
        print(f"Cosine sim range: [{np.min(cosine_sims):.4f}, {np.max(cosine_sims):.4f}]")
    print(f"\nResults saved to: {output_path}")
    return results_data


def main():
    parser = argparse.ArgumentParser(description="Benchmark tracker stack on Veo footage")
    parser.add_argument("--video", default=os.path.expanduser(
        "~/veo-g15a-match-7mar2026/standard-1920x1080-followcam.mp4"
    ))
    parser.add_argument("--end-time", type=float, default=300.0,
                        help="Benchmark end time in seconds (default: 300 = 5 minutes)")
    parser.add_argument("--output", default=os.path.expanduser(
        "~/veo-clips/player-continuity-tracking/benchmark_results.json"
    ))
    parser.add_argument("--yolo-onnx", default=os.path.expanduser("~/yolov8n.onnx"))
    parser.add_argument("--osnet-onnx", default=os.path.expanduser("~/osnet_ain_x1_0.onnx"))
    args = parser.parse_args()
    run_benchmark(args.video, args.end_time, args.output, args.yolo_onnx, args.osnet_onnx)


if __name__ == "__main__":
    main()
