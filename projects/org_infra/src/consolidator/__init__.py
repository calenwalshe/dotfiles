"""Knowledge Consolidator — runs phases in order, returns audit log.

Each phase is a callable: (store, config, audit_log) -> list[str] of actions taken.
"""

from __future__ import annotations

from typing import Callable

from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.phases.archive import run_archive
from src.consolidator.phases.decay import run_decay
from src.consolidator.phases.promote import run_promote
from src.consolidator.store_adapter import ConsolidatorStore

# Type alias for a phase function
PhaseFunc = Callable[[ConsolidatorStore, ConsolidatorConfig, AuditLog], list[str]]

# Ordered phase registry — phases run in this sequence
PHASES: list[tuple[int, str, PhaseFunc]] = [
    (4, "promote", run_promote),
    (5, "decay", run_decay),
    (6, "archive", run_archive),
]


class Consolidator:
    """Runs consolidation phases in order against a store."""

    def __init__(
        self,
        store: ConsolidatorStore,
        config: ConsolidatorConfig | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self.store = store
        self.config = config or ConsolidatorConfig()
        self.audit_log = audit_log or AuditLog()

    def run(
        self,
        *,
        dry_run: bool = False,
        phase_number: int | None = None,
    ) -> AuditLog:
        """Run all phases (or a single phase) and return the audit log."""
        phases_to_run = PHASES
        if phase_number is not None:
            phases_to_run = [(n, name, fn) for n, name, fn in PHASES if n == phase_number]
            if not phases_to_run:
                raise ValueError(f"Unknown phase number: {phase_number}")

        for _num, _name, phase_fn in phases_to_run:
            phase_fn(self.store, self.config, self.audit_log)

        return self.audit_log
