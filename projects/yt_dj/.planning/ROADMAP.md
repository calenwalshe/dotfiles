# Roadmap: Play History — Data Foundation Layer

## Overview

Build a durable play-history data foundation layer for the self-hosted radio stream — two new SQLite tables in `music/library.db`, a fire-and-forget Liquidsoap play-event writer, a library-track ingest extension to `analyze_library.py`, a stdlib-only Python read module, and four FastAPI read endpoints — so that every track change on the live radio stream is durably logged and queryable by future slugs (first consumer: track-freshness rotation logic).

## Phases

### Phase 1: Schema, Read Layer, and Library Ingest

**Goal**: Create the SQLite schema (both tables + WAL mode), write the stdlib-only `play_history.py` read module, add 4 FastAPI endpoints, and extend `analyze_library.py` to populate `library_tracks`. After this phase, the schema exists, the read API is live (returning empty results), and running `analyze_library.py` fills the library index — all verifiable before any Liquidsoap changes.

**Depends on**: Nothing

**Requirements**: PH-01, PH-03, PH-04, PH-05

**Success Criteria** (what must be TRUE):
1. `music/library.db` contains both `library_tracks` and `plays` tables matching the schema in `docs/cortex/specs/play-history/spec.md` Section 4
2. `PRAGMA journal_mode` on `library.db` returns `wal`
3. After running `python3 src/analyze_library.py`, `SELECT COUNT(*) FROM library_tracks WHERE removed_at IS NULL` equals `ls music/clips/*.mp3 | wc -l`
4. `GET /api/play-history/recent` returns HTTP 200 and a JSON array (empty is valid at t=0)
5. `GET /api/play-history/never-played` returns HTTP 200 and a JSON array
6. `GET /api/play-history/freshness?max_days=7` returns HTTP 200 and a JSON array
7. `GET /api/play-history/track?file_path=<any_path_in_library_tracks>` returns HTTP 200 and a JSON object with `play_count`, `last_played_at`, `first_seen_at`
8. No existing endpoint in `src/web/app.py` returns a different response after this slug ships (regression check)

**Research**: Unlikely — all implementation decisions resolved in Cortex research dossier

**Plans**: 2 plans (complete)

---

### Phase 2: Writer Hook and Container Wire-up

**Goal**: Write `src/log_play.py`, add the `source.on_track` hook to `radio.liq`, and update `docker-compose.yml` with the required volume mounts. After this phase, Liquidsoap automatically logs every track change to the `plays` table — the full data foundation is live.

**Depends on**: Phase 1 (schema and `library_tracks` must exist before writer runs FK lookups)

**Requirements**: PH-02

**Success Criteria** (what must be TRUE):
1. After the next Liquidsoap track change, a row appears in `plays` within 10 seconds of the change
2. Stream audio continues playing without interruption if `src/log_play.py` exits with error or is missing

**Research**: Unlikely — Liquidsoap async hook pattern resolved in Cortex research dossier (F3)

**Plans**: 2 plans (complete)

---

## Progress

| Phase | Plans Complete | Status | Completed |
|---|---|---|---|
| Phase 1: Schema, Read Layer, and Library Ingest | 2/2 | Complete | 2026-04-12 |
| Phase 2: Writer Hook and Container Wire-up | 2/2 | Complete | 2026-04-12 |
