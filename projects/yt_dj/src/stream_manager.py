"""Stream manager — orchestrates the FFmpeg compositing pipeline and handles YouTube stream lifecycle."""
from __future__ import annotations

import json
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from src.compositor import FFmpegCompositor, GridLayout
from src.webcam_client import WindyWebcamClient, WebcamFeed

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_config() -> dict:
    stream_cfg = json.loads((CONFIG_DIR / "stream.json").read_text())
    webcam_cfg = json.loads((CONFIG_DIR / "webcams.json").read_text())
    return {"stream": stream_cfg, "webcams": webcam_cfg}


class StreamManager:
    """Manages the FFmpeg streaming pipeline lifecycle."""

    def __init__(self, config: dict):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self._running = False

        video_cfg = config["stream"]["video"]
        self.compositor = FFmpegCompositor(
            width=video_cfg["width"],
            height=video_cfg["height"],
        )

    def get_rtmp_url(self) -> str:
        yt = self.config["stream"]["youtube"]
        if not yt["stream_key"]:
            raise ValueError("YouTube stream key not configured in config/stream.json")
        return f"{yt['rtmp_url']}/{yt['stream_key']}"

    def resolve_layout(self, layout_name: str = "2x2") -> GridLayout:
        scenes = self.config["webcams"]["scenes"]
        if layout_name not in scenes:
            raise ValueError(f"Unknown layout: {layout_name}. Available: {list(scenes.keys())}")
        scene = scenes[layout_name]
        video_cfg = self.config["stream"]["video"]
        return GridLayout(
            rows=scene["rows"],
            cols=scene["cols"],
            width=video_cfg["width"],
            height=video_cfg["height"],
        )

    def fetch_webcam_feeds(self, count: int, theme: str = "world") -> list[str]:
        """Fetch webcam stream URLs from Windy API."""
        api_key = self.config["webcams"].get("windy_api_key", "")
        if not api_key:
            logger.warning("No Windy API key — using test color sources")
            return self._test_sources(count)

        themes = self.config["webcams"].get("themes", {})
        theme_cfg = themes.get(theme, themes.get("world", {}))
        countries = theme_cfg.get("countries", ["US", "GB", "JP"])

        client = WindyWebcamClient(api_key=api_key)
        feeds: list[WebcamFeed] = []
        for country in countries:
            if len(feeds) >= count:
                break
            results = client.search(country=country, limit=count - len(feeds), active_only=True)
            feeds.extend(results)
        client.close()

        urls = [f.stream_url for f in feeds if f.stream_url]
        if len(urls) < count:
            logger.warning(f"Only found {len(urls)} feeds, padding with test sources")
            urls.extend(self._test_sources(count - len(urls)))
        return urls[:count]

    def _test_sources(self, count: int) -> list[str]:
        """Generate FFmpeg test pattern sources for development."""
        colors = ["red", "blue", "green", "yellow", "purple", "orange", "cyan", "white", "gray"]
        sources = []
        for i in range(count):
            color = colors[i % len(colors)]
            sources.append(
                f"testsrc=size=960x540:rate=30:duration=86400,drawtext="
                f"text='CAM {i+1}':fontsize=48:fontcolor=white:x=(w-tw)/2:y=(h-th)/2"
            )
        return sources

    def start(self, layout_name: str = "2x2", theme: str = "world", audio_source: Optional[str] = None):
        """Start the streaming pipeline."""
        layout = self.resolve_layout(layout_name)
        rtmp_url = self.get_rtmp_url()

        sources = self.fetch_webcam_feeds(layout.total_cells, theme)
        is_test = sources[0].startswith("testsrc=")

        if is_test:
            cmd = self._build_test_stream_command(sources, layout, rtmp_url)
        else:
            cmd = self.compositor.build_command(
                sources=sources,
                layout=layout,
                rtmp_url=rtmp_url,
                audio_source=audio_source,
            )

        logger.info(f"Starting stream: {layout_name} grid, theme={theme}")
        logger.debug(f"Command: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._running = True
        logger.info(f"Stream started (PID {self.process.pid})")

    def _build_test_stream_command(self, sources: list[str], layout: GridLayout, rtmp_url: str) -> list[str]:
        """Build FFmpeg command using test pattern sources (lavfi inputs)."""
        cmd = ["ffmpeg"]

        for src in sources[:layout.total_cells]:
            cmd.extend(["-f", "lavfi", "-i", src])

        # Generate silent audio
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

        filters = []
        for i in range(layout.total_cells):
            filters.append(f"[{i}:v]scale={layout.cell_width}:{layout.cell_height},setsar=1[v{i}]")

        inputs_str = "".join(f"[v{i}]" for i in range(layout.total_cells))
        xstack_layout = layout.xstack_layout()
        filters.append(f"{inputs_str}xstack=inputs={layout.total_cells}:layout={xstack_layout}[vout]")

        cmd.extend(["-filter_complex", ";".join(filters)])
        cmd.extend(["-map", "[vout]", "-map", f"{layout.total_cells}:a"])
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k",
            "-g", "60", "-keyint_min", "60",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-f", "flv", rtmp_url,
        ])
        return cmd

    def stop(self):
        """Stop the streaming pipeline."""
        if self.process and self.process.poll() is None:
            logger.info("Stopping stream...")
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info("Stream stopped")
        self._running = False

    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def restart(self, **kwargs):
        """Restart the stream (used for 12-hour rotation)."""
        logger.info("Restarting stream...")
        self.stop()
        time.sleep(2)
        self.start(**kwargs)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    config = load_config()
    manager = StreamManager(config)

    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    layout = sys.argv[1] if len(sys.argv) > 1 else "2x2"
    theme = sys.argv[2] if len(sys.argv) > 2 else "world"

    manager.start(layout_name=layout, theme=theme)

    # Keep alive and monitor
    while manager.is_running():
        time.sleep(5)

    logger.warning("Stream ended unexpectedly")
    sys.exit(1)


if __name__ == "__main__":
    main()
