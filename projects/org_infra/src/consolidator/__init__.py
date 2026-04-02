"""Knowledge Consolidator — runs phases in order, returns audit log.

Phase order:
1. embed — generate embeddings for claims without them
2. contradict — detect contradictions via NLI
3. corroborate — find independently corroborated L1 claims
4. promote L0→L1 — rule-based gate
5. promote L1→L2 — corroboration + Claude Haiku validation
6. promote L2→L3 — Claude Sonnet review (human approval gate)
7. decay — time-based confidence decay
8. archive — move expired/promoted claims to archive
9. project — generate markdown projections
"""

from __future__ import annotations

import fcntl
import sys
from pathlib import Path
from typing import Any, Callable

from src.consolidator.audit import AuditLog
from src.consolidator.budget import BudgetTracker
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.phases.archive import run_archive
from src.consolidator.phases.contradict import NliFn, ClusterFn, run_contradict
from src.consolidator.phases.corroborate import run_corroborate
from src.consolidator.phases.decay import run_decay
from src.consolidator.phases.embed import EmbedFn, run_embed
from src.consolidator.phases.promote import (
    run_promote,
    run_promote_l1_to_l2,
    run_promote_l2_to_l3,
    run_review_ambiguous,
)
from src.consolidator.store_adapter import ConsolidatorStore

LOCK_FILE = "/tmp/consolidator.lock"


class _NoCommitConnection:
    """Wrapper around sqlite3.Connection that makes commit() a no-op.

    Used for dry-run mode: changes accumulate in the implicit transaction
    and get rolled back at the end.
    """

    def __init__(self, conn):
        self._conn = conn

    def commit(self):
        pass  # no-op in dry-run

    def rollback(self):
        self._conn.rollback()

    def __getattr__(self, name):
        return getattr(self._conn, name)


class ConsolidatorLockError(RuntimeError):
    """Raised when another consolidation cycle is already running."""
    pass


class Consolidator:
    """Runs consolidation phases in order against a store."""

    def __init__(
        self,
        store: ConsolidatorStore,
        config: ConsolidatorConfig | None = None,
        audit_log: AuditLog | None = None,
        *,
        embed_fn: EmbedFn | None = None,
        nli_fn: NliFn | None = None,
        cluster_fn: ClusterFn | None = None,
        llm_client: Any | None = None,
        output_dir: str | Path = "projections",
    ) -> None:
        self.store = store
        self.config = config or ConsolidatorConfig()
        self.audit_log = audit_log or AuditLog()
        self.embed_fn = embed_fn
        self.nli_fn = nli_fn
        self.cluster_fn = cluster_fn
        self.llm_client = llm_client
        self.output_dir = Path(output_dir)
        self.budget = BudgetTracker(budget_cap=self.config.budget_cap_per_cycle)
        self._lock_fd = None

    def _acquire_lock(self) -> None:
        """Acquire file lock. Raises ConsolidatorLockError if already held."""
        try:
            self._lock_fd = open(LOCK_FILE, "w")
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_fd.write(str(Path("/proc/self").resolve()))
            self._lock_fd.flush()
        except (IOError, OSError):
            if self._lock_fd:
                self._lock_fd.close()
                self._lock_fd = None
            raise ConsolidatorLockError(
                "Another consolidation cycle is already running. "
                f"Lock file: {LOCK_FILE}"
            )

    def _release_lock(self) -> None:
        """Release file lock."""
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
                self._lock_fd.close()
            except (IOError, OSError):
                pass
            self._lock_fd = None

    def run(
        self,
        *,
        dry_run: bool = False,
        phase_number: int | None = None,
        verbose: bool = False,
    ) -> AuditLog:
        """Run all phases (or a single phase) and return the audit log.

        Args:
            dry_run: If True, wraps everything in a transaction that gets rolled back.
            phase_number: If set, run only that phase number (1-9).
            verbose: If True, print audit entries to stderr as they happen.
        """
        self._acquire_lock()
        try:
            return self._run_phases(
                dry_run=dry_run,
                phase_number=phase_number,
                verbose=verbose,
            )
        finally:
            self._release_lock()

    def _run_phases(
        self,
        *,
        dry_run: bool = False,
        phase_number: int | None = None,
        verbose: bool = False,
    ) -> AuditLog:
        # If dry_run, wrap the connection so commits are no-ops.
        # Changes accumulate but get rolled back at the end.
        original_conn = None
        if dry_run:
            original_conn = self.store._store.conn
            self.store._store.conn = _NoCommitConnection(original_conn)

        original_record = self.audit_log.record
        if verbose:
            import json

            def verbose_record(**kwargs):
                original_record(**kwargs)
                entry = self.audit_log.entries[-1]
                print(json.dumps(entry), file=sys.stderr)

            self.audit_log.record = verbose_record

        try:
            # Map of phase number -> runner
            phase_runners = {
                1: self._run_embed,
                2: self._run_contradict,
                3: self._run_corroborate,
                4: self._run_promote_l0_l1,
                5: self._run_promote_l1_l2,
                6: self._run_promote_l2_to_l3,
                7: self._run_decay,
                8: self._run_archive,
                9: self._run_project,
            }

            if phase_number is not None:
                if phase_number not in phase_runners:
                    raise ValueError(f"Unknown phase number: {phase_number}")
                phase_runners[phase_number]()
            else:
                # Run phases 1-3 first (embed, contradict, corroborate)
                self._run_embed()
                ambiguous = self._run_contradict()
                corroboration_results = self._run_corroborate()

                # Phase 4a: L0→L1
                self._run_promote_l0_l1()

                # Phase 4b: L1→L2 with corroboration results
                self._run_promote_l1_l2(corroboration_results)

                # Review ambiguous contradictions
                if ambiguous:
                    run_review_ambiguous(
                        self.store,
                        self.audit_log,
                        ambiguous,
                        self.budget,
                        llm_client=self.llm_client,
                    )

                # Phase 4c: L2→L3
                self._run_promote_l2_to_l3()

                # Phases 5-9
                self._run_decay()
                self._run_archive()
                self._run_project()

        finally:
            # Restore original record method
            self.audit_log.record = original_record

            if dry_run and original_conn is not None:
                self.store._store.conn = original_conn
                original_conn.rollback()

        return self.audit_log

    def _run_embed(self):
        run_embed(self.store, self.config, self.audit_log, embed_fn=self.embed_fn)

    def _run_contradict(self):
        return run_contradict(
            self.store,
            self.config,
            self.audit_log,
            nli_fn=self.nli_fn,
            cluster_fn=self.cluster_fn,
        )

    def _run_corroborate(self):
        return run_corroborate(self.store, self.config, self.audit_log)

    def _run_promote_l0_l1(self):
        run_promote(self.store, self.config, self.audit_log)

    def _run_promote_l1_l2(self, corroboration_results=None):
        if corroboration_results is None:
            corroboration_results = []
        run_promote_l1_to_l2(
            self.store,
            self.config,
            self.audit_log,
            corroboration_results,
            self.budget,
            llm_client=self.llm_client,
        )

    def _run_promote_l2_to_l3(self):
        return run_promote_l2_to_l3(
            self.store,
            self.config,
            self.audit_log,
            self.budget,
            llm_client=self.llm_client,
        )

    def _run_decay(self):
        run_decay(self.store, self.config, self.audit_log)

    def _run_archive(self):
        run_archive(self.store, self.config, self.audit_log)

    def _run_project(self):
        from src.projectors.markdown import run as run_projector
        run_projector(self.store._store, self.output_dir)
        self.audit_log.record(
            phase="project",
            action="project",
            claim_id="*",
            reason=f"Generated projections to {self.output_dir}",
        )
