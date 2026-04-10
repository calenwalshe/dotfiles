"""OBS WebSocket controller — subscribes to Redis commands, manipulates OBS scenes/sources."""
from __future__ import annotations

import logging
from typing import Optional

from src.command_bus import Command, CommandBus

logger = logging.getLogger(__name__)

# Import obsws lazily to allow testing without OBS running
try:
    import obsws_python as obsws
except ImportError:
    obsws = None


class OBSController:
    """Bridges Redis commands to OBS WebSocket API calls."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4455, password: str = ""):
        self.host = host
        self.port = port
        self.password = password
        self._client = None
        self._connected = False

    def connect(self):
        if obsws is None:
            raise RuntimeError("obsws-python not installed")
        try:
            self._client = obsws.ReqClient(host=self.host, port=self.port, password=self.password)
            self._connected = True
            logger.info(f"Connected to OBS WebSocket at {self.host}:{self.port}")
        except Exception:
            logger.exception("Failed to connect to OBS WebSocket")
            self._connected = False
            raise

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    def switch_scene(self, scene_name: str):
        if not self.is_connected:
            raise RuntimeError("Not connected to OBS")
        self._client.set_current_program_scene(scene_name)
        logger.info(f"Switched to scene: {scene_name}")

    def set_source_visibility(self, scene_name: str, source_name: str, visible: bool):
        if not self.is_connected:
            raise RuntimeError("Not connected to OBS")
        item_id = self._client.get_scene_item_id(scene_name, source_name).scene_item_id
        self._client.set_scene_item_enabled(scene_name, item_id, visible)
        logger.info(f"Set {source_name} visibility to {visible} in {scene_name}")

    def get_scene_list(self) -> list[str]:
        if not self.is_connected:
            raise RuntimeError("Not connected to OBS")
        resp = self._client.get_scene_list()
        return [s["sceneName"] for s in resp.scenes]

    def start_stream(self):
        if not self.is_connected:
            raise RuntimeError("Not connected to OBS")
        self._client.start_stream()
        logger.info("OBS stream started")

    def stop_stream(self):
        if not self.is_connected:
            raise RuntimeError("Not connected to OBS")
        self._client.stop_stream()
        logger.info("OBS stream stopped")

    def handle_command(self, cmd: Command):
        """Handle a command from the Redis bus."""
        try:
            if cmd.action == "switch_scene":
                self.switch_scene(cmd.params["scene"])
            elif cmd.action == "set_layout":
                layout = cmd.params.get("layout", "2x2")
                self.switch_scene(f"grid_{layout}")
            elif cmd.action == "set_source_visible":
                self.set_source_visibility(
                    cmd.params["scene"],
                    cmd.params["source"],
                    cmd.params.get("visible", True),
                )
            elif cmd.action == "start_stream":
                self.start_stream()
            elif cmd.action == "stop_stream":
                self.stop_stream()
            else:
                logger.warning(f"Unknown OBS command: {cmd.action}")
        except Exception:
            logger.exception(f"Error handling OBS command: {cmd.action}")

    def register_on_bus(self, bus: CommandBus):
        """Subscribe to video and layout channels on the command bus."""
        bus.subscribe("stream:video", self.handle_command)
        bus.subscribe("stream:layout", self.handle_command)
        logger.info("OBS controller registered on command bus")

    def disconnect(self):
        self._client = None
        self._connected = False
