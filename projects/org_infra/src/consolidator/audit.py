"""Audit log for consolidation actions — in-memory accumulator + JSON lines file."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    """Records every action taken during a consolidation cycle.

    Each entry is a structured dict with: phase, action, claim_id, reason, timestamp, details.
    Entries accumulate in memory and optionally flush to a JSONL file.
    """

    def __init__(self, output_path: str | Path | None = None) -> None:
        self.entries: list[dict[str, Any]] = []
        self.output_path = Path(output_path) if output_path else None
        self._file = None
        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.output_path, "a")

    def record(
        self,
        *,
        phase: str,
        action: str,
        claim_id: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "phase": phase,
            "action": action,
            "claim_id": claim_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        self.entries.append(entry)
        if self._file:
            self._file.write(json.dumps(entry) + "\n")
            self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
