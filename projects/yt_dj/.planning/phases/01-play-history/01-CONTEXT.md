# Phase 1: Schema, Read Layer, and Library Ingest - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Create the SQLite schema (both new tables + WAL mode), write the stdlib-only `play_history.py` read module, add 4 FastAPI GET endpoints, and extend `analyze_library.py` to populate `library_tracks`. After this phase, the schema exists, the read API is live (returning empty results), and running `analyze_library.py` fills the library index — all verifiable before any Liquidsoap changes. The stream is not touched in this phase.

</domain>

<decisions>
## Implementation Decisions

### Schema (from research F2)
Two new tables in `music/library.db`. Exact DDL:

```sql
CREATE TABLE IF NOT EXISTS library_tracks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path     TEXT    NOT NULL UNIQUE,
    filename      TEXT    NOT NULL,
    title         TEXT,
    artist        TEXT,
    bpm           REAL,
    camelot       TEXT,
    duration_s    REAL,
    first_seen_at TEXT    NOT NULL,
    removed_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_library_tracks_file_path  ON library_tracks(file_path);
CREATE INDEX IF NOT EXISTS idx_library_tracks_removed_at ON library_tracks(removed_at);

CREATE TABLE IF NOT EXISTS plays (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    library_track_id INTEGER,
    file_path        TEXT    NOT NULL,
    filename         TEXT    NOT NULL,
    played_at        TEXT    NOT NULL,
    source           TEXT    DEFAULT 'liquidsoap'
);
CREATE INDEX IF NOT EXISTS idx_plays_library_track_id ON plays(library_track_id, played_at DESC);
CREATE INDEX IF NOT EXISTS idx_plays_played_at         ON plays(played_at DESC);
CREATE INDEX IF NOT EXISTS idx_plays_file_path         ON plays(file_path);
```

WAL mode: `conn.execute("PRAGMA journal_mode=WAL")` inside `get_db()`.

### Migration strategy (from research F7 + Adjacent Finding #3)
The existing `get_db()` in `src/web/app.py` already uses `CREATE TABLE IF NOT EXISTS` for the `tracks` table — follow the same pattern. Add both new table definitions and the WAL PRAGMA to `get_db()`. No separate migration script, no manual operator step. The migration runs automatically on web app startup.

### `analyze_library.py` extension (from research F4)
Add `upsert_library_tracks(results)` function:
- `INSERT INTO library_tracks (...) ON CONFLICT(file_path) DO UPDATE SET ...` for each result
- Leave `first_seen_at` alone on conflict (only set on initial insert)
- Clear `removed_at = NULL` on re-add (resurrection)
- Soft-delete rows whose `file_path` is not in current scan (`UPDATE SET removed_at = now`)
- Call from end of `main()` after the JSON write

`DB_PATH` for `analyze_library.py`: `PROJECT / "music" / "library.db"` (mirrors existing `OUTPUT` path pattern).

### Read module (`src/play_history.py`) (from research F5)
Stdlib-only. `DB_PATH = Path(__file__).parent.parent / "music" / "library.db"`. Five functions:
- `track_stats(file_path)` → `{play_count, last_played_at, first_seen_at, filename}` or `None`
- `tracks_played_since(iso_ts)` → list of `{file_path, filename, played_at}`
- `tracks_never_played()` → list of `{id, file_path, filename, first_seen_at}`
- `tracks_by_days_since_play(max_days)` → list of `{file_path, filename, last_played_at, play_count}` — tracks not played in `max_days` (includes never-played)
- `recent_plays(limit=100)` → list of `{file_path, filename, played_at, source}`

Each function opens its own connection, queries, closes. No connection pooling.

### FastAPI endpoints (from research F5)
Add to `src/web/app.py` after the existing routes. Import `play_history` module at top of file. Four GET endpoints:
- `GET /api/play-history/track?file_path=<str>` → `track_stats()` or HTTP 404
- `GET /api/play-history/recent?limit=100` → `recent_plays()`
- `GET /api/play-history/never-played` → `tracks_never_played()`
- `GET /api/play-history/freshness?max_days=7` → `tracks_by_days_since_play()`

Response format: plain dict/list (no Pydantic response models needed — matches existing endpoint style in `src/web/app.py`).

### Timestamps
All timestamps ISO 8601 UTC: `datetime.now(timezone.utc).isoformat(timespec="seconds")`. Matches existing `created_at` convention in the `tracks` table.

### Claude's Discretion
- Exact SQL for the `track_stats` aggregate query (JOIN pattern vs subquery — either is fine; choose whichever is cleaner)
- Whether to use `conn.row_factory = sqlite3.Row` (matches `get_db()`) or plain tuples (either works for the module)
- Exact import location for `play_history` in `src/web/app.py` (top of file imports, after existing imports)

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/play-history/spec.md
- docs/cortex/specs/play-history/gsd-handoff.md
- docs/cortex/specs/play-history/project-context.md
- docs/cortex/contracts/play-history/contract-001.md
- docs/cortex/research/play-history/concept-20260412T035404Z.md
- docs/cortex/clarify/play-history/20260412T034512Z-clarify-brief.md

</canonical_refs>

<specifics>
## Specific Ideas

- `get_db()` in `src/web/app.py` is the right home for schema creation — it already creates the `tracks` table idempotently on every connection. Add the two new tables and WAL PRAGMA there.
- `analyze_library.py` already builds the full `results` list before writing JSON — `upsert_library_tracks(results)` slots cleanly after the JSON write with no restructuring.
- The `plays` table has a nullable `library_track_id` FK — this is intentional. If a track isn't in `library_tracks` yet (e.g., first play before `analyze_library.py` has run), the play is still logged with `library_track_id = NULL`. The writer resolves it later.
- `tracks_never_played()` should use a LEFT JOIN / NOT EXISTS pattern against `plays`, not a separate counter — keeps the append-only invariant clean.
- The `tracks_by_days_since_play` function is the one the freshness rotation slug will call most. Make it include never-played tracks (they're the freshest by definition).

</specifics>

<deferred>
## Deferred Ideas

- Track-freshness rotation logic (separate slug that calls `tracks_by_days_since_play`)
- Admin UI for `library.db` — manual `sqlite3` CLI is sufficient
- Listener-level statistics — out of scope
- Historical backfill from Icecast/Liquidsoap logs — accepted t=0 start
- Retention/compaction jobs — revisit at ~1M rows (~7.5 years)
- Replacing `config/track_metadata.json` — existing `dj_mixer.py` flow continues unchanged
- Changes to `dj_mixer.py` — separate rotation-fix slug

</deferred>

---

*Phase: 01-play-history*
*Context gathered: 2026-04-12 via /cortex-bridge*
