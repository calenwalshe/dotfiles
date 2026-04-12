# Play History — Data Foundation Layer

## What This Is

The self-hosted radio stream plays tracks in a static 4.5-hour linear loop — there is no record of when any track last played, so the scheduler cannot prefer fresher material. This milestone builds the durable data foundation that makes track-freshness logic possible: a schema, a writer, and a read API, delivered as a minimal additive diff with zero refactors to existing code. The first downstream consumer (smart rotation) depends on this layer being in place.

## Core Value

Every track change on the live radio stream is automatically logged to a durable append-only SQLite table, every track file in `music/clips/` has a row with `first_seen_at` and derivable stats, and a read API exists that future slugs (track-freshness rotation) can consume directly — without any changes to existing working code.

## Requirements

### Active

- [ ] **PH-01**: `music/library.db` contains `library_tracks` and `plays` tables with WAL mode enabled
- [ ] **PH-02**: Every Liquidsoap track change fires a durable play event to the database within 10 seconds
- [ ] **PH-03**: `analyze_library.py` populates `library_tracks` with one row per `music/clips/*.mp3` file
- [ ] **PH-04**: Four FastAPI read endpoints expose play history data at `/api/play-history/*`
- [ ] **PH-05**: A stdlib-only `src/play_history.py` module provides direct-import access for future Python consumers

### Out of Scope

- Track-freshness rotation logic (separate slug)
- Listener-facing stats dashboard or any UI
- Admin UI for `library.db`
- Listener-level statistics (unique listeners, sessions, geography)
- External music service integrations (Last.fm, Spotify, AcoustID)
- Changes to the existing `tracks` table (YT-pipeline-owned)
- Historical backfill from Icecast access logs or Liquidsoap stdout
- Retention/compaction jobs (revisit at ~1M rows, ~7+ years)
- Changes to `dj_mixer.py`
- Any change to `config/track_metadata.json`

## Context

**Baseline:** Radio stream replays a static 4.5-hour linear loop. No play history exists anywhere. Operator experiences the same songs cycling every session.

**Target:** Append-only plays log + library track index in `music/library.db`. Read API accessible both in-process (Python module import) and via HTTP.

**Ownership contract:** `docs/cortex/contracts/play-history/contract-001.md`

## Constraints

- **Additive only** — existing `dj_mixer.py`, Liquidsoap config, `analyze_library.py`, and web app must continue working unchanged except where this slug explicitly extends them
- **Single source of truth** — all play history lives in `music/library.db`; no JSON side-files for plays or library_tracks
- **Append-only `plays`** — no UPDATE/DELETE on the plays table; aggregates derived via SQL on read
- **Writer must not block playback** — fire-and-forget; a dropped play event is better than a stalled stream
- **No external dependencies** — stdlib `sqlite3`, FastAPI (existing), Liquidsoap (existing)
- **Write roots** — only: `src/web/app.py`, `src/play_history.py` (new), `src/log_play.py` (new), `src/analyze_library.py`, `agent-stack/liquidsoap/radio.liq`, `agent-stack/docker-compose.yml`

## Key Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| Two new tables, not reuse `tracks` | `tracks` is YT-pipeline-owned (`youtube_url NOT NULL`), breaks for manually-added files | `library_tracks` + `plays` added to existing `library.db` |
| Strict append-only `plays` | Zero drift risk vs denorm counters; aggregates free via SQL; future queries all work | No UPDATE/DELETE on `plays`; `play_count` and `last_played_at` derived on read |
| Shell-out writer, not HTTP | Fewer moving parts; works when web app is down; no HTTP chain | `log_play.py` called directly by Liquidsoap hook via `thread.run` + `system()` |
| Extend `analyze_library.py` | It already walks `music/clips/`; one process, one truth | `upsert_library_tracks()` called at end of `main()` |
| Both Python module + HTTP API | Module for in-process callers (dj_mixer); HTTP for out-of-process (curl, future dashboard) | `src/play_history.py` + 4 FastAPI wrappers |
