"""Comms adapter for PM agent stakeholder communication.

Abstract interface + mock implementation for testing.
Real implementation would use Slack API or email.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CommsMessage:
    to: str
    subject: str
    body: str


@dataclass
class CommsResponse:
    from_stakeholder: str
    body: str
    sentiment: str = ""


class CommsAdapter(ABC):
    @abstractmethod
    def send(self, message: CommsMessage) -> bool:
        """Send a message to a stakeholder. Returns True on success."""

    @abstractmethod
    def poll_responses(self) -> list[CommsResponse]:
        """Poll for stakeholder responses."""


class MockCommsAdapter(CommsAdapter):
    """Mock adapter that records sent messages and returns canned responses."""

    def __init__(self, canned_responses: list[CommsResponse] | None = None) -> None:
        self.sent: list[CommsMessage] = []
        self.canned_responses: list[CommsResponse] = canned_responses or [
            CommsResponse(
                from_stakeholder="eng_lead",
                body="Looks reasonable. Concerned about timeline.",
                sentiment="cautious",
            )
        ]
        self._polled = False

    def send(self, message: CommsMessage) -> bool:
        self.sent.append(message)
        return True

    def poll_responses(self) -> list[CommsResponse]:
        if not self._polled:
            self._polled = True
            return self.canned_responses
        return []
