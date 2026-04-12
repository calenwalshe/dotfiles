"""Play history read module — stdlib-only, safe to import from any context."""
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "music" / "library.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def track_stats(file_path: str) -> dict | None:
    """Return play stats for a single track, or None if not in library_tracks."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, filename, first_seen_at FROM library_tracks WHERE file_path = ?",
            (file_path,)
        ).fetchone()
        if row is None:
            return None
        agg = conn.execute(
            """
            SELECT COUNT(*) AS play_count,
                   MAX(played_at) AS last_played_at
            FROM plays WHERE library_track_id = ?
            """,
            (row["id"],)
        ).fetchone()
        return {
            "file_path": file_path,
            "filename": row["filename"],
            "first_seen_at": row["first_seen_at"],
            "play_count": agg["play_count"] or 0,
            "last_played_at": agg["last_played_at"],
        }
    finally:
        conn.close()


def tracks_played_since(iso_ts: str) -> list[dict]:
    """Return play events that occurred after iso_ts (ISO8601 UTC string)."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT file_path, filename, played_at, source
            FROM plays WHERE played_at > ? ORDER BY played_at ASC
            """,
            (iso_ts,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def tracks_never_played() -> list[dict]:
    """Return library_tracks rows that have no matching plays row."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT lt.id, lt.file_path, lt.filename, lt.first_seen_at
            FROM library_tracks lt
            WHERE lt.removed_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM plays p WHERE p.library_track_id = lt.id
              )
            ORDER BY lt.first_seen_at ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def tracks_by_days_since_play(max_days: int) -> list[dict]:
    """
    Return active library_tracks not played in the last max_days days.
    Includes tracks that have never been played (freshest by definition).
    """
    conn = _connect()
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=max_days)
        ).isoformat(timespec="seconds")
        rows = conn.execute(
            """
            SELECT lt.file_path, lt.filename, lt.first_seen_at,
                   COUNT(p.id)   AS play_count,
                   MAX(p.played_at) AS last_played_at
            FROM library_tracks lt
            LEFT JOIN plays p ON p.library_track_id = lt.id
            WHERE lt.removed_at IS NULL
            GROUP BY lt.id
            HAVING last_played_at IS NULL OR last_played_at < ?
            ORDER BY last_played_at ASC NULLS FIRST
            """,
            (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def recent_plays(limit: int = 100) -> list[dict]:
    """Return the most recent play events, newest first."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT file_path, filename, played_at, source
            FROM plays ORDER BY played_at DESC LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
