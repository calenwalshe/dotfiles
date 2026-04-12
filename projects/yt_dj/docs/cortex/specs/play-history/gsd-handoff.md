# GSD Handoff: play-history

<!-- Produced by /cortex-spec. Import this into GSD explicitly. -->
<!-- Do NOT auto-execute — human must import and approve. -->

## Objective

Build a durable data foundation layer for the self-hosted radio stream: a SQLite schema (two new tables in `music/library.db`), a fire-and-forget Liquidsoap play-event writer (`src/log_play.py`), a library-track ingest extension to `analyze_library.py`, a stdlib-only Python read module (`src/play_history.py`), and four FastAPI read endpoints — all additive, zero refactors to existing code.

Success means: every track change on the live stream is automatically logged to a durable append-only SQLite table, every track file in `music/clips/` has a row with `first_seen_at` and derivable stats, and a read API exists that future slugs (track-freshness rotation) can consume directly.

## Deliverables

| File | Status | Change |
|---|---|---|
| `src/web/app.py` | existing | Extend `get_db()` with schema + WAL; add 4 GET endpoints |
| `src/play_history.py` | NEW | 5 query functions, stdlib-only, ~80 lines |
| `src/log_play.py` | NEW | Argv writer, silent-fail, ~25 lines |
| `src/analyze_library.py` | existing | Add `upsert_library_tracks()` + call from `main()`, ~25 lines |
| `agent-stack/liquidsoap/radio.liq` | existing | Add `log_play` handler + `source.on_track` wire-up, ~15 lines |
| `agent-stack/docker-compose.yml` | existing | Add 2 volume mounts to liquidsoap service |

## Requirements

None formalized.

## Tasks

1. - [ ] Extend `get_db()` in `src/web/app.py`:
   - Add `CREATE TABLE IF NOT EXISTS library_tracks (...)` with the exact schema from spec Section 4
   - Add `CREATE TABLE IF NOT EXISTS plays (...)` with the exact schema from spec Section 4
   - Add all 7 `CREATE INDEX IF NOT EXISTS` statements
   - Add `conn.execute("PRAGMA journal_mode=WAL")` and `conn.commit()`
   - **Verify:** restart yt-dj-web.service; `sqlite3 music/library.db ".schema"` shows both tables and all indexes

2. - [ ] Write `src/play_history.py`:
   - `DB_PATH = Path(__file__).parent.parent / "music" / "library.db"`
   - `track_stats(file_path: str) -> dict | None` — joins `library_tracks` + `plays` for a single track
   - `tracks_played_since(iso_ts: str) -> list[dict]` — plays after timestamp
   - `tracks_never_played() -> list[dict]` — `library_tracks` rows with no matching `plays` row
   - `tracks_by_days_since_play(max_days: int) -> list[dict]` — active tracks whose last play was ≥ max_days ago (includes never-played)
   - `recent_plays(limit: int = 100) -> list[dict]` — most recent `plays` rows
   - **Verify:** `python3 -c "from src.play_history import recent_plays; print(recent_plays())"` returns `[]`

3. - [ ] Add 4 endpoints to `src/web/app.py` (import `play_history` at top):
   - `GET /api/play-history/track` — query param `file_path: str`, returns `track_stats()` or 404
   - `GET /api/play-history/recent` — query param `limit: int = 100`, returns `recent_plays()`
   - `GET /api/play-history/never-played` — returns `tracks_never_played()`
   - `GET /api/play-history/freshness` — query param `max_days: int = 7`, returns `tracks_by_days_since_play()`
   - **Verify:** `curl http://localhost:9093/api/play-history/recent` → `[]` (HTTP 200)

4. - [ ] Extend `src/analyze_library.py`:
   - Add `DB_PATH = PROJECT / "music" / "library.db"` constant
   - Add `upsert_library_tracks(results: list[dict]) -> None`:
     - Open `library.db` in WAL mode
     - `INSERT INTO library_tracks (...) ON CONFLICT(file_path) DO UPDATE SET ...` for each result (leaves `first_seen_at` alone, clears `removed_at` on re-add)
     - Soft-delete rows whose `file_path` is no longer in the scan set (`removed_at = now`)
     - Commit + close
   - Call `upsert_library_tracks(results)` at the end of `main()` after the JSON write
   - **Verify:** `python3 src/analyze_library.py` then `sqlite3 music/library.db "SELECT COUNT(*) FROM library_tracks WHERE removed_at IS NULL"` equals `ls music/clips/*.mp3 | wc -l`

5. - [ ] Write `src/log_play.py`:
   ```python
   #!/usr/bin/env python3
   # Usage: python3 log_play.py <file_path> <title> <artist>
   # Inserts one row into plays. Exits 0 always — never blocks the stream.
   ```
   - Parse `sys.argv[1:4]` for file_path, title, artist (default empty string if missing)
   - Derive `filename = Path(file_path).name`
   - Query `library_tracks` for `id` by `file_path` (may be NULL if not yet indexed)
   - INSERT into `plays` with `played_at = datetime.now(UTC).isoformat(timespec="seconds")`
   - Wrap everything in `try/except Exception: sys.exit(0)`
   - **Verify:** `python3 src/log_play.py /home/agent/projects/yt_dj/music/clips/test.mp3 "Test" ""` then `sqlite3 music/library.db "SELECT * FROM plays"` shows one row

6. - [ ] Update `agent-stack/liquidsoap/radio.liq` — add AFTER the `map_metadata` block, BEFORE `output.icecast`:
   ```liquidsoap
   def log_play(meta) =
     filename = default("", list.assoc("filename", meta))
     title    = default("", list.assoc("title",    meta))
     artist   = default("", list.assoc("artist",   meta))
     thread.run(fun() ->
       ignore(system("/usr/bin/python3 /home/agent/projects/yt_dj/src/log_play.py " ^
                     process.quote(filename) ^ " " ^
                     process.quote(title)    ^ " " ^
                     process.quote(artist)))
     )
   end
   radio = source.on_track(synchronous=false, radio, log_play)
   ```

7. - [ ] Update `agent-stack/docker-compose.yml` — add to the `liquidsoap` service `volumes` list:
   ```yaml
   - /home/agent/projects/yt_dj/music/library.db:/home/agent/projects/yt_dj/music/library.db:rw
   - /home/agent/projects/yt_dj/src/log_play.py:/home/agent/projects/yt_dj/src/log_play.py:ro
   ```
   Then: `cd /home/agent/agent-stack && docker-compose restart liquidsoap`
   - **Verify:** `docker exec liquidsoap python3 /home/agent/projects/yt_dj/src/log_play.py /home/agent/projects/yt_dj/music/clips/$(ls /home/agent/projects/yt_dj/music/clips/*.mp3 | head -1 | xargs basename) "TestTitle" "TestArtist"` inserts a row

8. - [ ] Regression check: `curl http://localhost:9093/api/tracks` (or any existing endpoint) returns the same response as before.

## Acceptance Criteria

- [ ] `music/library.db` contains both `library_tracks` and `plays` tables matching the schema in spec Section 4
- [ ] `PRAGMA journal_mode` on `library.db` returns `wal`
- [ ] After running `python3 src/analyze_library.py`, `SELECT COUNT(*) FROM library_tracks WHERE removed_at IS NULL` equals `ls music/clips/*.mp3 | wc -l`
- [ ] `GET /api/play-history/recent` returns HTTP 200 and a JSON array (empty is valid at t=0)
- [ ] `GET /api/play-history/never-played` returns HTTP 200 and a JSON array
- [ ] `GET /api/play-history/freshness?max_days=7` returns HTTP 200 and a JSON array
- [ ] `GET /api/play-history/track?file_path=<any_path_in_library_tracks>` returns HTTP 200 and a JSON object with `play_count`, `last_played_at`, `first_seen_at`
- [ ] After the next Liquidsoap track change, a row appears in `plays` within 10 seconds of the change
- [ ] Stream audio continues playing without interruption if `src/log_play.py` exits with error or is missing
- [ ] No existing endpoint in `src/web/app.py` returns a different response after this slug ships (regression check)

## Contract Link

`docs/cortex/contracts/play-history/contract-001.md`
