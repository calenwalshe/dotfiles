# Requirements: Play History — Data Foundation Layer

**Defined:** 2026-04-12
**Core Value:** Every track change on the live radio stream is automatically logged to a durable append-only SQLite table, every track file in `music/clips/` has a row with `first_seen_at` and derivable stats, and a read API exists that future slugs (track-freshness rotation) can consume directly.

## Database Requirements

- [x] **PH-01**: `music/library.db` contains `library_tracks` and `plays` tables with WAL mode enabled

## Writer Requirements

- [x] **PH-02**: Every Liquidsoap track change fires a durable play event to the database within 10 seconds

## Ingest Requirements

- [x] **PH-03**: `analyze_library.py` populates `library_tracks` with one row per `music/clips/*.mp3` file

## API Requirements

- [x] **PH-04**: Four FastAPI read endpoints expose play history data at `/api/play-history/*`
- [x] **PH-05**: A stdlib-only `src/play_history.py` module provides direct-import access for future Python consumers

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| **PH-01** | Phase 1: Schema, Read Layer, and Library Ingest | Complete |
| **PH-02** | Phase 2: Writer Hook and Container Wire-up | Complete |
| **PH-03** | Phase 1: Schema, Read Layer, and Library Ingest | Complete |
| **PH-04** | Phase 1: Schema, Read Layer, and Library Ingest | Complete |
| **PH-05** | Phase 1: Schema, Read Layer, and Library Ingest | Complete |

**Coverage:**
- Database requirements: 1 total — 1 complete
- Writer requirements: 1 total — 1 complete
- Ingest requirements: 1 total — 1 complete
- API requirements: 2 total — 2 complete
- Unmapped: 0
