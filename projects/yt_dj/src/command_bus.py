"""Redis Pub/Sub command bus for pipeline control."""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

import redis

logger = logging.getLogger(__name__)


@dataclass
class Command:
    channel: str
    action: str
    params: dict = field(default_factory=dict)
    source: str = "system"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        return json.dumps({
            "action": self.action,
            "params": self.params,
            "source": self.source,
            "timestamp": self.timestamp,
        })

    @classmethod
    def from_json(cls, channel: str, raw: str) -> Command:
        data = json.loads(raw)
        return cls(
            channel=channel,
            action=data["action"],
            params=data.get("params", {}),
            source=data.get("source", "unknown"),
            timestamp=data.get("timestamp", ""),
        )


CommandHandler = Callable[[Command], None]


class CommandBus:
    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        self.host = host
        self.port = port
        self._conn: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._handlers: dict[str, list[CommandHandler]] = {}
        self._listener_thread: Optional[threading.Thread] = None
        self._running = False

    def connect(self):
        self._conn = redis.Redis(host=self.host, port=self.port, decode_responses=True)
        self._pubsub = self._conn.pubsub()
        logger.info(f"Connected to Redis at {self.host}:{self.port}")

    def publish(self, cmd: Command):
        if not self._conn:
            raise RuntimeError("Not connected — call connect() first")
        self._conn.publish(cmd.channel, cmd.to_json())
        logger.debug(f"Published to {cmd.channel}: {cmd.action}")

    def subscribe(self, channel: str, handler: CommandHandler):
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

        if self._pubsub:
            self._pubsub.subscribe(**{
                channel: lambda msg: self._dispatch(msg)
            })
            logger.info(f"Subscribed to {channel}")

    def _dispatch(self, message: dict):
        if message["type"] != "message":
            return
        channel = message["channel"]
        try:
            cmd = Command.from_json(channel, message["data"])
            for handler in self._handlers.get(channel, []):
                handler(cmd)
        except Exception:
            logger.exception(f"Error dispatching message on {channel}")

    def listen(self):
        """Start listening for messages in a background thread."""
        if not self._pubsub:
            raise RuntimeError("Not connected — call connect() first")
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        logger.info("Command bus listener started")

    def _listen_loop(self):
        while self._running:
            try:
                message = self._pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    self._dispatch(message)
            except Exception:
                logger.exception("Error in listener loop")
                time.sleep(1)

    def stop(self):
        self._running = False
        if self._pubsub:
            self._pubsub.close()
        if self._conn:
            self._conn.close()
        logger.info("Command bus stopped")
