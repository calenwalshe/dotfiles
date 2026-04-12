# Requirements: Play History — Data Foundation Layer

**Defined:** 2026-04-12
**Core Value:** Every track change on the live radio stream is automatically logged to a durable append-only SQLite table, every track file in `music/clips/` has a row with `first_seen_at` and derivable stats, and a read API exists that future slugs (track-freshness rotation) can consume directly.

## Database Requirements

- [ ] **PH-01**: `music/library.db` contains `library_tracks` and `plays` tables with WAL mode enabled

## Writer Requirements

- [ ] **PH-02**: Every Liquidsoap track change fires a durable play event to the database within 10 seconds

## Ingest Requirements

- [ ] **PH-03**: `analyze_library.py` populates `library_tracks` with one row per `music/clips/*.mp3` file

## API Requirements

- [ ] **PH-04**: Four FastAPI read endpoints expose play history data at `/api/play-history/*`
- [ ] **PH-05**: A stdlib-only `src/play_history.py` module provides direct-import access for future Python consumers

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| **PH-01** | Phase 1: Schema, Read Layer, and Library Ingest | Pending |
| **PH-02** | Phase 2: Writer Hook and Container Wire-up | Pending |
| **PH-03** | Phase 1: Schema, Read Layer, and Library Ingest | Pending |
| **PH-04** | Phase 1: Schema, Read Layer, and Library Ingest | Pending |
| **PH-05** | Phase 1: Schema, Read Layer, and Library Ingest | Pending |

**Coverage:**
- Database requirements: 1 total — mapped
- Writer requirements: 1 total — mapped
- Ingest requirements: 1 total — mapped
- API requirements: 2 total — mapped
- Unmapped: 0
