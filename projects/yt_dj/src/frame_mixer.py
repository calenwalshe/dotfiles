"""Frame mixer — fetches cam images, generates dissolve transitions, writes to FIFO for FFmpeg."""
from __future__ import annotations

import io
import logging
import os
import struct
import time
from pathlib import Path

import httpx
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
FRAME_BYTES = WIDTH * HEIGHT * 3  # RGB24


def fetch_image(url: str, timeout: float = 10.0) -> np.ndarray | None:
    """Fetch a JPEG image and return as a 1920x1080 RGB numpy array."""
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
        return np.array(img, dtype=np.uint8)
    except Exception as e:
        log.warning(f"Failed to fetch image: {e}")
        return None


def fetch_windy_image(windy_client, country: str) -> np.ndarray | None:
    """Fetch a webcam image from Windy API for a given country."""
    try:
        feeds = windy_client.search(country=country, limit=3, active_only=True)
        if not feeds:
            return None
        import random
        feed = random.choice(feeds)
        if not feed.preview_url:
            return None
        return fetch_image(feed.preview_url)
    except Exception as e:
        log.warning(f"Windy fetch failed for {country}: {e}")
        return None


def dissolve(fd: int, old_frame: np.ndarray, new_frame: np.ndarray,
             duration: float = 3.0, fps: int = FPS):
    """Write dissolve transition frames to file descriptor."""
    steps = int(duration * fps)
    old_f = old_frame.astype(np.float32)
    new_f = new_frame.astype(np.float32)

    for i in range(steps):
        alpha = i / (steps - 1) if steps > 1 else 1.0
        blended = ((1.0 - alpha) * old_f + alpha * new_f).astype(np.uint8)
        os.write(fd, blended.tobytes())


def hold_frame(fd: int, frame: np.ndarray, duration: float = 45.0, fps: int = FPS):
    """Write the same frame repeatedly for a hold period."""
    frame_bytes = frame.tobytes()
    total_frames = int(duration * fps)
    for _ in range(total_frames):
        os.write(fd, frame_bytes)


def black_frame() -> np.ndarray:
    """Return a black frame."""
    return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
