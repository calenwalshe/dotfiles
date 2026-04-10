"""yt_dj main orchestrator — wires up all components and runs the stream."""
from __future__ import annotations

import json
import logging
import signal
import sys
import time
from pathlib import Path

from src.command_bus import CommandBus
from src.obs_controller import OBSController
from src.liquidsoap_controller import LiquidsoapController
from src.health_monitor import FeedHealthMonitor
from src.chatbot import ChatCommandHandler
from src.command_bus import Command

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_config() -> dict:
    stream_cfg = json.loads((CONFIG_DIR / "stream.json").read_text())
    webcam_cfg = json.loads((CONFIG_DIR / "webcams.json").read_text())
    return {"stream": stream_cfg, "webcams": webcam_cfg}


class Orchestrator:
    """Main orchestrator — connects all components via the Redis command bus."""

    def __init__(self, config: dict):
        self.config = config
        self._running = False

        # Command bus
        redis_cfg = config["stream"]["redis"]
        self.bus = CommandBus(host=redis_cfg["host"], port=redis_cfg["port"])

        # Controllers
        obs_cfg = config["stream"]["obs"]
        self.obs = OBSController(
            host=obs_cfg["host"],
            port=obs_cfg["port"],
            password=obs_cfg.get("password", ""),
        )

        ls_cfg = config["stream"]["audio"]
        self.liquidsoap = LiquidsoapController(
            host=ls_cfg.get("liquidsoap_host", "127.0.0.1"),
            port=ls_cfg.get("liquidsoap_port", 3333),
        )

        # Health monitor
        self.health_monitor = FeedHealthMonitor(failure_threshold=3, poll_interval=60)

        # Chatbot handler
        self.chat_handler = ChatCommandHandler(bus=self.bus)

    def start(self):
        """Start all components."""
        logger.info("Starting yt_dj orchestrator...")

        # Connect command bus
        self.bus.connect()

        # Register controllers on bus
        self.obs.register_on_bus(self.bus)
        self.liquidsoap.register_on_bus(self.bus)

        # Try connecting to OBS (may not be running yet)
        try:
            self.obs.connect()
            logger.info("OBS connected")
        except Exception:
            logger.warning("OBS not available — video commands will fail until OBS starts")

        # Start command bus listener
        self.bus.listen()

        # Start health monitor
        self.health_monitor.on_swap(self._on_feed_swap)
        self.health_monitor.start()

        self._running = True
        logger.info("yt_dj orchestrator running")

    def _on_feed_swap(self, feed_id: str, new_url: str):
        """Handle webcam feed swap — publish command to update OBS source."""
        cmd = Command(
            channel="stream:video",
            action="swap_source",
            params={"feed_id": feed_id, "new_url": new_url},
            source="health_monitor",
        )
        self.bus.publish(cmd)
        logger.info(f"Published feed swap: {feed_id} -> {new_url}")

    def handle_chat_message(self, text: str, source: str = "chatbot") -> str | None:
        """Process an incoming chat message."""
        return self.chat_handler.handle_message(text, source=source)

    def stop(self):
        """Stop all components."""
        logger.info("Stopping yt_dj orchestrator...")
        self._running = False
        self.health_monitor.stop()
        self.bus.stop()
        self.obs.disconnect()
        logger.info("yt_dj orchestrator stopped")

    def run(self):
        """Run the orchestrator main loop."""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = load_config()
    orchestrator = Orchestrator(config)

    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}")
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    orchestrator.run()


if __name__ == "__main__":
    main()
