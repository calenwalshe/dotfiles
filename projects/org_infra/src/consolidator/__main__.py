"""CLI entry point: python -m src.consolidator --db path --dry-run --phase N --verbose"""

from __future__ import annotations

import argparse
import json
import sys

from src.consolidator import Consolidator, ConsolidatorLockError
from src.consolidator.audit import AuditLog
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.sqlite_store import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Consolidator")
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Run all phases but roll back changes")
    parser.add_argument("--phase", type=int, default=None, help="Run only phase N (1-9)")
    parser.add_argument("--verbose", action="store_true", help="Print audit entries to stderr as they happen")
    parser.add_argument("--audit-file", default=None, help="Path for JSONL audit log")
    parser.add_argument("--output-dir", default="projections", help="Directory for markdown projections")
    args = parser.parse_args()

    sqlite_store = SQLiteStore(args.db)
    store = ConsolidatorStore(sqlite_store)
    config = ConsolidatorConfig()
    audit = AuditLog(output_path=args.audit_file)

    consolidator = Consolidator(
        store=store,
        config=config,
        audit_log=audit,
        output_dir=args.output_dir,
    )

    try:
        result = consolidator.run(
            dry_run=args.dry_run,
            phase_number=args.phase,
            verbose=args.verbose,
        )
    except ConsolidatorLockError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        audit.close()
        store.close()

    print(f"Consolidation complete: {len(result.entries)} actions logged.")
    if args.dry_run:
        print("(dry-run mode — no changes were committed)")


if __name__ == "__main__":
    main()
