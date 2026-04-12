---
phase: 01-play-history
plan: "02"
subsystem: api
tags: [sqlite, fastapi, play-history, read-api, query-functions]

# Dependency graph
requires:
  - phase: 01-play-history/01-01
    provides: library_tracks and plays tables in music/library.db with all indexes and WAL mode
provides:
  - src/play_history.py — stdlib-only read module with 5 query functions
  - GET /api/play-history/recent — last N play events (newest first)
  - GET /api/play-history/never-played — library tracks with no plays
  - GET /api/play-history/freshness?max_days=N — tracks not played in N days
  - GET /api/play-history/track?file_path=<path> — per-track stats dict
affects:
  - dj_mixer.py freshness rotation (will call tracks_never_played / tracks_by_days_since_play)
  - future log_play.py writer (consumes same DB schema; read API available for verification)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stdlib-only read module pattern: play_history.py imports no FastAPI/third-party, safe in any context"
    - "Each query function opens and closes its own sqlite3.Connection — no connection reuse, no state leakage"
    - "FastAPI thin wrapper pattern: endpoint functions are one-liners delegating to play_history module"

key-files:
  created:
    - src/play_history.py
  modified:
    - src/web/app.py

key-decisions:
  - "from src import play_history import style — consistent with project root uvicorn invocation, avoids sys.path manipulation"
  - "Endpoint functions are synchronous def (not async) — sqlite3 is synchronous, no async benefit"
  - "tracks_by_days_since_play uses NULLS FIRST in ORDER BY — never-played tracks sort to top of freshness list"

patterns-established:
  - "Read module isolation: domain query logic lives in src/play_history.py, HTTP layer in web/app.py — testable independently"
  - "HAVING clause freshness filter: GROUP BY + LEFT JOIN + HAVING last_played_at IS NULL OR < cutoff avoids subquery for stale-track detection"

# Metrics
duration: ~2min
completed: 2026-04-12
---

# Phase 01 Plan 02: Play History Read API Summary

**Stdlib-only play_history.py module with 5 query functions and 4 FastAPI GET endpoints providing full read access to library_tracks + plays tables**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-12T04:55:58Z
- **Completed:** 2026-04-12T04:57:32Z
- **Tasks:** 2
- **Files created/modified:** 2

## Accomplishments
- `src/play_history.py` created (122 lines) — 5 query functions covering all read patterns the rotation logic and HTTP API need
- 4 GET endpoints wired into `src/web/app.py` at `/api/play-history/*` — all return HTTP 200 with valid JSON
- `/api/play-history/track` returns HTTP 404 for unknown file paths (correct behavior)
- All existing endpoints confirmed unaffected (regression check on `/api/tracks` passed)
- 69 tracks show as never-played at t=0 — correct, no play events recorded yet

## Task Commits

Each task was committed atomically:

1. **Task 1: Write src/play_history.py with 5 query functions** - `ca54dc2` (feat)
2. **Task 2: Add 4 FastAPI endpoints to src/web/app.py** - `ec9b8ab` (feat)

## Files Created/Modified
- `/home/agent/projects/yt_dj/src/play_history.py` — New file: 5 query functions (track_stats, tracks_played_since, tracks_never_played, tracks_by_days_since_play, recent_plays), stdlib-only
- `/home/agent/projects/yt_dj/src/web/app.py` — Added `from src import play_history` import and 4 GET endpoints at `/api/play-history/*`

## Decisions Made
- `from src import play_history` at the top of `app.py` alongside other third-party imports — consistent with how uvicorn is invoked (from project root), no sys.path manipulation needed
- Endpoint functions use `def` not `async def` — sqlite3 operations are synchronous and there is no I/O multiplexing benefit from async here
- `tracks_by_days_since_play` places never-played tracks first via `ORDER BY last_played_at ASC NULLS FIRST` — ensures the rotation engine sees the freshest (unplayed) tracks at the top of the freshness list

## Deviations from Plan
None - plan executed exactly as written.

## Verification Results

All 6 final verification checks passed:

| Check | Result |
|---|---|
| `python3 -c "from src.play_history import recent_plays; print(recent_plays())"` | `[]` |
| `GET /api/play-history/recent` | HTTP 200, `[]` |
| `GET /api/play-history/never-played` | HTTP 200, 69-item list |
| `GET /api/play-history/freshness?max_days=7` | HTTP 200, 69-item list |
| `GET /api/play-history/track?file_path=<bad>` | HTTP 404 |
| `GET /api/tracks` (regression) | HTTP 200, valid list |

## Next Phase Readiness
- Phase 01 is now complete: schema (01-01) + read API (01-02) both shipped
- `log_play.py` writer can now be added at any time — inserts into `plays` table, read API immediately reflects new data
- `dj_mixer.py` freshness rotation can call `play_history.tracks_never_played()` or `play_history.tracks_by_days_since_play(N)` directly as a Python import
- No blockers for next phase

---
*Phase: 01-play-history*
*Completed: 2026-04-12*
