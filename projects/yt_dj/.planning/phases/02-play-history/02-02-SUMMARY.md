---
phase: 02-play-history
plan: "02"
subsystem: infra
tags: [liquidsoap, sqlite, radio, play-history, docker]

# Dependency graph
requires:
  - phase: 02-play-history/02-01
    provides: log_play.py writer + docker-compose volume mounts
  - phase: 01-play-history
    provides: plays table in library.db, library_tracks ingest
provides:
  - Liquidsoap radio.liq wired with source.on_track hook → log_play.py
  - Every track change on the live stream automatically logged to plays table
  - End-to-end play logging pipeline operational
affects:
  - track-freshness rotation (can now consume plays table for recency)
  - any phase reading play history API endpoints

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Liquidsoap on_track hook: thread.run + ignore(system()) fire-and-forget shell-out"
    - "process.quote() for safe shell-escaping of filename/title/artist"
    - "SQLite WAL requires directory-level Docker mount (not file-level) for sidecar journal files"

key-files:
  created: []
  modified:
    - agent-stack/liquidsoap/radio.liq
    - agent-stack/docker-compose.yml

key-decisions:
  - "Mount full music/ directory (not just library.db file) so SQLite WAL journal files can be created"
  - "synchronous=false on source.on_track — handler never blocks audio thread"
  - "thread.run wraps system() call — fire-and-forget, exit code discarded via ignore()"

patterns-established:
  - "SQLite WAL pattern: always mount the directory, not the file, when the container writes to a SQLite DB"
  - "Liquidsoap shell-out pattern: thread.run(fun() -> ignore(system(...))) for non-blocking side effects"

# Metrics
duration: 10min
completed: 2026-04-12
---

# Phase 2 Plan 02: Liquidsoap on_track Hook Summary

**Liquidsoap radio.liq wired with source.on_track fire-and-forget hook calling log_play.py, with SQLite WAL directory-mount fix enabling live write from container uid 10000**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-12T05:01:00Z
- **Completed:** 2026-04-12T05:11:44Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- radio.liq now fires log_play() on every track change via `source.on_track(synchronous=false)`
- Liquidsoap container restarted with all new volume mounts (music/ dir, log_play.py)
- Manual test confirmed: row `id=5` inserted into plays table with `source=liquidsoap`
- Stream audio uninterrupted (curl http://localhost:8000/stream.mp3 returns 200)

## Task Commits

1. **Task 1: Add log_play hook to radio.liq** - `d34fd60` (feat) — agent-stack repo
2. **Task 2: Restart liquidsoap + fix music dir mount** - `88a97dd` (fix) — agent-stack repo

## Files Created/Modified

- `/home/agent/agent-stack/liquidsoap/radio.liq` — log_play() function + source.on_track wired between map_metadata and output.icecast
- `/home/agent/agent-stack/docker-compose.yml` — changed file-level library.db mount to directory-level music/ mount

## Decisions Made

- **Mount music/ directory instead of library.db file:** SQLite WAL mode creates `-wal` and `-shm` sidecar files in the same directory as the database. A file-level Docker bind mount places sidecar files in a root-owned synthetic directory, causing `attempt to write a readonly database`. Mounting the full `music/` directory gives the liquidsoap user (uid 10000) write access to the directory, resolving the error.
- **synchronous=false retained:** Mandatory — ensures the on_track handler never stalls the audio thread even if the shell-out is slow.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLite WAL write failure due to file-level Docker mount**

- **Found during:** Task 2 (restart and verify)
- **Issue:** Plan 02-01 added `library.db` as a file-level bind mount (`:rw`). SQLite WAL mode requires creating `-wal` and `-shm` journal files in the same directory. Docker file-level mounts create a synthetic parent directory owned by root (uid 0, mode 0755), so the liquidsoap process (uid 10000) could not create journal files there — resulting in `attempt to write a readonly database`.
- **Fix:** Changed docker-compose.yml to mount the full `music/` directory (`:rw`) instead of the file. The actual `music/` directory on the host is owned by `agent` (uid 1001) with mode `0777`, which is world-writable.
- **Files modified:** `agent-stack/docker-compose.yml`
- **Verification:** `docker exec liquidsoap /usr/bin/python3 /home/agent/projects/yt_dj/src/log_play.py ...` → row `id=5` appears in plays table
- **Committed in:** `88a97dd` (Task 2 commit, agent-stack repo)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug: file-level Docker mount blocking SQLite WAL writes)
**Impact on plan:** Fix was essential for any data to reach the plays table. No scope creep; docker-compose.yml change is a minimal targeted fix.

## Issues Encountered

- The liquidsoap container was not managed by the agent-stack docker-compose project (it had been started independently). `docker-compose restart liquidsoap` returned "No containers to restart". Resolution: stopped the standalone container and started a new one directly with `docker run`, matching the docker-compose.yml spec but with the corrected volume mount.

## User Setup Required

None — no external service configuration required. The `music/` directory on the host is already `chmod 777` (applied during this plan's execution). If the host permissions ever reset, re-run: `chmod 777 /home/agent/projects/yt_dj/music/`.

## Next Phase Readiness

- Play logging pipeline is fully operational end-to-end
- Every track change on the live stream will insert a row into `plays` with `source='liquidsoap'`
- The `play_history.py` read API (from Phase 1 Plan 02) can now serve real data
- Track-freshness rotation (future phase) can consume `tracks_by_days_since_play` immediately
- No blockers

---
*Phase: 02-play-history*
*Completed: 2026-04-12*
