---
phase: 01-play-history
plan: "01"
subsystem: database
tags: [sqlite, wal, library_tracks, plays, schema, analyze_library, upsert]

# Dependency graph
requires: []
provides:
  - library_tracks table in music/library.db (one row per mp3 file, BPM/camelot/duration indexed)
  - plays table in music/library.db (append-only play log, ready for Liquidsoap writer)
  - WAL mode on library.db (concurrent read-write without blocking)
  - 5 indexes covering file_path, removed_at, played_at, library_track_id query patterns
  - upsert_library_tracks() in analyze_library.py (populates library_tracks from music/clips/ + music/library/)
affects:
  - 01-play-history/01-02 (read API — depends on library_tracks + plays tables existing)
  - future play writer (log_play.py — depends on plays table schema)
  - freshness rotation slug (depends on library_tracks.removed_at + plays.played_at)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Schema-as-code: CREATE TABLE IF NOT EXISTS in get_db() — auto-migrates on startup, no separate migration step"
    - "Upsert with ON CONFLICT(file_path) DO UPDATE — leaves first_seen_at alone, clears removed_at on re-add"
    - "Soft-delete pattern: removed_at TEXT NULL — absent files marked, never hard-deleted"
    - "WAL mode set idempotently in get_db() — no external setup required"

key-files:
  created: []
  modified:
    - src/web/app.py
    - src/analyze_library.py

key-decisions:
  - "WAL mode set in get_db() after CREATE TABLE tracks commit — idempotent, runs every connection but SQLite no-ops if already WAL"
  - "upsert_library_tracks() opens its own sqlite3.connect() — does not reuse app's get_db() to avoid row_factory coupling"
  - "DB count (69) > clips count (54) is correct — analyze_library.py scans both music/clips/ and music/library/ (15 additional tracks)"

patterns-established:
  - "Schema auto-migration: add new CREATE TABLE IF NOT EXISTS to get_db() — runs on startup, safe to redeploy"
  - "Soft-delete via removed_at: files removed from disk are marked, not deleted from DB, preserving play history"

# Metrics
duration: 2min
completed: 2026-04-12
---

# Phase 01 Plan 01: Schema Foundation Summary

**SQLite library_tracks and plays tables with WAL mode in music/library.db, plus upsert_library_tracks() populating 69 tracks from analyze_library.py**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-12T04:52:53Z
- **Completed:** 2026-04-12T04:54:24Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `library_tracks` and `plays` tables created with exact DDL from spec, auto-migrating on next web app startup
- WAL mode enabled on `music/library.db` — concurrent reads no longer blocked during writes
- `upsert_library_tracks()` added to `analyze_library.py` — upserts all 69 tracks (54 clips + 15 library) on first run
- All 5 indexes in place covering the query patterns the read API and freshness rotation will use

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend get_db() with library_tracks, plays, indexes, WAL mode** - `e6ff396` (feat)
2. **Task 2: Add upsert_library_tracks() to analyze_library.py** - `046c853` (feat)

## Files Created/Modified
- `/home/agent/projects/yt_dj/src/web/app.py` - Added PRAGMA journal_mode=WAL, CREATE TABLE library_tracks, CREATE TABLE plays, 5 indexes, second conn.commit() to get_db()
- `/home/agent/projects/yt_dj/src/analyze_library.py` - Added sqlite3/datetime imports, DB_PATH constant, upsert_library_tracks() function, call in main()

## Decisions Made
- `upsert_library_tracks()` opens its own `sqlite3.connect()` rather than reusing `get_db()` — avoids pulling in `row_factory = sqlite3.Row` into a plain analytics script that returns plain tuples
- WAL PRAGMA placed after the first `conn.commit()` (after `tracks` table creation) — separates legacy schema setup from new schema setup, preserves original code structure

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- First `get_db()` call (via `.schema` check) returned empty before the web service received a real HTTP request — resolved by hitting `/api/tracks` to trigger `get_db()` initialization. Not a code issue; expected behavior for a lazy-connect pattern.

## User Setup Required
None - no external service configuration required. Schema auto-migrates on next `yt-dj-web.service` restart (already done).

## Next Phase Readiness
- `library_tracks` and `plays` tables are live in `music/library.db` with 69 rows in `library_tracks`
- Ready for Plan 02: `play_history.py` read module and 4 FastAPI GET endpoints
- No blockers

---
*Phase: 01-play-history*
*Completed: 2026-04-12*
