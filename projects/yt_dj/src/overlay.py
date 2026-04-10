"""Dynamic overlay text writer for FFmpeg drawtext reload."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pytz

log = logging.getLogger(__name__)

OVERLAY_PATH = "/tmp/yt_dj_overlay.txt"


def update_overlay(cam: dict):
    """Write location + local time to overlay text file."""
    try:
        tz = pytz.timezone(cam.get("tz", "UTC"))
        local_time = datetime.now(tz).strftime("%H\\:%M")
        name = cam.get("name", "Unknown")
        country = cam.get("country", "")

        text = f"{name}   {local_time}"
        if country and country != "SPACE":
            text = f"{name}, {country}   {local_time}"

        with open(OVERLAY_PATH, "w") as f:
            f.write(text)

        log.debug(f"Overlay: {text}")
    except Exception as e:
        log.warning(f"Overlay update failed: {e}")


def clear_overlay():
    with open(OVERLAY_PATH, "w") as f:
        f.write(" ")
