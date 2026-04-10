"""Mubert API client for AI-generated royalty-free music (autonomous mode)."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class MubertClient:
    """Client for Mubert API — generates royalty-free music by mood/genre."""

    BASE_URL = "https://api-b2b.mubert.com/v2"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Mubert API key is required")
        self.api_key = api_key
        self._client = httpx.Client(timeout=30.0)

    def generate_track(
        self,
        genre: str = "electronic",
        mood: str = "energetic",
        duration: int = 300,
        intensity: str = "medium",
    ) -> Optional[str]:
        """Generate a music track and return the stream URL.

        Args:
            genre: Music genre (electronic, ambient, house, etc.)
            mood: Mood descriptor (energetic, chill, dark, uplifting)
            duration: Track duration in seconds
            intensity: low, medium, high

        Returns:
            URL to the generated audio stream, or None on failure.
        """
        try:
            resp = self._client.post(
                f"{self.BASE_URL}/RecordTrackTTM",
                json={
                    "method": "RecordTrackTTM",
                    "params": {
                        "pat": self.api_key,
                        "duration": duration,
                        "tags": [genre, mood, intensity],
                        "mode": "track",
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == 1:
                tasks = data.get("data", {}).get("tasks", [])
                if tasks:
                    return tasks[0].get("download_link")

            logger.warning(f"Mubert generation failed: {data}")
            return None
        except Exception:
            logger.exception("Mubert API error")
            return None

    def get_genres(self) -> list[str]:
        """Get available genre tags."""
        try:
            resp = self._client.post(
                f"{self.BASE_URL}/GetServiceTags",
                json={
                    "method": "GetServiceTags",
                    "params": {"pat": self.api_key},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            tags = data.get("data", {}).get("tags", [])
            return [t.get("name", "") for t in tags]
        except Exception:
            logger.exception("Failed to get Mubert genres")
            return []

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
