# Phase 2: Writer Hook and Container Wire-up - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning (depends on Phase 1 completion)
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Write `src/log_play.py` (the argv-based SQLite writer), add the Liquidsoap `source.on_track` hook to `radio.liq`, and update `docker-compose.yml` with the `library.db` (rw) and `log_play.py` (ro) volume mounts for the liquidsoap container. After this phase, Liquidsoap automatically logs every track change to the `plays` table — the full data foundation is live end-to-end.

**Prerequisite:** Phase 1 must be complete — `library_tracks` and `plays` tables must exist before the writer runs its FK lookup.

</domain>

<decisions>
## Implementation Decisions

### `src/log_play.py` interface and behavior (from research F3)
```
Usage: python3 src/log_play.py <file_path> <title> <artist>
Exit: always 0, regardless of outcome
```
- Parse `sys.argv[1]` = file_path, `sys.argv[2]` = title (default `""`), `sys.argv[3]` = artist (default `""`)
- Derive `filename = Path(file_path).name`
- Open `library.db` in WAL mode: `sqlite3.connect(str(DB_PATH)); conn.execute("PRAGMA journal_mode=WAL")`
- Resolve `library_track_id`: `SELECT id FROM library_tracks WHERE file_path = ?` → `None` if not found
- `INSERT INTO plays (library_track_id, file_path, filename, played_at, source) VALUES (?, ?, ?, ?, 'liquidsoap')`
- `played_at = datetime.now(timezone.utc).isoformat(timespec="seconds")`
- Commit, close
- Wrap **everything** in `try/except Exception: sys.exit(0)` — even the argv parsing. The stream must never see a non-zero exit for any reason.

### Liquidsoap hook pattern (from research F3)
Exact pattern to add to `radio.liq` after the `map_metadata` block and before `output.icecast`:

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

Key points:
- `synchronous=false` ensures the handler never blocks playback
- `thread.run` + `ignore(system(...))` is fire-and-forget; exit code discarded
- `process.quote()` safely escapes all three arguments
- `filename` metadata contains the absolute path from the bind-mount (same path `analyze_library.py` uses as `file_path`)

### Volume mounts for liquidsoap container (from research F3)
Add to `agent-stack/docker-compose.yml` under the `liquidsoap` service `volumes` list:

```yaml
- /home/agent/projects/yt_dj/music/library.db:/home/agent/projects/yt_dj/music/library.db:rw
- /home/agent/projects/yt_dj/src/log_play.py:/home/agent/projects/yt_dj/src/log_play.py:ro
```

The `library.db` mount must be `:rw` (writer needs write access). The `log_play.py` mount is `:ro` (read-only is sufficient and safer).

**After editing `docker-compose.yml`:** `cd /home/agent/agent-stack && docker-compose restart liquidsoap`

**Also restart yt-dj-web.service:** `sudo systemctl restart yt-dj-web.service` (so web app picks up any schema changes from Phase 1 if not already restarted)

### Verification sequence
1. `docker exec liquidsoap python3 /home/agent/projects/yt_dj/src/log_play.py /home/agent/projects/yt_dj/music/clips/<any_mp3> "TestTitle" "TestArtist"` — inserts a test row
2. `sqlite3 /home/agent/projects/yt_dj/music/library.db "SELECT * FROM plays ORDER BY id DESC LIMIT 1"` — verify the row
3. Wait for next natural track change (or skip tracks via Liquidsoap if needed) — verify a new row appears within 10 seconds
4. Confirm stream did not pause or interrupt during the test

### Error handling note
If `library.db` doesn't exist at the path inside the container, the writer will fail silently (try/except → sys.exit(0)). This is intentional. The symptom would be an empty `plays` table. Verify the mount with `docker exec liquidsoap ls -la /home/agent/projects/yt_dj/music/library.db` if plays are not appearing.

### Claude's Discretion
- Whether to add a `# log_play.py` comment at the insertion point in `radio.liq` to mark the hook section
- Exact placement of the `log_play` definition in `radio.liq` (after `map_metadata` and before `output.icecast` is specified; exact line number is Claude's judgment)

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/play-history/spec.md (Section 7 sequencing step 6)
- docs/cortex/specs/play-history/gsd-handoff.md (Tasks 6 and 7)
- docs/cortex/contracts/play-history/contract-001.md (Done Criteria 8 and 9)
- docs/cortex/research/play-history/concept-20260412T035404Z.md (Finding F3 — Liquidsoap hook pattern)

</canonical_refs>

<specifics>
## Specific Ideas

- The existing `radio.liq` has 5 blocks: settings, playlist, fallback, crossfade, map_metadata, output.icecast. The `log_play` handler goes between `map_metadata` and `output.icecast` — it needs the metadata to be fully resolved before it can log the `title`.
- The `filename` field in Liquidsoap metadata is the absolute path (set by the playlist source). This is the same path `analyze_library.py` uses. No normalization needed.
- The liquidsoap container's `music/clips` mount is already `:ro` — that's fine; `log_play.py` doesn't need to write there. Only `library.db` needs `:rw`.
- After `docker-compose restart liquidsoap`, Liquidsoap will re-read `radio.liq` from scratch. The first track change after restart will trigger the hook.

</specifics>

<deferred>
## Deferred Ideas

- Making the writer robust against `library.db` file rotation or backup — not needed; single-file setup
- Buffering/retry for dropped play events — out of scope; drop is the accepted failure mode
- A separate ingest endpoint (`POST /api/play-history/ingest`) for non-Liquidsoap writers — out of scope; shell-out pattern is sufficient

</deferred>

---

*Phase: 02-play-history*
*Context gathered: 2026-04-12 via /cortex-bridge*
