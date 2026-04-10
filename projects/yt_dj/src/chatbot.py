"""Chatbot — parses user commands and publishes to Redis command bus."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from src.command_bus import Command, CommandBus

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    channel: str
    action: str
    params: dict

    def to_command(self, source: str = "chatbot") -> Command:
        return Command(channel=self.channel, action=self.action, params=self.params, source=source)


# Genre aliases for flexible input
GENRE_ALIASES = {
    "house": "house", "deep house": "house", "tech house": "house",
    "techno": "techno", "minimal": "techno",
    "dnb": "drum_and_bass", "drum and bass": "drum_and_bass", "jungle": "drum_and_bass",
    "ambient": "ambient", "chill": "ambient", "lo-fi": "ambient", "lofi": "ambient",
    "trance": "trance", "psytrance": "trance",
    "hip hop": "hip_hop", "hip-hop": "hip_hop", "rap": "hip_hop",
    "electronic": "electronic", "edm": "electronic",
}

SCENE_ALIASES = {
    "night": "night", "night cams": "night", "nighttime": "night",
    "world": "world", "global": "world", "worldwide": "world",
    "europe": "europe", "eu": "europe",
    "traffic": "traffic", "roads": "traffic", "cars": "traffic",
}

LAYOUT_ALIASES = {
    "2x2": "2x2", "4": "2x2", "quad": "2x2",
    "3x3": "3x3", "9": "3x3", "nine": "3x3",
    "single": "single", "1": "single", "fullscreen": "single", "solo": "single",
}


def parse_message(text: str) -> Optional[ParsedCommand]:
    """Parse a chat message into a structured command.

    Supports natural language patterns:
    - "play house", "switch to techno", "genre: ambient"
    - "night cams", "show europe", "switch to traffic"
    - "2x2", "3x3 grid", "layout single", "fullscreen"
    - "skip", "next track"
    - "volume 80", "vol 0.5"
    """
    text = text.strip().lower()

    # Skip/next track
    if text in ("skip", "next", "next track", "skip track"):
        return ParsedCommand(channel="stream:audio", action="skip_track", params={})

    # Volume control
    vol_match = re.match(r"(?:vol(?:ume)?)\s+(\d+\.?\d*)", text)
    if vol_match:
        vol = float(vol_match.group(1))
        if vol > 1.0:
            vol = vol / 100.0  # "volume 80" -> 0.8
        return ParsedCommand(channel="stream:audio", action="set_volume", params={"volume": min(vol, 1.0)})

    # Layout changes
    for alias, layout in LAYOUT_ALIASES.items():
        if alias in text and ("layout" in text or "grid" in text or text.strip() == alias):
            return ParsedCommand(channel="stream:layout", action="set_layout", params={"layout": layout})
    # Direct layout match (just "2x2", "3x3", "single")
    if text in LAYOUT_ALIASES:
        return ParsedCommand(
            channel="stream:layout", action="set_layout",
            params={"layout": LAYOUT_ALIASES[text]},
        )

    # Scene/theme changes
    for alias, scene in SCENE_ALIASES.items():
        if alias in text:
            return ParsedCommand(channel="stream:video", action="switch_scene", params={"scene": scene})

    # Genre/music changes
    for alias, genre in GENRE_ALIASES.items():
        if alias in text:
            return ParsedCommand(channel="stream:audio", action="set_genre", params={"genre": genre})

    return None


class ChatCommandHandler:
    """Receives parsed commands and publishes to the command bus."""

    def __init__(self, bus: CommandBus):
        self.bus = bus

    def handle_message(self, text: str, source: str = "chatbot") -> Optional[str]:
        """Parse and dispatch a chat message. Returns a response string or None."""
        parsed = parse_message(text)
        if parsed is None:
            return None

        cmd = parsed.to_command(source=source)
        self.bus.publish(cmd)

        responses = {
            "skip_track": "Skipping track...",
            "set_volume": f"Volume set to {cmd.params.get('volume', '?')}",
            "set_layout": f"Layout changed to {cmd.params.get('layout', '?')}",
            "switch_scene": f"Switching to {cmd.params.get('scene', '?')} cams",
            "set_genre": f"Switching to {cmd.params.get('genre', '?')}",
        }
        return responses.get(cmd.action, f"Command sent: {cmd.action}")
