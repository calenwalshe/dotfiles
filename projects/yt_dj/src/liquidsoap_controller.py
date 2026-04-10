"""Liquidsoap telnet controller — subscribes to Redis commands, controls audio playout."""
from __future__ import annotations

import logging
import socket
from typing import Optional

from src.command_bus import Command, CommandBus

logger = logging.getLogger(__name__)


class LiquidsoapController:
    """Bridges Redis commands to Liquidsoap telnet API."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3333, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send(self, command: str) -> str:
        """Send a command to Liquidsoap via telnet and return the response."""
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            sock.sendall((command + "\n").encode())
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"END" in chunk or b"\n" in chunk:
                    break
            sock.close()
            return response.decode().strip()
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            logger.error(f"Liquidsoap connection error: {e}")
            raise

    def skip_track(self) -> str:
        return self._send("source.skip")

    def get_metadata(self) -> str:
        return self._send("request.metadata")

    def set_volume(self, volume: float) -> str:
        """Set volume (0.0 to 1.0)."""
        return self._send(f"var.set volume = {volume}")

    def switch_playlist(self, playlist_name: str) -> str:
        """Switch to a named playlist/source."""
        return self._send(f"{playlist_name}.start")

    def get_remaining(self) -> str:
        return self._send("source.remaining")

    def handle_command(self, cmd: Command):
        """Handle a command from the Redis bus."""
        try:
            if cmd.action == "skip_track":
                self.skip_track()
                logger.info("Skipped track")
            elif cmd.action == "set_genre" or cmd.action == "switch_playlist":
                playlist = cmd.params.get("genre") or cmd.params.get("playlist", "default")
                self.switch_playlist(playlist)
                logger.info(f"Switched playlist to: {playlist}")
            elif cmd.action == "set_volume":
                volume = float(cmd.params.get("volume", 0.8))
                self.set_volume(volume)
                logger.info(f"Set volume to: {volume}")
            elif cmd.action == "get_now_playing":
                meta = self.get_metadata()
                logger.info(f"Now playing: {meta}")
            else:
                logger.warning(f"Unknown audio command: {cmd.action}")
        except Exception:
            logger.exception(f"Error handling Liquidsoap command: {cmd.action}")

    def register_on_bus(self, bus: CommandBus):
        """Subscribe to audio channel on the command bus."""
        bus.subscribe("stream:audio", self.handle_command)
        logger.info("Liquidsoap controller registered on command bus")
