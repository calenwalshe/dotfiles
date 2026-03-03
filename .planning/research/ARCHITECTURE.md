# Architecture Research

**Domain:** URL screenshot capture + perception classification system
**Researched:** 2026-03-03
**Confidence:** HIGH (based on direct inspection of existing codebase)

---

## Standard Architecture for Screenshot + Perception Systems

Screenshot-and-classify systems decompose into four layers: capture, classify, store, and alert. Each has a clear boundary. The openclaw-fresh / master_harness system already implements all four layers for web_search_resilience — this milestone reuses those layers and adds a user-facing request path.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                             │
│  Telegram DM / Browser UI → openclaw-fresh (main agent)                 │
│  "/screenshot https://example.com" or natural language                  │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ user request (URL + intent)
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    L1: SCREENSHOT ACTOR (openclaw-fresh)                │
│                                                                         │
│  ┌─────────────┐   ┌──────────────────┐   ┌─────────────────────────┐  │
│  │ URL parser  │   │ browser-service  │   │  cf-bypass-worker       │  │
│  │ + validator │──▶│ /sessions        │──▶│  (fallback if CF hit)   │  │
│  └─────────────┘   │ /navigate        │   └─────────────────────────┘  │
│                    │ /screenshot      │                                 │
│                    └──────────┬───────┘                                 │
│                               │ screenshot_b64 + blocker info           │
└───────────────────────────────┼─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    L2: PERCEPTION HARNESS (openclaw-scheduler)          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ _classify_blocker()  ──▶  PASS_CONTENT / BLOCKED_CHALLENGE /   │    │
│  │                            BLANK_PAGE / DEGRADED_CONTENT        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ url_screenshot suite (new) — extends web_search_resilience      │    │
│  │  - STABLE_DOMAIN_HINTS / site_test_catalog                      │    │
│  │  - failed user URLs → auto-registered in site_test_catalog      │    │
│  │  - scheduled runs via @suite decorator                          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└───────────────────┬───────────────────────────────────────────────┬─────┘
                    │                                               │
                    ▼                                               ▼
┌───────────────────────────────────┐   ┌───────────────────────────────┐
│   STORAGE LAYER (PostgreSQL)      │   │   ALERT LAYER (Telegram)      │
│                                   │   │                               │
│  harness.harness_results          │   │  Reporter.report()            │
│  harness.harness_runs             │   │  → send_message() (notifier)  │
│  harness.site_test_catalog        │   │  → ADMIN_TELEGRAM_ID          │
│  harness.site_test_scores         │   │                               │
│  harness-artifacts/ (PNG files)   │   │  Level: critical / warning /  │
│                                   │   │         digest                │
└───────────────────────────────────┘   └───────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Where It Lives | Communicates With |
|-----------|----------------|----------------|-------------------|
| openclaw-fresh (main agent) | Parse user intent, dispatch screenshot request, format response + image back to user | `openclaw-fresh` container | browser-service (HTTP), Telegram (outbound), L2 harness (auto-registration of failures) |
| browser-service | Headless browser management via Playwright; navigate to URL, capture screenshot_b64, run blocker detection (PageDetector) | `browser-service:9150` | Playwright (chromium), cf-bypass-worker |
| PageDetector (detector.py) | JS DOM scan — detects CAPTCHA iframes, CF challenge signals, login walls, cookie consent; returns BlockerInfo | Inside browser-service | Page (Playwright sync) |
| cf-bypass-worker | Attempt to bypass Cloudflare challenges when detected | `cf-bypass-worker:9160` | browser-service (called on CF detection) |
| L2 perception harness suite | Classifies screenshot result into PASS_CONTENT / BLOCKED_CHALLENGE / BLANK_PAGE / DEGRADED_CONTENT; schedules periodic re-checks; detects new failure patterns | `openclaw-scheduler` suites/ | browser-service, Storage, Reporter |
| site_test_catalog (Storage) | Persistent registry of URLs to test; upsert from user failures; get_next_site() for schedule coverage | PostgreSQL `harness` schema | L2 harness suite |
| Storage (master_harness) | Persists run metadata, per-test results, site scores to PostgreSQL | `openclaw-scheduler` | PostgreSQL (asyncpg) |
| Reporter (master_harness) | Formats results as Telegram HTML digest; classifies alert level (critical/warning/digest); compares against previous run | `openclaw-scheduler` | notifier.send_message(), Storage |
| harness-artifacts/ | Filesystem store for screenshot PNG + page_meta.json per test run | `openclaw-scheduler` volume | Written by harness suite, readable for debugging |

---

## Data Flow

### Flow 1: User-Requested Screenshot (L1 + immediate L2 feedback)

```
User sends Telegram message: "/screenshot https://discogs.com/sell/list"
    │
    ▼
openclaw-fresh (main agent)
    │  parse URL from message
    ▼
POST browser-service:9150/sessions  {name: "screenshot-<uuid>", url: <target_url>}
    │  {ok: true, session: {...}}
    ▼
POST browser-service:9150/sessions/<name>/navigate  {url: <target_url>}
    │  Returns: {ok, url, title, screenshot_b64, elements, blocker}
    │  blocker = {blocked: bool, type: "cloudflare"|"captcha"|..., signals: [...]}
    ▼
_classify_blocker(blocker, final_url, title)
    │  Returns: classification string + challenge_detected bool
    │  PASS_CONTENT | BLOCKED_CHALLENGE | BLANK_PAGE | DEGRADED_CONTENT
    ▼  (if BLOCKED_CHALLENGE detected)
POST cf-bypass-worker:9160/bypass  {url: <target_url>, timeout: N}
    │  Retry up to 2x with increasing timeout
    ▼
[if bypass succeeds] → re-fetch screenshot
[if bypass fails]    → keep original screenshot + classification
    │
    ▼
openclaw-fresh sends to user:
    - Screenshot image (base64 → photo message)
    - Classification label: "PASS_CONTENT" / "BLOCKED_CHALLENGE (CF)" / etc.
    - Status message: "Captured. CF challenge detected, bypass attempted."
    │
    ▼
If classification != PASS_CONTENT:
    → Call L2 harness: Storage.upsert_site(site_key, base_url, notes="auto from user request")
    (URL joins the scheduled test pool for future regression tracking)
```

### Flow 2: Scheduled Harness Run (L2 autonomous)

```
openclaw-scheduler cron (e.g. every 4 hours)
    │
    ▼
HarnessRunner.run_suite(url_screenshot_suite)
    │
    ▼
Storage.get_next_site()  ← picks URL with fewest recent score records
    │  Returns {site_key, base_url, ...}
    ▼
_run_browser_perception_test(session, query=None, url=base_url, ...)
    │  Full browser navigate + classify cycle (same as L1)
    ▼
Storage.record_site_score(site_key, classification, challenge_detected, ...)
Storage.record_results(run_id, [TestResult])
    │
    ▼
Reporter.report(suite_descriptor, summary, results)
    │  _classify_alert() → "critical" if P0 tag + failure
    │                    → "warning" if P1 + 2+ consecutive failures
    │                    → "digest" otherwise
    ▼
Telegram alert to ADMIN_TELEGRAM_ID
    - If new failure class on a known URL: "New failure pattern on discogs.com — want me to investigate?"
    - If recovered: "discogs.com recovered: PASS_CONTENT"
    - Digest otherwise
```

### Flow 3: Failure Pattern Detection

```
Reporter.report() compares:
    curr_failed = {tests that failed this run}
    prev_failed = {tests that failed last run}

    new_failures = curr_failed - prev_failed  → alert with "NEW FAIL:" prefix
    recovered    = prev_failed - curr_failed  → note with "RECOVERED:" prefix

Storage.get_consecutive_failures(suite, test_name)
    → count of consecutive recent failures before a pass
    → used to escalate warning level threshold (≥2 = warning)
```

---

## Component Boundaries

### L1 vs L2 Boundary

L1 (openclaw-fresh) owns the user interaction: receives URL, drives the browser, returns the screenshot + label to the user. L1 is synchronous from the user's perspective — they wait for a response.

L2 (openclaw-scheduler / master_harness) owns regression tracking: stores results over time, detects new failure patterns, alerts the operator. L2 runs on a schedule independent of user requests.

The handoff: L1 writes to `site_test_catalog` (via Storage API or direct DB write) when a user request fails. This is the only coupling between L1 and L2.

### browser-service Boundary

browser-service is a stateless HTTP service. It does not know about classifications, harness runs, or Telegram. It provides: session lifecycle, navigation, screenshots, element scans, blocker detection. Any caller that wants to drive a browser goes through it.

Key API surface used by this milestone:
- `POST /sessions` — create session
- `POST /sessions/{name}/navigate` — navigate + screenshot + blocker scan in one call
- `DELETE /sessions/{name}` — cleanup

### master_harness Boundary

master_harness is pure test infrastructure. It does not know about specific URLs or what constitutes a "pass." Suite functions implement that logic. master_harness provides: HarnessRunner (concurrency, timeout, error handling), Storage (PostgreSQL persistence), Reporter (Telegram formatting and alerting), Registry (@suite decorator, discovery).

New suite files drop into `master_harness/suites/` and are auto-discovered at startup.

---

## Recommended Project Structure

```
agent-stack/
├── browser-service/             # No changes needed
│   └── app/
│       ├── server.py            # Existing navigate endpoint is sufficient
│       └── detector.py          # Existing BlockerInfo types are sufficient
│
├── openclaw-scheduler/
│   ├── master_harness/
│   │   └── suites/
│   │       └── url_screenshot.py   # NEW: L2 perception harness suite
│   │
│   └── jobs/
│       └── url_screenshot_job.py   # NEW: scheduler entry point (thin wrapper)
│
└── openclaw-fresh/
    └── workspace/
        └── tools/
            └── screenshot_tool.py  # NEW: L1 actor — tool callable by main agent
```

### Structure Rationale

- **url_screenshot.py (suites/):** The harness suite. Implements `_run_url_screenshot_test()` modeled on `_run_browser_perception_test()`. Registers with `@suite("url_screenshot", ...)`. Reads from `site_test_catalog`. Writes to `site_test_scores` and `harness_results`.

- **screenshot_tool.py (openclaw-fresh):** The tool the main agent calls when a user requests a screenshot. Calls `browser-service` directly via HTTP. Returns classification + base64 image. Handles CF bypass logic. If classification != PASS_CONTENT, calls `Storage.upsert_site()` to register the URL in the harness catalog.

- **No new services:** Everything reuses existing containers. L1 runs inside openclaw-fresh. L2 runs inside openclaw-scheduler. browser-service is unchanged.

---

## Architectural Patterns

### Pattern 1: Thin Actor, Fat Harness

L1 (the actor) is intentionally thin — navigate, classify, return result, optionally register failure. All the complexity (scheduling, historical comparison, alerting logic, storage) lives in L2 (the harness). This keeps L1 testable in isolation and means the harness can be extended without touching user-facing code.

**When to use:** When the same operation (browser perception) is needed both interactively (user request) and autonomously (scheduled regression), share the classification logic but keep the entry points separate.

### Pattern 2: _classify_blocker() as the Shared Contract

The existing `_classify_blocker(blocker, page_url, title) -> (classification, challenge_detected)` function is the classification contract. Both L1 and L2 must use this same function so that classifications are consistent across user requests and scheduled runs.

Do not duplicate classification logic. Extract it into a shared module (`master_harness/classification.py` or keep it in `web_search_resilience.py` and import from there).

```python
# Classification contract — both L1 and L2 use this
def _classify_blocker(blocker: dict | None, page_url: str, title: str) -> tuple[str, bool]:
    """Returns (classification_label, challenge_detected_bool)."""
    # PASS_CONTENT | BLOCKED_CHALLENGE | SOFT_BLOCK → classification
    # challenge_detected = True when Cloudflare-like signals present
```

### Pattern 3: site_test_catalog as the Shared URL Registry

The existing `site_test_catalog` table (`harness.site_test_catalog`) is the handoff point between L1 and L2. When L1 sees a failure, it `upsert_site()` into the catalog. The L2 harness reads from `get_next_site()` to find URLs to test. This avoids any direct coupling between the openclaw-fresh container and the scheduler container.

```python
# L1 handoff to L2 — write to catalog on user-request failure
await storage.upsert_site(
    site_key=f"user_request_{_host(url)}",
    base_url=url,
    category="user_requested",
    priority=10,   # Higher priority than default
    notes=f"Auto-added from user request, classification={classification}",
)
```

### Pattern 4: Artifact Directory per Test Run

The existing `_artifact_dir(run_tag, test_name, artifact_root)` pattern stores PNG screenshots and `page_meta.json` at:
```
harness-artifacts/
└── url_screenshot/
    └── <run_tag>/
        └── <test_name>/
            ├── screenshot.png
            └── page_meta.json
```

Use this pattern for all screenshot artifacts. Do not store base64 in the database — write PNG to disk and store the file path in metadata.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Creating a New Service for L1

**What people do:** Build a separate `screenshot-service` container to handle user screenshot requests.

**Why it's wrong:** openclaw-fresh already has a direct HTTP path to browser-service. Adding an intermediate service creates an extra hop, additional deployment complexity, and a new failure point. The main agent can call browser-service directly.

**Do this instead:** Implement L1 as a tool function inside openclaw-fresh that makes HTTP calls to browser-service and returns the result to the agent.

### Anti-Pattern 2: Duplicating Classification Logic

**What people do:** Write separate CF/blocker detection in L1 and a different version in L2.

**Why it's wrong:** Classifications will diverge. A URL classified as BLOCKED_CHALLENGE by L1 may be PASS_CONTENT in L2. Debugging is impossible.

**Do this instead:** Import and use `_classify_blocker()` from a single canonical location in both L1 and L2.

### Anti-Pattern 3: Storing Screenshots in PostgreSQL

**What people do:** Store screenshot PNG bytes as a BYTEA column or base64 TEXT in the database.

**Why it's wrong:** Screenshots are 50-500 KB each. The harness runs periodically against many URLs. The database will balloon rapidly, queries slow down, backups grow.

**Do this instead:** Write PNG to `harness-artifacts/` filesystem path (already mounted in openclaw-scheduler container). Store the file path in `metadata` JSONB column.

### Anti-Pattern 4: Skipping Session Cleanup

**What people do:** Create browser sessions and let them pile up (forget the DELETE call).

**Why it's wrong:** browser-service manages real Chromium processes. Leaked sessions consume memory and eventually starve the host. The existing pattern uses try/finally to always DELETE the session.

**Do this instead:** Always wrap browser session usage in try/finally:
```python
try:
    # create session, navigate, take screenshot
    ...
finally:
    await session.delete(f"{BROWSER_SERVICE_URL}/sessions/{sess_name}", ...)
```

---

## Integration Points

### With Existing openclaw-fresh

| Integration Point | How | Notes |
|-------------------|-----|-------|
| Main agent tool dispatch | Add screenshot_tool to available tools list | Agent calls it when user sends screenshot request |
| Telegram response | Use existing send_photo / send_message pipeline | Same pathway as all other agent responses |
| browser-service | Direct HTTP POST to `http://browser-service:9150` | Already on the docker network, no auth required |
| cf-bypass-worker | Direct HTTP POST to `http://cf-bypass-worker:9160/bypass` | Already called by web_search_resilience |

### With Existing master_harness

| Integration Point | How | Notes |
|-------------------|-----|-------|
| Suite registration | `@suite("url_screenshot", tier="standard", default_schedule="0 */4 * * *")` | Auto-discovered via discover_suites() |
| Storage | Use existing `Storage` instance from runner context | Tables already exist including site_test_catalog |
| Reporter | No changes needed — existing report() handles all suites | Classification label goes in TestResult.detail |
| Scheduler job | Thin job file in `jobs/` calls `HarnessRunner.run_suite()` | Same pattern as stack_harness, web_search_resilience |

### With Existing site_test_catalog

The `site_test_catalog` and `site_test_scores` tables were built for exactly this use case. They are already in the `harness` schema. The storage layer exposes `upsert_site()`, `get_next_site()`, and `record_site_score()`. No schema changes required.

---

## Build Order (Phase Dependency Graph)

```
Phase 1: L1 Screenshot Actor
    - screenshot_tool.py in openclaw-fresh
    - Direct browser-service calls
    - CF bypass logic
    - Classification + Telegram response
    ↓ (L2 depends on classification contract being stable)

Phase 2: L2 Perception Harness Suite
    - url_screenshot.py in master_harness/suites/
    - site_test_catalog integration (auto-registration from L1 failures)
    - Scheduled runs via @suite decorator
    ↓ (Alerting depends on harness suite producing results)

Phase 3: Failure Pattern Alerting
    - Reporter already handles new_failures / recovered comparison
    - Add "New failure pattern" message format for new site_key failures
    - Operator alert when failure class changes for a tracked URL
```

**Rationale for this order:**
- L1 can be tested immediately (user can request screenshots and see results)
- L1 failures populate site_test_catalog, giving L2 real URLs to test before L2 is even scheduled
- L2 alerting requires historical data (needs ≥2 runs) — build last so there's data to compare against

---

## Scalability Considerations

This is a single-operator internal system. Scale considerations are operational, not load-based.

| Concern | Current Scale | Mitigation |
|---------|--------------|------------|
| Screenshot storage growth | ~500 KB/screenshot × scheduled runs | Prune harness-artifacts/ older than 30 days in a maintenance job |
| Browser session accumulation | 1-2 concurrent sessions max | Always DELETE sessions in finally blocks; browser-service has no session limit but Chromium processes are expensive |
| site_test_catalog growth | URLs added from user requests | Deactivate URLs that pass consistently for 30+ days (set active=false) |
| Scheduled run duration | Each URL takes 5-30s | Suite timeout_s=300 handles up to ~10 URLs per run; increase if catalog grows |

---

## Sources

- Direct inspection of `/home/agent/agent-stack/browser-service/app/server.py` (HIGH)
- Direct inspection of `/home/agent/agent-stack/browser-service/app/detector.py` (HIGH)
- Direct inspection of `/home/agent/agent-stack/openclaw-scheduler/master_harness/suites/web_search_resilience.py` (HIGH)
- Direct inspection of `/home/agent/agent-stack/openclaw-scheduler/master_harness/storage.py` (HIGH)
- Direct inspection of `/home/agent/agent-stack/openclaw-scheduler/master_harness/runner.py` (HIGH)
- Direct inspection of `/home/agent/agent-stack/openclaw-scheduler/master_harness/reporter.py` (HIGH)
- Direct inspection of `/home/agent/agent-stack/openclaw-scheduler/master_harness/registry.py` (HIGH)
- PROJECT.md at `/home/agent/.planning/PROJECT.md` (HIGH)

---

*Architecture research for: URL screenshot capture + perception classification (L1 actor + L2 harness)*
*Researched: 2026-03-03*
