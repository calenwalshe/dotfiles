"""Webcam feed health monitor with automatic fallback/swap logic."""
from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class FeedStatus:
    feed_id: str
    url: str
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_check: float = 0.0

    @property
    def needs_replacement(self) -> bool:
        return not self.is_healthy and self.consecutive_failures >= 3


class FeedHealthMonitor:
    def __init__(self, failure_threshold: int = 3, poll_interval: int = 60):
        self.failure_threshold = failure_threshold
        self.poll_interval = poll_interval
        self.feeds: dict[str, FeedStatus] = {}
        self._on_swap: Optional[Callable[[str, str], None]] = None
        self._backup_feeds: list[str] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_feed(self, feed_id: str, url: str):
        self.feeds[feed_id] = FeedStatus(feed_id=feed_id, url=url)

    def set_backup_feeds(self, urls: list[str]):
        self._backup_feeds = list(urls)

    def on_swap(self, callback: Callable[[str, str], None]):
        """Register callback for when a feed is swapped. Args: (feed_id, new_url)."""
        self._on_swap = callback

    def record_failure(self, feed_id: str):
        if feed_id not in self.feeds:
            return
        status = self.feeds[feed_id]
        status.consecutive_failures += 1
        if status.consecutive_failures >= self.failure_threshold:
            status.is_healthy = False
            logger.warning(f"Feed {feed_id} marked unhealthy after {status.consecutive_failures} failures")

    def record_success(self, feed_id: str):
        if feed_id not in self.feeds:
            return
        status = self.feeds[feed_id]
        status.consecutive_failures = 0
        status.is_healthy = True

    def get_unhealthy_feeds(self) -> list[FeedStatus]:
        return [s for s in self.feeds.values() if not s.is_healthy]

    def check_feed(self, feed_id: str) -> bool:
        """Probe a feed URL to check if it's responsive."""
        status = self.feeds.get(feed_id)
        if not status:
            return False

        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-i", status.url, "-show_entries", "format=duration", "-of", "csv=p=0"],
                timeout=10,
                capture_output=True,
            )
            alive = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            alive = False

        if alive:
            self.record_success(feed_id)
        else:
            self.record_failure(feed_id)

        status.last_check = time.time()
        return alive

    def _try_swap(self, feed_id: str):
        """Attempt to swap a dead feed for a backup."""
        if not self._backup_feeds:
            logger.error(f"No backup feeds available to replace {feed_id}")
            return

        new_url = self._backup_feeds.pop(0)
        old_url = self.feeds[feed_id].url
        self.feeds[feed_id].url = new_url
        self.feeds[feed_id].consecutive_failures = 0
        self.feeds[feed_id].is_healthy = True
        logger.info(f"Swapped feed {feed_id}: {old_url} -> {new_url}")

        if self._on_swap:
            self._on_swap(feed_id, new_url)

    def start(self):
        """Start the health monitoring loop in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Health monitor started (interval={self.poll_interval}s, threshold={self.failure_threshold})")

    def _monitor_loop(self):
        while self._running:
            for feed_id in list(self.feeds.keys()):
                self.check_feed(feed_id)
                status = self.feeds[feed_id]
                if status.needs_replacement:
                    self._try_swap(feed_id)
            time.sleep(self.poll_interval)

    def stop(self):
        self._running = False
        logger.info("Health monitor stopped")
