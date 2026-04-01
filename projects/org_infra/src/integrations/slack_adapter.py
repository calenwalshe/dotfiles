"""Slack comms adapter for PM agent stakeholder communication.

Requires SLACK_BOT_TOKEN and SLACK_CHANNEL_ID environment variables.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass

from src.integrations.comms import CommsAdapter, CommsMessage, CommsResponse


class SlackAdapter(CommsAdapter):
    """Real Slack adapter using Web API."""

    def __init__(
        self,
        bot_token: str | None = None,
        channel_id: str | None = None,
    ) -> None:
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN", "")
        self.channel_id = channel_id or os.environ.get("SLACK_CHANNEL_ID", "")
        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN required (env var or constructor arg)")
        if not self.channel_id:
            raise ValueError("SLACK_CHANNEL_ID required (env var or constructor arg)")

    def send(self, message: CommsMessage) -> bool:
        """Send a message to the Slack channel."""
        payload = {
            "channel": self.channel_id,
            "text": f"*{message.subject}*\n\nTo: {message.to}\n\n{message.body}",
        }
        try:
            req = urllib.request.Request(
                "https://slack.com/api/chat.postMessage",
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {self.bot_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                return result.get("ok", False)
        except (urllib.error.URLError, json.JSONDecodeError):
            return False

    def poll_responses(self) -> list[CommsResponse]:
        """Poll for responses in the channel (last 10 messages)."""
        try:
            params = f"channel={self.channel_id}&limit=10"
            req = urllib.request.Request(
                f"https://slack.com/api/conversations.history?{params}",
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if not result.get("ok"):
                    return []

                responses: list[CommsResponse] = []
                for msg in result.get("messages", []):
                    # Skip bot's own messages
                    if msg.get("bot_id"):
                        continue
                    responses.append(
                        CommsResponse(
                            from_stakeholder=msg.get("user", "unknown"),
                            body=msg.get("text", ""),
                        )
                    )
                return responses
        except (urllib.error.URLError, json.JSONDecodeError):
            return []
