"""Go live — sun-chasing single-cam stream with dissolve transitions + DJ mix audio."""
from __future__ import annotations

import json
import logging
import os
import random
import signal
import subprocess
import sys
import time
import threading
from pathlib import Path

from src.solar_scorer import rank_cameras, load_cameras
from src.frame_mixer import fetch_windy_image, fetch_image, dissolve, hold_frame, black_frame, WIDTH, HEIGHT, FPS
from src.overlay import update_overlay, clear_overlay, OVERLAY_PATH
from src.webcam_client import WindyWebcamClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

PROJECT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT / "config"

stream_cfg = json.loads((CONFIG_DIR / "stream.json").read_text())
webcam_cfg = json.loads((CONFIG_DIR / "webcams.json").read_text())

STREAM_KEY = stream_cfg["youtube"]["stream_key"]
RTMP_URL = f"{stream_cfg['youtube']['rtmp_url']}/{STREAM_KEY}"
WINDY_KEY = webcam_cfg["windy_api_key"]
MERGED_AUDIO = Path("/tmp/yt_dj_merged.mp3")
FIFO_PATH = "/tmp/yt_dj_video_feed"

DWELL_SECONDS = 120       # how long to hold each cam
DISSOLVE_SECONDS = 4.0    # transition duration


def ensure_fifo():
    """Create named pipe if it doesn't exist."""
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)
    os.mkfifo(FIFO_PATH)
    log.info(f"FIFO created: {FIFO_PATH}")


def start_ffmpeg() -> subprocess.Popen:
    """Start FFmpeg reading from FIFO + audio, streaming to YouTube."""
    # Ensure overlay file exists
    with open(OVERLAY_PATH, "w") as f:
        f.write(" ")

    cmd = [
        "ffmpeg", "-y",
        # Video from FIFO
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS),
        "-i", FIFO_PATH,
        # Audio (DJ mix, infinite loop)
        "-stream_loop", "-1", "-i", str(MERGED_AUDIO),
        # Overlay: location + time (lower left) + LIVE dot (upper right)
        "-vf",
        f"drawtext=textfile={OVERLAY_PATH}:reload=1"
        f":fontsize=28:fontcolor=white@0.6:borderw=1:bordercolor=black@0.3"
        f":x=40:y=H-50:font=monospace,"
        f"drawtext=text='LIVE':fontsize=18:fontcolor=red@0.8"
        f":x=W-90:y=25:font=monospace",
        # Encoding
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k",
        "-pix_fmt", "yuv420p",
        "-g", "60", "-keyint_min", "60",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-f", "flv", RTMP_URL,
    ]

    log.info("Starting FFmpeg...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    log.info(f"FFmpeg started (PID {proc.pid})")
    return proc


def fetch_cam_frame(cam: dict, windy_client: WindyWebcamClient) -> tuple:
    """Fetch a frame for a camera. Returns (frame, cam) or (None, cam) on failure."""
    if cam.get("source") == "iss":
        # Try to get ISS feed frame
        try:
            r = subprocess.run(
                ["yt-dlp", "--cookies-from-browser", "chrome", "--remote-components", "ejs:github",
                 "-g", "-f", "best", "https://www.youtube.com/watch?v=vytmBNhc9ig"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0 and r.stdout.strip():
                # Grab one frame from HLS
                hls_url = r.stdout.strip()
                grab = subprocess.run(
                    ["ffmpeg", "-y", "-i", hls_url, "-frames:v", "1",
                     "-f", "image2", "/tmp/iss_frame.jpg"],
                    capture_output=True, timeout=15
                )
                if grab.returncode == 0:
                    return fetch_image("/tmp/iss_frame.jpg"), cam
        except Exception as e:
            log.warning(f"ISS fetch failed: {e}")
        return None, cam

    # Windy-sourced camera
    country = cam.get("windy_country", cam.get("country", "US"))
    frame = fetch_windy_image(windy_client, country)
    return frame, cam


def main_loop(fd: int, windy_client: WindyWebcamClient):
    """Main visual loop — pick cam, dissolve, hold, repeat."""
    cameras = load_cameras()
    current_frame = black_frame()
    current_name = None

    while True:
        # Rank by solar position
        ranked = rank_cameras(cameras)

        # Pick next (avoid repeating)
        chosen = None
        for cam in ranked:
            if cam["name"] == current_name:
                continue
            frame, cam = fetch_cam_frame(cam, windy_client)
            if frame is not None:
                chosen = cam
                new_frame = frame
                break

        if chosen is None:
            log.warning("No cam available, holding current frame")
            hold_frame(fd, current_frame, duration=30)
            continue

        # Update overlay
        update_overlay(chosen)
        log.info(f"Switching to: {chosen['name']} (score={chosen.get('solar_score', 0):.2f})")

        # Dissolve transition
        dissolve(fd, current_frame, new_frame, duration=DISSOLVE_SECONDS)

        # Hold
        hold_frame(fd, new_frame, duration=DWELL_SECONDS)

        current_frame = new_frame
        current_name = chosen["name"]


def main():
    log.info("=== yt_dj GO LIVE — Sun Chaser ===")

    if not MERGED_AUDIO.exists():
        log.error(f"No merged audio at {MERGED_AUDIO}. Run dj_mixer.py first.")
        sys.exit(1)

    windy_client = WindyWebcamClient(api_key=WINDY_KEY)

    ensure_fifo()

    # Start FFmpeg in background thread (it blocks on FIFO read until we write)
    ffmpeg_proc = None
    def run_ffmpeg():
        nonlocal ffmpeg_proc
        ffmpeg_proc = start_ffmpeg()

    ffmpeg_thread = threading.Thread(target=run_ffmpeg, daemon=True)
    ffmpeg_thread.start()
    time.sleep(1)  # Let FFmpeg open the FIFO for reading

    # Open FIFO for writing
    fd = os.open(FIFO_PATH, os.O_WRONLY)
    log.info("FIFO opened for writing")

    def shutdown(sig, frame):
        log.info("Shutting down...")
        os.close(fd)
        if ffmpeg_proc:
            ffmpeg_proc.send_signal(signal.SIGINT)
            try:
                ffmpeg_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                ffmpeg_proc.kill()
        windy_client.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log.info("LIVE! Sun-chasing stream active.")

    try:
        main_loop(fd, windy_client)
    except BrokenPipeError:
        log.error("FFmpeg pipe broken — stream ended")
        if ffmpeg_proc:
            stderr = ffmpeg_proc.stderr.read().decode()[-500:] if ffmpeg_proc.stderr else ""
            log.error(f"FFmpeg stderr: {stderr}")
    except Exception:
        log.exception("Main loop error")
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


if __name__ == "__main__":
    main()
