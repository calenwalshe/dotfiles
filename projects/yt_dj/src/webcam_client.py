"""Windy Webcams API v3 client for discovering public webcam feeds."""
from __future__ import annotations

import logging
import os
import tempfile
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class WebcamFeed:
    id: str
    title: str
    stream_url: str
    preview_url: str
    city: str
    country: str
    latitude: float
    longitude: float
    is_active: bool

    @classmethod
    def from_api(cls, data: dict) -> WebcamFeed:
        location = data.get("location", {})
        # Player embed URL (timelapse player, not direct stream)
        player = data.get("player", {})
        embed_url = player.get("day", "") or player.get("lifetime", "")
        # Image URL — use full resolution by replacing /preview/ with /full/ in URL
        images = data.get("images", {})
        preview = images.get("current", {}).get("preview", "")
        # Upgrade to full resolution (1280x960 vs 400x224)
        if preview:
            preview = preview.replace("/preview/", "/full/")

        return cls(
            id=str(data.get("webcamId", data.get("id", ""))),
            title=data.get("title", ""),
            stream_url=embed_url,
            preview_url=preview,
            city=location.get("city", ""),
            country=location.get("country_code", location.get("country", "")),
            latitude=location.get("latitude", 0.0),
            longitude=location.get("longitude", 0.0),
            is_active=data.get("status") == "active",
        )


class WindyWebcamClient:
    BASE_URL = "https://api.windy.com/webcams/api/v3/webcams"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self._client = httpx.Client(
            headers={"x-windy-api-key": api_key},
            timeout=15.0,
        )

    def search(
        self,
        country: Optional[str] = None,
        limit: int = 10,
        active_only: bool = True,
    ) -> list[WebcamFeed]:
        params: dict = {
            "limit": limit,
            "include": "player,images,location",
        }
        if country:
            params["countries"] = country

        resp = self._client.get(self.BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        feeds = [WebcamFeed.from_api(w) for w in data.get("webcams", [])]
        if active_only:
            feeds = [f for f in feeds if f.is_active]
        return feeds

    def get_by_id(self, webcam_id: str) -> WebcamFeed:
        resp = self._client.get(
            f"{self.BASE_URL}/{webcam_id}",
            params={"include": "player,images,location"},
        )
        resp.raise_for_status()
        data = resp.json()
        webcams = data.get("webcams", [])
        if not webcams:
            raise ValueError(f"Webcam {webcam_id} not found")
        return WebcamFeed.from_api(webcams[0])

    def download_preview(self, feed: WebcamFeed, output_dir: str) -> str:
        """Download a webcam preview image to a local file. Returns the file path."""
        if not feed.preview_url:
            raise ValueError(f"No preview URL for feed {feed.id}")
        resp = self._client.get(feed.preview_url)
        resp.raise_for_status()
        path = os.path.join(output_dir, f"cam_{feed.id}.jpg")
        with open(path, "wb") as f:
            f.write(resp.content)
        return path

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ImageRefresher:
    """Periodically downloads webcam snapshots to local files for FFmpeg to consume."""

    def __init__(self, client: WindyWebcamClient, feeds: list[WebcamFeed], output_dir: str, interval: int = 10):
        self.client = client
        self.feeds = feeds
        self.output_dir = output_dir
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        os.makedirs(output_dir, exist_ok=True)

    def refresh_once(self) -> list[str]:
        """Download all feed images once. Returns list of local file paths."""
        paths = []
        for feed in self.feeds:
            try:
                path = self.client.download_preview(feed, self.output_dir)
                paths.append(path)
                logger.debug(f"Refreshed {feed.id}: {feed.city}")
            except Exception:
                logger.warning(f"Failed to refresh {feed.id}: {feed.city}")
                # Keep existing file if refresh fails
                existing = os.path.join(self.output_dir, f"cam_{feed.id}.jpg")
                if os.path.exists(existing):
                    paths.append(existing)
        return paths

    def start(self):
        """Start refreshing images in a background thread."""
        self._running = True
        # Initial fetch
        self.refresh_once()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"Image refresher started ({len(self.feeds)} feeds, {self.interval}s interval)")

    def _loop(self):
        while self._running:
            time.sleep(self.interval)
            self.refresh_once()

    def stop(self):
        self._running = False

    def get_image_paths(self) -> list[str]:
        """Return current local image file paths for all feeds."""
        return [
            os.path.join(self.output_dir, f"cam_{feed.id}.jpg")
            for feed in self.feeds
            if os.path.exists(os.path.join(self.output_dir, f"cam_{feed.id}.jpg"))
        ]
