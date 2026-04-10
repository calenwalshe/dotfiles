"""Score camera feeds by solar position — prefer golden hour."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pvlib

log = logging.getLogger(__name__)

PROJECT = Path(__file__).parent.parent
CAMERAS_PATH = PROJECT / "config" / "cameras.json"


def load_cameras() -> list[dict]:
    with open(CAMERAS_PATH) as f:
        return json.load(f)


def solar_score(lat: float, lon: float, now: datetime = None) -> float:
    """Score 0.0-1.0 based on solar elevation. Golden hour = 1.0."""
    now = now or datetime.now(timezone.utc)
    solpos = pvlib.solarposition.get_solarposition(
        pd.DatetimeIndex([now]), lat, lon
    )
    elev = float(solpos["apparent_elevation"].iloc[0])

    if elev < -12:
        return 0.05   # deep night — city lights possible
    if elev < -6:
        return 0.15   # astronomical twilight
    if elev < 0:
        return 0.5    # civil twilight — nice colors
    if elev <= 6:
        return 1.0    # golden hour — peak
    if elev <= 10:
        return 0.85   # near golden
    if elev <= 30:
        return 0.4    # nice daylight
    return 0.25        # harsh midday


def rank_cameras(cameras: list[dict] = None, now: datetime = None) -> list[dict]:
    """Rank cameras by solar score, highest first."""
    cameras = cameras or load_cameras()
    now = now or datetime.now(timezone.utc)

    scored = []
    for cam in cameras:
        if cam.get("source") == "iss":
            # ISS is always interesting — give it a moderate fixed score
            cam["solar_score"] = 0.6
        else:
            cam["solar_score"] = solar_score(cam["lat"], cam["lon"], now)
        scored.append(cam)

    scored.sort(key=lambda c: c["solar_score"], reverse=True)
    return scored


def pick_next(cameras: list[dict] = None, exclude: str = None) -> dict:
    """Pick the best camera, optionally excluding the current one."""
    ranked = rank_cameras(cameras)
    for cam in ranked:
        if exclude and cam["name"] == exclude:
            continue
        return cam
    return ranked[0]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cameras = load_cameras()
    ranked = rank_cameras(cameras)
    print(f"{'Name':20s} {'Score':>6s} {'Category':10s}")
    print("-" * 40)
    for cam in ranked[:15]:
        print(f"{cam['name']:20s} {cam['solar_score']:6.2f} {cam['category']:10s}")
