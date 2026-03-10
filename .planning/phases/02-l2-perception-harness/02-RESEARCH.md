# Phase 2: L2 Perception Harness - Research

**Researched:** 2026-03-10
**Domain:** master_harness suite integration, asyncpg/aiohttp, filesystem artifact management
**Confidence:** HIGH

## Summary

Phase 2 creates `l2_perception.py` — a new harness suite that iterates through all active entries in `harness.site_test_catalog`, captures and classifies each URL using the Phase 1 pipeline functions, stores PNG + JSON artifacts on the scheduler's shared filesystem, records scores to `harness.site_test_scores`, and detects classification drift run-over-run. The suite registers via `@suite()` and is auto-discovered; a single config.yaml stanza activates it on the `0 * * * *` cron.

The code infrastructure is completely proven: the `@suite` decorator, `Storage` class, `TestResult` type, `_artifact_dir()` pattern, browser/bypass HTTP calls, and config.yaml harness section all exist and are in production use by `web_search_resilience`. The new suite is a structured application of those patterns — not new infrastructure.

The key complexity is the classifier consolidation decision: `_classify_screenshot()` currently lives in `screenshot_tool.py` (openclaw-fresh container). The simplest safe approach is to copy the pure function into the L2 suite module directly — avoiding cross-container import while keeping logic identical. The two implementations diverge only if they're updated independently, which is acceptable until a future shared library is built.

**Primary recommendation:** Build `l2_perception.py` as a self-contained harness suite module; copy classifier logic from `screenshot_tool.py`; prune at run start; skip-and-continue on per-URL failures; write full-res PNG + classification.json per site per run; record to `site_test_scores` after each URL.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Run Cadence & Coverage**
- Hourly schedule (`0 * * * *`) — balances monitoring responsiveness with resource use
- Full catalog sweep every run — every active URL tested every hour
- Sequential URL processing — one at a time, no concurrency complexity; 50 URLs at ~30s each = 25min, well within the hour window
- CF bypass attempted on BLOCKED_CHALLENGE URLs — same behavior as L1; records pre-bypass and post-bypass classification for Phase 3 health metric data

**Artifact Retention**
- Harness-style artifact dirs: `{artifact_root}/l2_perception/{run_tag}/{site_key}/screenshot.png` + `classification.json`
- Run tag format: `{YYYYMMDDTHHMMSSZ}-{uuid6}` matching web_search_resilience pattern
- Pruning window: 7 days — artifacts older than 7 days auto-deleted at start of each run
- Metadata also recorded to `site_test_scores` table via Storage for queryable history beyond the pruning window

**Staging-to-Active Promotion**
- No auto-promotion — URLs stay in staging (active=false) until operator promotes them
- Phase 3 delivers the Telegram promotion UX; this phase just respects the active flag via `list_sites(active_only=True)`
- Promotion logic is a simple `upsert_site(site_key, active=True)` — Phase 3 wraps it in Telegram command

**Failure Tracking**
- Each run records classification + confidence + challenge_detected to `site_test_scores`
- Classification drift detection: compare current classification against previous run's classification for the same URL
- Flag when a URL's classification changes (e.g., PASS_CONTENT → BLOCKED_CHALLENGE) — store drift event in TestResult metadata
- `get_consecutive_failures()` already in Storage — used to track how many consecutive non-PASS results per URL
- Phase 3 consumes this data for alerting; this phase just records it faithfully

**Classifier Consolidation**
- Extract shared classification logic from `screenshot_tool.py` into a module importable by both L1 (openclaw-fresh) and L2 (openclaw-scheduler)
- Since L1 runs in openclaw-fresh container and L2 runs in openclaw-scheduler container, the shared module lives in openclaw-scheduler and screenshot_tool.py is updated to match (or duplicated classification is acceptable if cross-container import is impractical — Claude's discretion on approach)

### Claude's Discretion
- Exact pruning implementation (delete at run start vs separate cleanup job)
- Whether to save full-page PNG or resized JPEG for harness artifacts
- Error handling for individual URL failures within a run (skip and continue vs abort run)
- TestResult metadata structure beyond required fields
- Whether to use aiohttp session pooling or per-URL sessions
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFR-03 | Screenshot artifacts stored with metadata (URL, timestamp, classification, confidence) | Covered by `record_site_score()` + filesystem PNG + `classification.json` per site; `harness_results` JSONB metadata field holds all required fields |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | >=3.9,<4.0 | HTTP to browser-service:9150 and cf-bypass-worker:9160 | Already in scheduler requirements.txt; used by all existing suites |
| asyncpg | >=0.29 | PostgreSQL (Storage class) | Already in requirements.txt; wired by scheduler.py into db_pool |
| APScheduler | >=3.10,<4.0 | Cron scheduling | Already running; `scheduler_integration.py` registers @suite cron jobs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | Artifact directory creation and file writes | All artifact writes |
| shutil | stdlib | Recursive directory deletion for pruning | Pruning runs older than 7 days |
| asyncio.Semaphore | stdlib | CF bypass worker concurrency guard | When attempting bypass on BLOCKED_CHALLENGE URLs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Full-res PNG (raw decode) | Resized JPEG (Pillow) | PNG is lossless, no Pillow dependency needed in scheduler container; JPEG saves ~70% space but requires adding Pillow to requirements.txt |
| Skip-and-continue on failure | Abort run | Skip keeps partial runs valuable; abort wastes work already done on earlier URLs |
| Per-URL aiohttp.ClientSession | Shared session | Per-URL matches existing `capture_screenshot()` pattern exactly; shared pool adds complexity for marginal gain |

**Installation:** No new dependencies required. All libraries already present in scheduler container.

---

## Architecture Patterns

### Recommended Project Structure
```
openclaw-scheduler/
  master_harness/
    suites/
      l2_perception.py      # New suite file — auto-discovered
  config.yaml               # Add l2_perception section under harness.suites
```

### Pattern 1: @suite decorator registration
**What:** Decorate an `async def run(params: dict) -> list[TestResult]` function with `@suite(...)`. The suite is auto-discovered by `discover_suites("master_harness.suites")` at scheduler startup.
**When to use:** All harness suites — this is the only registration mechanism.
**Example:**
```python
# Source: /home/agent/agent-stack/openclaw-scheduler/master_harness/registry.py
from master_harness.registry import suite
from master_harness.types import TestResult

@suite(
    "l2_perception",
    tier="standard",
    default_schedule="0 * * * *",
    timeout_s=2400,          # 40 min ceiling for 50 URLs
    tags={"perception", "catalog", "l2"},
)
async def run(params: dict) -> list[TestResult]:
    ...
```

### Pattern 2: _artifact_dir() filesystem layout
**What:** `Path(artifact_root) / SUITE / run_tag / site_key` — created with `mkdir(parents=True, exist_ok=True)`.
**When to use:** Every site within a run gets its own directory.
**Example:**
```python
# Source: /home/agent/agent-stack/openclaw-scheduler/master_harness/suites/web_search_resilience.py:112
def _artifact_dir(run_tag: str, site_key: str, artifact_root: str) -> Path:
    p = Path(artifact_root) / SUITE / run_tag / site_key
    p.mkdir(parents=True, exist_ok=True)
    return p
```

### Pattern 3: run_tag generation
**What:** `time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:6]`
**When to use:** Once per `run()` invocation, before URL loop.
**Example:**
```python
# Source: web_search_resilience.py:1725
run_tag = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:6]
```

### Pattern 4: record_site_score() after each URL
**What:** Insert per-URL observation into `harness.site_test_scores` immediately after capture/classify. Storage pool is passed via params dict.
**When to use:** After processing each URL — not batched at end of run (so partial runs have data).
**Example:**
```python
# Source: /home/agent/agent-stack/openclaw-scheduler/master_harness/storage.py:433
await storage.record_site_score(
    run_id=run_id,
    suite=SUITE,
    site_key=site["site_key"],
    passed=(cls == "PASS_CONTENT"),
    score=conf,
    classification=cls,
    challenge_detected=(cls == "BLOCKED_CHALLENGE"),
    nav_latency_ms=nav.get("latency_ms", 0),
    content_confidence=conf,
    metadata={
        "pre_bypass_class": pre_cls,
        "post_bypass_class": cls,
        "drift": drift_event,
        "artifact_path": str(case_dir),
    },
)
```

### Pattern 5: Artifact writes
**What:** PNG written as raw bytes from base64-decoded screenshot_b64. `classification.json` written as JSON file. Both in the case_dir for the site.
**When to use:** After classification, before recording to DB.
**Example:**
```python
# Source: web_search_resilience.py:892-923
import base64, json
png_bytes = base64.b64decode(shot_b64.encode("ascii"))
(case_dir / "screenshot.png").write_bytes(png_bytes)
(case_dir / "classification.json").write_text(
    json.dumps({
        "url": site["base_url"],
        "site_key": site["site_key"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "classification": cls,
        "confidence": conf,
        "challenge_detected": challenge_detected,
        "pre_bypass_class": pre_bypass_cls,
        "bypassed": bypassed,
    }, indent=2)
)
```

### Pattern 6: 7-day pruning at run start
**What:** Walk `{artifact_root}/l2_perception/` at the top of `run()`. Delete subdirs whose run_tag timestamps are older than 7 days.
**When to use:** First thing in `run()`, before acquiring any sites.
**Example:**
```python
import shutil, time
from datetime import datetime, timezone, timedelta

def _prune_artifacts(artifact_root: str, suite: str, max_age_days: int = 7) -> None:
    base = Path(artifact_root) / suite
    if not base.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    for run_dir in base.iterdir():
        # run_tag format: 20260310T120000Z-abc123
        try:
            ts_part = run_dir.name[:16]          # "20260310T120000Z"
            run_dt = datetime.strptime(ts_part, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            if run_dt < cutoff:
                shutil.rmtree(run_dir, ignore_errors=True)
        except (ValueError, OSError):
            continue
```

### Pattern 7: Classification drift detection
**What:** After recording the current score, query `site_test_scores` for the most recent previous row for this site_key to compare classifications.
**When to use:** After every per-URL classification.
**Example:**
```python
# Query previous classification from site_test_scores
prev_rows = await storage.get_site_scores(site_key=site_key, limit=1)
prev_cls = prev_rows[0]["classification"] if prev_rows else None
drift = (prev_cls is not None and prev_cls != cls)
drift_event = {"prev": prev_cls, "curr": cls} if drift else None
```

### Pattern 8: Storage passed via params
**What:** The harness runner calls `suite.func(params)`. The suite can receive the Storage instance via `params["storage"]` if the caller passes it, or can create its own asyncpg connection using `DATABASE_URL` env var. Existing suites do NOT receive storage through params — they use service HTTP endpoints only. For L2, the suite needs direct DB access.
**When to use:** The suite must call `list_sites()` and `record_site_score()` — both require the Storage object.

**Critical finding:** Existing suites (web_search_resilience, discogs_search) do NOT use the Storage class directly — they call external HTTP services. L2 is the first suite that needs direct DB access. Two approaches:

- **Approach A (recommended):** Suite creates its own asyncpg connection from `DATABASE_URL` env var (same pattern as `screenshot_tool.py:59`). No runner changes needed.
- **Approach B:** Pass the storage object through params in `scheduler_integration.py`. Requires modifying the integration layer.

Approach A is simpler and self-contained.

```python
DATABASE_URL = os.environ.get(
    "HARNESS_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://litellm:litellm@postgres:5432/harness"),
)

async def _get_storage() -> tuple[Storage, asyncpg.Pool]:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    return Storage(pool), pool
```

### Pattern 9: config.yaml harness.suites entry
**What:** Add an `l2_perception` key under `harness.suites` in `/home/agent/agent-stack/openclaw-scheduler/config.yaml`.
**Example:**
```yaml
harness:
  suites:
    l2_perception:
      enabled: true
      schedule: "0 * * * *"
      params:
        artifact_root: "/var/lib/openclaw/workspace/harness-artifacts"
        timeout_s: 30
        bypass_timeout_s: 60
        prune_days: 7
```

### Anti-Patterns to Avoid
- **Module-level asyncio.Semaphore for bypass:** The `_bypass_semaphore` in `screenshot_tool.py` is module-level. In L2, the semaphore must also be module-level so it persists across URL iterations within a single run.
- **Aborting the run on a single URL failure:** One URL's network error should not kill the other 49. Always wrap per-URL logic in try/except, record a failed TestResult, and continue.
- **Writing classification.json after DB insert:** Write the file first (non-transactional artifact), then insert to DB. Artifact presence is the ground truth; DB is queryable history.
- **Importing screenshot_tool.py from the scheduler container:** The two containers have separate filesystems. The classifier function must live in the scheduler codebase.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Suite registration | Manual registry dict | `@suite()` decorator | Already wires into APScheduler via `discover_suites()` |
| Scheduled execution | Custom cron loop | APScheduler CronTrigger | Already running, handles timezone, coalescing, jitter |
| DB schema/tables | Manual `CREATE TABLE` | `Storage.ensure_tables()` | Already creates `site_test_catalog` + `site_test_scores` |
| Previous-run comparison | Custom SQL | `Storage.get_previous_run()` + `get_previous_results()` | Already implemented |
| Consecutive failure count | Custom counter | `Storage.get_consecutive_failures()` | Already implemented with proper window |
| Telegram reporting | Custom message format | `Reporter.report()` via `_ReporterAdapter` | Already wired; called automatically by runner after `run()` returns |
| Browser session lifecycle | Custom Playwright | browser-service HTTP API at port 9150 | Existing pattern; `capture_screenshot()` in screenshot_tool.py shows exact calls |

**Key insight:** Every infrastructure piece is already built and in production. L2 is purely application logic on top of a solid foundation.

---

## Common Pitfalls

### Pitfall 1: Bypass semaphore scope
**What goes wrong:** Declaring `_bypass_semaphore = asyncio.Semaphore(1)` inside `run()` creates a new semaphore per run invocation. Within a run, all URL iterations share the same call stack (sequential, not concurrent), so this works — but the intent is a module-level guard.
**Why it happens:** Copying the pattern from screenshot_tool.py without noticing the module-level placement.
**How to avoid:** Declare `_bypass_semaphore = asyncio.Semaphore(1)` at module level in `l2_perception.py`.
**Warning signs:** Bypass calls completing without the 90s wait timeout during manual testing with rapid URL iteration.

### Pitfall 2: artifact_root not mounted in scheduler container
**What goes wrong:** Writing to `/var/lib/openclaw/workspace/harness-artifacts/` fails because that path doesn't exist in the container.
**Why it happens:** New developer assumes path exists.
**How to avoid:** Confirmed via `docker inspect openclaw-scheduler` — the path `/var/lib/openclaw/workspace/harness-artifacts` IS present and writable (web_search_resilience writes there today). No volume change needed.
**Warning signs:** `FileNotFoundError` on first mkdir call if `parents=True` is omitted.

### Pitfall 3: run_tag timestamp format mismatch in pruning
**What goes wrong:** Pruning logic fails to parse run_tag timestamps, leaves old directories.
**Why it happens:** The format `%Y%m%dT%H%M%SZ` has a literal `Z` suffix which `strptime` doesn't handle as a timezone.
**How to avoid:** Parse only the first 16 chars (`20260310T120000`) with `%Y%m%dT%H%M%S`, then attach UTC manually — OR parse 17 chars but replace `Z` before parsing.
**Warning signs:** Artifacts accumulate past 7 days without deletion.

### Pitfall 4: Storage class uses its own pool (not the runner's pool)
**What goes wrong:** Creating a new asyncpg pool inside `run()` on every invocation (every hour) wastes connection slots.
**Why it happens:** Calling `asyncpg.create_pool()` inside the `run()` function body.
**How to avoid:** Create the pool once at module level (lazy-initialized on first call), or use a connection (not pool) per run via `asyncpg.connect()`. For a suite running hourly with sequential DB calls, a single `asyncpg.connect()` per run is acceptable and clean.
**Warning signs:** Postgres `max_connections` log warnings; pool size growing over time.

### Pitfall 5: screenshot_b64 absent when browser fails to navigate
**What goes wrong:** `nav.get("screenshot_b64", "")` is empty or missing — writing `b64decode("")` raises `binascii.Error`.
**Why it happens:** Browser-service returns `{"ok": false, "error": "..."}` with no screenshot field.
**How to avoid:** Always check `nav.get("ok")` before decoding. If `ok=False`, record failed TestResult and skip artifact write entirely.

### Pitfall 6: get_site_scores() returns scores from current run
**What goes wrong:** Drift detection compares current run's classification against itself (if `record_site_score()` was called before `get_site_scores()`).
**Why it happens:** Inserting to DB before querying for the previous value.
**How to avoid:** Query previous scores BEFORE inserting the current score. Or use `WHERE run_id != current_run_id` in the query. The simplest approach: call `get_site_scores(site_key, limit=1)` before calling `record_site_score()` for that URL.

---

## Code Examples

Verified patterns from official codebase inspection:

### Suite skeleton (complete)
```python
# Mirrors pattern from discogs_search.py + web_search_resilience.py
import asyncio, base64, json, logging, os, shutil, time, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import aiohttp
import asyncpg

from master_harness.registry import suite
from master_harness.types import TestResult
from master_harness.storage import Storage

log = logging.getLogger("master_harness.suites.l2_perception")

SUITE = "l2_perception"
BROWSER_SERVICE_URL = os.environ.get("BROWSER_SERVICE_URL", "http://browser-service:9150")
CF_BYPASS_URL = os.environ.get("CF_BYPASS_URL", "http://cf-bypass-worker:9160")
DATABASE_URL = os.environ.get(
    "HARNESS_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://litellm:litellm@postgres:5432/harness"),
)

_bypass_semaphore = asyncio.Semaphore(1)   # module-level guard


@suite(
    "l2_perception",
    tier="standard",
    default_schedule="0 * * * *",
    timeout_s=2400,
    tags={"perception", "catalog", "l2"},
)
async def run(params: dict) -> list[TestResult]:
    artifact_root = str(params.get("artifact_root", "/var/lib/openclaw/workspace/harness-artifacts"))
    prune_days = int(params.get("prune_days", 7))
    capture_timeout_s = int(params.get("timeout_s", 30))
    bypass_timeout_s = int(params.get("bypass_timeout_s", 60))

    _prune_artifacts(artifact_root, SUITE, prune_days)

    run_tag = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:6]
    run_id = f"{SUITE}-{run_tag}"

    conn = await asyncpg.connect(DATABASE_URL)
    storage = Storage(await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2))
    # ... fetch sites, iterate, record
```

### Browser capture call (per url)
```python
# Source: screenshot_tool.py:260 — identical HTTP call sequence for L2
sess_name = f"l2-{uuid.uuid4().hex[:12]}"
async with aiohttp.ClientSession() as session:
    async with session.post(
        f"{BROWSER_SERVICE_URL}/sessions",
        json={"name": sess_name, "url": url},
        timeout=aiohttp.ClientTimeout(total=capture_timeout_s),
    ) as r:
        create_json = await r.json()
    # ... navigate, capture, delete session
```

### config.yaml stanza to add
```yaml
# Source: /home/agent/agent-stack/openclaw-scheduler/config.yaml — under harness.suites
l2_perception:
  enabled: true
  schedule: "0 * * * *"
  params:
    artifact_root: "/var/lib/openclaw/workspace/harness-artifacts"
    timeout_s: 30
    bypass_timeout_s: 60
    prune_days: 7
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Classifier in screenshot_tool.py only | Same for now; copy to L2 suite | Phase 2 | Duplication acceptable; consolidate in Phase 3+ if needed |
| Manual suite registration | `@suite` decorator + `discover_suites()` | Already in place | Drop a file in suites/ and it's live |

**Deprecated/outdated:**
- None applicable — framework is current.

---

## Open Questions

1. **asyncpg pool vs single connection for suite DB access**
   - What we know: The suite runs hourly. It makes sequential DB calls (list_sites, then one record_site_score per URL, then get_site_scores for drift).
   - What's unclear: Whether creating a pool per suite invocation causes observable connection pressure on Postgres.
   - Recommendation: Use a single `asyncpg.connect()` per run (not a pool). Simpler, no connection leak risk, adequate for sequential workload. Close in `finally`.

2. **PNG vs JPEG for harness artifacts**
   - What we know: `web_search_resilience` writes raw PNG bytes directly from base64 decode (`screenshot_b64`). `screenshot_tool.py` uses Pillow to resize and save as JPEG. Pillow is NOT in scheduler's `requirements.txt`.
   - What's unclear: Whether screenshot sizes matter for the harness filesystem (vs Telegram delivery where size matters).
   - Recommendation: Write raw PNG (no Pillow dependency). Add a TODO comment for future resize if storage grows. Harness artifacts are not Telegram-delivered.

3. **Drift detection data source**
   - What we know: `get_site_scores(site_key, limit=1)` returns the most recent row overall — but if L2 also writes a row for this run before querying, it returns the current run's row.
   - What's unclear: Nothing — this is a clear ordering requirement.
   - Recommendation: Query previous classification BEFORE inserting current. Store `prev_classification` in a local variable before the DB write.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (stdlib) |
| Config file | none — tests run with `python -m unittest discover` |
| Quick run command | `python -m unittest discover -s master_harness/suites -p "test_*.py" -v` |
| Full suite command | `python -m unittest discover -s . -p "test_*.py" -v` |

*(Run from `/home/agent/agent-stack/openclaw-scheduler/`)*

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-03 | Classification stored with URL, timestamp, classification, confidence | unit | `python -m unittest master_harness.suites.test_l2_perception -v` | Wave 0 |
| INFR-03 | Artifact files (PNG + classification.json) written per site per run | unit | same | Wave 0 |
| INFR-03 | Pruning removes dirs older than 7 days | unit | same | Wave 0 |
| INFR-03 | Drift detection flags classification change | unit | same | Wave 0 |
| INFR-03 | Per-URL failure skips to next URL (no run abort) | unit | same | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m unittest master_harness.suites.test_l2_perception -v` (from `/home/agent/agent-stack/openclaw-scheduler/`)
- **Per wave merge:** `python -m unittest discover -s . -p "test_*.py" -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `master_harness/suites/test_l2_perception.py` — unit tests for: `_prune_artifacts()`, `_classify_screenshot()` (copied logic), `_artifact_dir()`, drift detection logic, per-URL error handling
- [ ] No framework install needed — unittest is stdlib

---

## Sources

### Primary (HIGH confidence)
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/registry.py` — suite decorator API, SuiteDescriptor fields
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/storage.py` — full Storage API: `list_sites()`, `record_site_score()`, `get_site_scores()`, `get_consecutive_failures()`, DDL for all tables
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/types.py` — TestResult, RunSummary
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/runner.py` — run lifecycle, params passing
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/scheduler_integration.py` — how suites are wired to APScheduler
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/suites/web_search_resilience.py` — `_artifact_dir()`, run_tag format, PNG write pattern, classification.json write pattern
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/suites/discogs_search.py` — minimal suite skeleton reference
- `/home/agent/agent-stack/openclaw-scheduler/config.yaml` — live config showing harness.suites format and artifact_root value
- `/home/agent/agent-stack/openclaw-scheduler/scheduler.py` — DB pool creation, env var names
- `/home/agent/projects/openclaw-fresh/workspace/tools/screenshot_tool.py` — `_classify_screenshot()`, `capture_screenshot()`, `attempt_bypass()` — functions to port/copy into L2
- `docker inspect openclaw-scheduler` — confirmed `/var/lib/openclaw/workspace/harness-artifacts` is writable inside the container

### Secondary (MEDIUM confidence)
- `.planning/phases/02-l2-perception-harness/02-CONTEXT.md` — locked decisions from discuss-phase
- `.planning/REQUIREMENTS.md` — INFR-03 requirement text

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified in requirements.txt and container
- Architecture: HIGH — all patterns directly observed in production suite code
- Pitfalls: HIGH — discovered by reading actual code paths and confirmed with container inspection
- Validation: HIGH — unittest already used for screenshot_tool.py tests

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable codebase, no external dependencies to track)
