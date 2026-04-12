#!/usr/bin/env python3
"""
Play event writer — called by Liquidsoap on_track hook.
Usage: python3 log_play.py <file_path> <title> <artist>
Always exits 0. A dropped event is better than a stalled stream.
"""
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "music" / "library.db"


def main() -> None:
    argv = sys.argv[1:]
    file_path = argv[0] if len(argv) > 0 else ""
    title     = argv[1] if len(argv) > 1 else ""
    artist    = argv[2] if len(argv) > 2 else ""

    filename = Path(file_path).name if file_path else ""
    played_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        # Resolve library_track_id (may be NULL if track not yet indexed)
        row = conn.execute(
            "SELECT id FROM library_tracks WHERE file_path = ?", (file_path,)
        ).fetchone()
        library_track_id = row[0] if row else None

        conn.execute(
            """
            INSERT INTO plays (library_track_id, file_path, filename, played_at, source)
            VALUES (?, ?, ?, ?, 'liquidsoap')
            """,
            (library_track_id, file_path, filename, played_at),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Silent fail — stream must never block on a logging error
    sys.exit(0)
