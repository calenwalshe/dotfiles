# Phase 2: L2 Perception Harness - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Scheduled harness suite that autonomously monitors every active URL in site_test_catalog, captures and classifies screenshots using the Phase 1 pipeline, stores artifacts (PNG + metadata) per run, and integrates with the existing master_harness framework (registry, runner, storage, reporter). Alerting and operator workflow are Phase 3 — this phase delivers the data collection engine.

</domain>

<decisions>
## Implementation Decisions

### Run Cadence & Coverage
- Hourly schedule (`0 * * * *`) — balances monitoring responsiveness with resource use
- Full catalog sweep every run — every active URL tested every hour
- Sequential URL processing — one at a time, no concurrency complexity; 50 URLs at ~30s each = 25min, well within the hour window
- CF bypass attempted on BLOCKED_CHALLENGE URLs — same behavior as L1; records pre-bypass and post-bypass classification for Phase 3 health metric data

### Artifact Retention
- Harness-style artifact dirs: `{artifact_root}/l2_perception/{run_tag}/{site_key}/screenshot.png` + `classification.json`
- Run tag format: `{YYYYMMDDTHHMMSSZ}-{uuid6}` matching web_search_resilience pattern
- Pruning window: 7 days — artifacts older than 7 days auto-deleted at start of each run
- Metadata also recorded to `site_test_scores` table via Storage for queryable history beyond the pruning window

### Staging-to-Active Promotion
- No auto-promotion — URLs stay in staging (active=false) until operator promotes them
- Phase 3 delivers the Telegram promotion UX; this phase just respects the active flag via `list_sites(active_only=True)`
- Promotion logic is a simple `upsert_site(site_key, active=True)` — Phase 3 wraps it in Telegram command

### Failure Tracking
- Each run records classification + confidence + challenge_detected to `site_test_scores`
- Classification drift detection: compare current classification against previous run's classification for the same URL
- Flag when a URL's classification changes (e.g., PASS_CONTENT → BLOCKED_CHALLENGE) — store drift event in TestResult metadata
- `get_consecutive_failures()` already in Storage — used to track how many consecutive non-PASS results per URL
- Phase 3 consumes this data for alerting; this phase just records it faithfully

### Classifier Consolidation
- Extract shared classification logic from `screenshot_tool.py` into a module importable by both L1 (openclaw-fresh) and L2 (openclaw-scheduler)
- Since L1 runs in openclaw-fresh container and L2 runs in openclaw-scheduler container, the shared module lives in openclaw-scheduler and screenshot_tool.py is updated to match (or duplicated classification is acceptable if cross-container import is impractical — Claude's discretion on approach)

### Claude's Discretion
- Exact pruning implementation (delete at run start vs separate cleanup job)
- Whether to save full-page PNG or resized JPEG for harness artifacts
- Error handling for individual URL failures within a run (skip and continue vs abort run)
- TestResult metadata structure beyond required fields
- Whether to use aiohttp session pooling or per-URL sessions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `screenshot_tool.py` — `capture_screenshot()`, `_classify_screenshot()`, `attempt_bypass()`, `validate_url()` — the full L1 pipeline
- `@suite()` decorator from `master_harness/registry.py` — registers L2 as a harness suite
- `Storage` class — `list_sites()`, `record_site_score()`, `get_consecutive_failures()`, `start_run()`, `record_results()`, `finish_run()`
- `_artifact_dir()` pattern from `web_search_resilience.py` — structured artifact directories
- `Reporter` — Telegram alert formatting (Phase 3 will configure thresholds, but wiring happens here)

### Established Patterns
- Suite structure: `@suite(name, tier, schedule, timeout_s, tags)` → `async def run(params) -> list[TestResult]`
- Artifact storage: `{artifact_root}/{suite}/{run_tag}/{test_name}/` with PNGs and metadata files
- Browser session lifecycle: create → navigate → extract → cleanup via HTTP to browser-service:9150
- CF bypass: semaphore-guarded POST to cf-bypass-worker:9160
- Result recording: TestResult with metadata dict containing classification, challenge_detected, artifact paths

### Integration Points
- New suite file: `master_harness/suites/l2_perception.py` — auto-discovered by `discover_suites()`
- Scheduler config: add `l2_perception` section to harness YAML config
- Site catalog: reads from `harness.site_test_catalog` WHERE active=true
- Score recording: writes to `harness.site_test_scores` with classification + confidence
- Artifact root: `/var/lib/openclaw/workspace/harness-artifacts/` (same as web_search_resilience)

</code_context>

<specifics>
## Specific Ideas

- Full transparency maintained from Phase 1 — every classification stored, nothing hidden
- Bypass attempted on every BLOCKED_CHALLENGE to build honest bypass success rate data
- Classification drift detection is the key signal for Phase 3 alerting — record it cleanly
- Sequential processing keeps it simple; can add concurrency later if catalog outgrows the hour window

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-l2-perception-harness*
*Context gathered: 2026-03-10*
