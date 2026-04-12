---
slug: play-history
version: 1
timestamp: 2026-04-12T04:00:00Z
status: draft
---

# Spec: play-history

## 1. Problem

The self-hosted radio stream plays tracks in a static 4.5-hour linear loop — there is no record of when any track last played, so the scheduler cannot prefer fresher material. The operator experiences the same songs cycling every session. This slug builds the durable data foundation that makes track-freshness logic possible: a schema, a writer, and a read API, delivered as a minimal additive diff with zero refactors to existing code. The first downstream consumer (smart rotation) depends on this layer being in place; nothing useful can be built on top of track history without it.

---

## 2. Scope

### In Scope
- Two new SQLite tables (`library_tracks`, `plays`) in the existing `music/library.db`
- WAL mode migration — run once by extending `get_db()` in `src/web/app.py`
- `src/log_play.py` — writer script invoked by the Liquidsoap `on_track` hook (~25 lines)
- `agent-stack/liquidsoap/radio.liq` — add async `log_play` handler and wire with `source.on_track`
- `agent-stack/docker-compose.yml` — add `library.db` (rw) and `src/log_play.py` (ro) mounts to liquidsoap service
- `src/analyze_library.py` — extend with `upsert_library_tracks()` (~25 lines) called at end of `main()`
- `src/play_history.py` — new stdlib-only read module, 5 query functions (~80 lines)
- `src/web/app.py` — 4 new GET endpoints wrapping `play_history` module (~30 lines added)

### Out of Scope
- Track-freshness rotation logic (separate slug)
- Listener-facing stats dashboard or any UI
- Admin UI for `library.db`
- Listener-level statistics (unique listeners, sessions, geography)
- External music service integrations (Last.fm, Spotify, AcoustID)
- Changes to the existing `tracks` table (YT-pipeline-owned — untouched)
- Historical backfill from Icecast access logs or Liquidsoap stdout
- Retention/compaction jobs (revisit at ~1M rows, ~7+ years of continuous streaming)
- Changes to `dj_mixer.py`
- Any change to `config/track_metadata.json` or its role in the existing flow

---

## 3. Architecture Decision

**Chosen approach:** Two new tables in existing `library.db` (strict append-only `plays` + `library_tracks` index), Liquidsoap async hook → shell-out → `src/log_play.py` → direct sqlite INSERT, `analyze_library.py` extended for tracks ingest, read API split into a direct-import Python module and thin FastAPI wrappers.

**Rationale:** Purely additive — the entire diff can be reverted without touching existing tables or code paths. Strict append-only eliminates silent counter drift. Fire-and-forget writer (Liquidsoap `synchronous=false` + `thread.run`) means a DB failure never blocks playback. Extending `analyze_library.py` avoids a second process that already walks the same directories.

**Alternatives Considered:**
- **Reuse existing `tracks` table** — rejected. It is owned by the YouTube download pipeline (`youtube_url NOT NULL`, `status=downloading|ready|error`), cannot represent manually-added files, and breaking its schema couples this slug to the YT pipeline.
- **Hybrid append+denorm counters** — rejected. Denormalized `play_count` on `library_tracks` creates silent drift if any write is missed; deriving aggregates from the append log via SQL is free and drift-free.
- **Liquidsoap hook → curl → FastAPI ingest endpoint** — rejected. Adds an HTTP chain that drops events whenever the web app is down; the direct sqlite write is simpler and more resilient.
- **New standalone scanner process** — rejected. `analyze_library.py` already iterates `music/clips/`; a second process is redundant coupling.
- **Separate `play_history.db` file** — rejected. Violates the "single source of truth" hard constraint; two SQLite files split the data and complicate backup.

---

## 4. Interfaces

| Interface | Owner | This spec reads | This spec writes |
|---|---|---|---|
| `music/library.db` | Shared (YT pipeline owns `tracks`; this slug owns `library_tracks` + `plays`) | `library_tracks` (log_play.py FK lookup) | `library_tracks` (analyze_library.py), `plays` (log_play.py), schema+WAL (get_db) |
| `src/web/app.py` | Web app | `get_db()` pattern, existing endpoint structure | New `library_tracks`+`plays` creation in `get_db()`, 4 new GET endpoints |
| `src/log_play.py` | NEW — this slug | nothing | `plays` table |
| `src/play_history.py` | NEW — this slug | `library_tracks`, `plays` | nothing |
| `src/analyze_library.py` | Existing | existing results list | `library_tracks` table |
| `agent-stack/liquidsoap/radio.liq` | Liquidsoap config | existing `radio` source variable | `log_play` handler + `source.on_track` wire-up |
| `agent-stack/docker-compose.yml` | Agent-stack config | existing liquidsoap service definition | `library.db` rw mount + `src/log_play.py` ro mount |

**New table schema (exact SQL):**

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

**`log_play.py` interface:**
```
python3 src/log_play.py <file_path> <title> <artist>
```
Exit 0 always. Any failure silently discarded. No stdout output.

**`play_history.py` public API:**
```python
def track_stats(file_path: str) -> dict | None
    # Returns {play_count, last_played_at, first_seen_at, filename} or None

def tracks_played_since(iso_ts: str) -> list[dict]
    # Returns [{file_path, filename, played_at}, ...] since iso_ts

def tracks_never_played() -> list[dict]
    # Returns [{id, file_path, filename, first_seen_at}, ...] with zero plays

def tracks_by_days_since_play(max_days: int) -> list[dict]
    # Returns [{file_path, filename, last_played_at, play_count}, ...] not played in max_days

def recent_plays(limit: int = 100) -> list[dict]
    # Returns [{file_path, filename, played_at, source}, ...] most recent first
```

**FastAPI endpoints:**
```
GET /api/play-history/track?file_path=<path>   → track_stats()
GET /api/play-history/recent?limit=100         → recent_plays()
GET /api/play-history/never-played             → tracks_never_played()
GET /api/play-history/freshness?max_days=7     → tracks_by_days_since_play()
```

---

## 5. Dependencies

| Dependency | Version | Used for |
|---|---|---|
| Python 3 stdlib: `sqlite3`, `sys`, `datetime`, `pathlib` | 3.10+ | All new Python files |
| FastAPI | existing | 4 new read endpoints |
| Liquidsoap | 2.2.5 (deployed) | `source.on_track`, `thread.run`, `system`, `process.quote` |
| SQLite | 3.x (system) | `library.db` storage |
| `music/library.db` | existing | Tables added here |

---

## 6. Risks

- **DB bind-mount not added to liquidsoap container** — log_play.py fails silently, plays table stays empty. Mitigation: immediately test post-deploy with `docker exec liquidsoap python3 /home/agent/projects/yt_dj/src/log_play.py /home/agent/projects/yt_dj/music/clips/test.mp3 "Test" ""` and verify row in `plays`.
- **WAL mode sidecar files (`-wal`, `-shm`) break backup assumptions** — if the DB is backed up mid-transaction, the checkpoint may be incomplete. Mitigation: WAL files are harmless for a read-mostly DB; any full backup via `sqlite3 .dump` is consistent.
- **`first_seen_at` for pre-existing tracks is the first post-ship scan date** — no way to recover true first-added date from filesystem mtime. Mitigation: documented as accepted limitation; the freshness consumer only needs relative recency, not absolute first-added history.
- **Liquidsoap container runs as root; host DB file may have permission mismatch** — writer fails to open library.db. Mitigation: verify `chown` on `music/library.db` allows the container process; if needed, run `chmod 666 music/library.db` (acceptable for a local single-user system).
- **`source.on_track` receives absolute path in `filename` metadata** — confirmed from Liquidsoap docs and existing `radio.liq` map_metadata usage. If the path doesn't match `library_tracks.file_path`, the FK lookup returns NULL (play is still logged; just without the FK link). Mitigation: both the writer and `analyze_library.py` use the same absolute path convention from the bind-mount.

---

## 7. Sequencing

1. **Extend `get_db()` in `src/web/app.py`** — add `library_tracks`+`plays` table creation and `PRAGMA journal_mode=WAL`. Checkpoint: restart uvicorn (or yt-dj-web.service) and confirm `.schema` shows both new tables.
2. **Write `src/play_history.py`** — 5 query functions, stdlib-only, all return empty lists/None on empty DB. Checkpoint: `python3 -c "from src.play_history import recent_plays; print(recent_plays())"` returns `[]`.
3. **Add 4 FastAPI endpoints to `src/web/app.py`** — thin wrappers calling `play_history` functions. Checkpoint: `curl http://localhost:9093/api/play-history/recent` → `[]`, all 4 endpoints return HTTP 200.
4. **Extend `src/analyze_library.py`** with `upsert_library_tracks()` and call from `main()`. Checkpoint: run the script; `SELECT COUNT(*) FROM library_tracks WHERE removed_at IS NULL` equals `ls music/clips/*.mp3 | wc -l`.
5. **Write `src/log_play.py`** — argv-based writer, silent-fail. Checkpoint: direct invocation inserts one row into `plays`; re-invocation with same path inserts a second (append-only).
6. **Update `agent-stack/liquidsoap/radio.liq`** — add `log_play` function and `source.on_track(synchronous=false, ...)`. **Update `agent-stack/docker-compose.yml`** — add `library.db` rw mount and `src/log_play.py` ro mount to liquidsoap service. Checkpoint: `docker-compose restart liquidsoap` succeeds; on next track change, `SELECT * FROM plays ORDER BY id DESC LIMIT 1` returns a row within 10 seconds.

---

## 8. Tasks

- [ ] Extend `get_db()` in `src/web/app.py` to create `library_tracks` table, `plays` table, all indexes, and run `PRAGMA journal_mode=WAL`
- [ ] Write `src/play_history.py` with 5 functions: `track_stats`, `tracks_played_since`, `tracks_never_played`, `tracks_by_days_since_play`, `recent_plays`
- [ ] Add `GET /api/play-history/track`, `GET /api/play-history/recent`, `GET /api/play-history/never-played`, `GET /api/play-history/freshness` to `src/web/app.py`
- [ ] Extend `src/analyze_library.py` with `upsert_library_tracks()` and call from `main()`
- [ ] Write `src/log_play.py` (argv: file_path, title, artist; inserts into `plays`; exits 0 always)
- [ ] Add `log_play` handler and `source.on_track(synchronous=false, radio, log_play)` to `agent-stack/liquidsoap/radio.liq`
- [ ] Add `library.db` rw mount and `src/log_play.py` ro mount to liquidsoap service in `agent-stack/docker-compose.yml`
- [ ] Restart yt-dj-web.service and verify all 4 endpoints return HTTP 200 with valid JSON
- [ ] Run `python3 src/analyze_library.py` and verify `library_tracks` row count equals `music/clips/*.mp3` count
- [ ] Restart liquidsoap container and verify a play event lands in `plays` on next track change

---

## 9. Acceptance Criteria

- [ ] `music/library.db` contains both `library_tracks` and `plays` tables matching the schema in Section 4
- [ ] `PRAGMA journal_mode` on `library.db` returns `wal`
- [ ] After running `python3 src/analyze_library.py`, `SELECT COUNT(*) FROM library_tracks WHERE removed_at IS NULL` equals `ls music/clips/*.mp3 | wc -l`
- [ ] `GET /api/play-history/recent` returns HTTP 200 and a JSON array (empty is valid at t=0)
- [ ] `GET /api/play-history/never-played` returns HTTP 200 and a JSON array
- [ ] `GET /api/play-history/freshness?max_days=7` returns HTTP 200 and a JSON array
- [ ] `GET /api/play-history/track?file_path=<any_path_in_library_tracks>` returns HTTP 200 and a JSON object with `play_count`, `last_played_at`, `first_seen_at`
- [ ] After the next Liquidsoap track change, a row appears in `plays` within 10 seconds of the change
- [ ] Stream audio continues playing without interruption if `src/log_play.py` exits with error or is missing
- [ ] No existing endpoint in `src/web/app.py` returns a different response after this slug ships (regression check)
