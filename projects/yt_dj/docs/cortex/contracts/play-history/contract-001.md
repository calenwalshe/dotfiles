---
id: play-history-001
slug: play-history
phase: execute
status: pending
timestamp: 2026-04-12T04:00:00Z
---

# Contract: play-history-001

## Objective

Build the play-history data foundation layer — two new SQLite tables in `music/library.db`, a fire-and-forget Liquidsoap play-event writer, a library-track ingest extension to `analyze_library.py`, a stdlib-only Python read module, and four FastAPI read endpoints — so that every track change on the live radio stream is durably logged and queryable by future slugs (first consumer: track-freshness rotation logic).

## Deliverables

| File | Status | Change |
|---|---|---|
| `src/web/app.py` | existing | Extend `get_db()` with schema + WAL; add 4 GET endpoints |
| `src/play_history.py` | NEW | 5 query functions, stdlib-only, ~80 lines |
| `src/log_play.py` | NEW | Argv-based writer, silent-fail, ~25 lines |
| `src/analyze_library.py` | existing | `upsert_library_tracks()` + call from `main()`, ~25 lines |
| `agent-stack/liquidsoap/radio.liq` | existing | `log_play` handler + `source.on_track` wire-up |
| `agent-stack/docker-compose.yml` | existing | 2 new volume mounts for liquidsoap service |

## Scope

### In Scope
- `library_tracks` and `plays` tables + WAL mode migration in `music/library.db`
- `src/log_play.py` writer script
- `source.on_track` hook in `radio.liq`
- `library.db` + `log_play.py` mounts in `docker-compose.yml`
- `upsert_library_tracks()` in `analyze_library.py`
- `src/play_history.py` read module
- 4 FastAPI GET endpoints in `src/web/app.py`

### Out of Scope
- Track-freshness rotation logic
- Any UI or dashboard
- Changes to existing `tracks` table
- Historical backfill
- `dj_mixer.py` changes
- `config/track_metadata.json` changes

## Write Roots

The executing agent may ONLY write to these paths:

- `src/web/app.py`
- `src/play_history.py` (new file)
- `src/log_play.py` (new file)
- `src/analyze_library.py`
- `agent-stack/liquidsoap/radio.liq`
- `agent-stack/docker-compose.yml`

All other paths are read-only for this contract.

## Done Criteria

- [ ] `music/library.db` contains both `library_tracks` and `plays` tables matching the schema in `docs/cortex/specs/play-history/spec.md` Section 4
- [ ] `PRAGMA journal_mode` on `library.db` returns `wal`
- [ ] After running `python3 src/analyze_library.py`, `SELECT COUNT(*) FROM library_tracks WHERE removed_at IS NULL` equals `ls music/clips/*.mp3 | wc -l`
- [ ] `GET /api/play-history/recent` returns HTTP 200 and a JSON array
- [ ] `GET /api/play-history/never-played` returns HTTP 200 and a JSON array
- [ ] `GET /api/play-history/freshness?max_days=7` returns HTTP 200 and a JSON array
- [ ] `GET /api/play-history/track?file_path=<any_path_in_library_tracks>` returns HTTP 200 and a JSON object with `play_count`, `last_played_at`, `first_seen_at`
- [ ] After the next Liquidsoap track change, a row appears in `plays` within 10 seconds of the change
- [ ] Stream audio continues playing without interruption if `src/log_play.py` exits with error or is missing
- [ ] No existing endpoint in `src/web/app.py` returns a different response after this slug ships

## Validators

```bash
# 1. Schema check
sqlite3 /home/agent/projects/yt_dj/music/library.db ".schema library_tracks"
sqlite3 /home/agent/projects/yt_dj/music/library.db ".schema plays"

# 2. WAL mode
sqlite3 /home/agent/projects/yt_dj/music/library.db "PRAGMA journal_mode"
# Expected: wal

# 3. Library tracks populated
sqlite3 /home/agent/projects/yt_dj/music/library.db "SELECT COUNT(*) FROM library_tracks WHERE removed_at IS NULL"
ls /home/agent/projects/yt_dj/music/clips/*.mp3 | wc -l
# Numbers must match

# 4. API endpoints
curl -s http://localhost:9093/api/play-history/recent | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if isinstance(d, list) else 'FAIL')"
curl -s http://localhost:9093/api/play-history/never-played | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if isinstance(d, list) else 'FAIL')"
curl -s "http://localhost:9093/api/play-history/freshness?max_days=7" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if isinstance(d, list) else 'FAIL')"

# 5. Writer test (direct invocation)
python3 /home/agent/projects/yt_dj/src/log_play.py /home/agent/projects/yt_dj/music/clips/$(ls /home/agent/projects/yt_dj/music/clips/*.mp3 | head -1 | xargs basename) "TestTitle" "TestArtist"
sqlite3 /home/agent/projects/yt_dj/music/library.db "SELECT * FROM plays ORDER BY id DESC LIMIT 1"
# Expected: one row with filename, played_at, source='liquidsoap'

# 6. Play-history/track endpoint
FIRST_TRACK=$(sqlite3 /home/agent/projects/yt_dj/music/library.db "SELECT file_path FROM library_tracks LIMIT 1")
curl -s "http://localhost:9093/api/play-history/track?file_path=${FIRST_TRACK}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'play_count' in d else 'FAIL')"

# 7. Liquidsoap container writer test
docker exec liquidsoap python3 /home/agent/projects/yt_dj/src/log_play.py \
  /home/agent/projects/yt_dj/music/clips/$(ls /home/agent/projects/yt_dj/music/clips/*.mp3 | head -1 | xargs basename) \
  "ContainerTest" "TestArtist"
sqlite3 /home/agent/projects/yt_dj/music/library.db "SELECT COUNT(*) FROM plays"
# Expected: count increased

# 8. Regression check
curl -s http://localhost:9093/api/tracks | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if isinstance(d, list) else 'FAIL')"
```

## Eval Plan

`docs/cortex/evals/play-history/eval-plan.md` (pending — no automated eval suite for DB/infra work; validators above serve as the acceptance test suite)

## Repair Budget

- `max_repair_contracts: 3`
- `cooldown_between_repairs: 1`

## Failed Approaches

(none — initial contract)

## Why Previous Approach Failed

N/A — initial contract

## Approvals

- [ ] Contract approved for execution
- [ ] Evals approved

## Rollback Hints

If this contract needs to be rolled back:
1. Drop the new tables: `sqlite3 music/library.db "DROP TABLE IF EXISTS plays; DROP TABLE IF EXISTS library_tracks;"`
2. Optionally revert WAL mode: `sqlite3 music/library.db "PRAGMA journal_mode=DELETE;"` (safe to leave as WAL)
3. Delete `src/log_play.py` and `src/play_history.py`
4. Revert changes to `src/web/app.py`, `src/analyze_library.py`, `agent-stack/liquidsoap/radio.liq`, `agent-stack/docker-compose.yml` via `git checkout -- <file>`
5. `cd /home/agent/agent-stack && docker-compose restart liquidsoap`
6. Restart yt-dj-web.service: `sudo systemctl restart yt-dj-web.service`
