# Phase 1: L1 Screenshot Actor - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

User requests a screenshot of any URL via Telegram. The system navigates to the URL using browser-service, captures a full-page screenshot, classifies it (5-class taxonomy with confidence), handles CF challenges with bypass attempts, and returns the screenshot + classification to the user. Failed URLs are written to site_test_catalog staging queue. Concurrency guard on cf-bypass-worker prevents contention.

</domain>

<decisions>
## Implementation Decisions

### Response Format
- Screenshot delivered as **photo + caption** in Telegram (not separate message)
- Caption is **detailed**: URL, classification label, confidence, load time, challenge status
- Screenshots **resized to Telegram-friendly dimensions** (~1280px wide max) before sending via `notifier.send_photo()`
- **All user-triggered screenshots saved locally** with metadata (URL, timestamp, classification, confidence) — builds artifact history for future harness use

### Challenge UX Flow
- When CF challenge detected: **send the challenge page screenshot first**, then text "Attempting bypass..." — user sees what's happening
- Bypass timeout: **60 seconds** — moderate, gives CF bypass time for Turnstile
- On bypass failure: **send both** challenge screenshot + explanation text — full transparency
- On bypass success: send the real content screenshot with classification
- Retry UX after failure: **Claude's discretion** — may offer retry prompt or let user resend manually

### Failure Communication
- Error message tone: **Claude's discretion** based on error type (technical for DNS/timeout, friendly for "site might be down")
- Diagnostics: **always included** in error messages — error class, latency, retry count — useful for iterating on the system
- BLANK_PAGE or DEGRADED_CONTENT: **auto-retry once** with longer wait (JS-heavy sites may need more time), then send whatever we got with classification

### Classification Display
- Labels shown as **emoji + human-readable**: "OK", "Blocked", "Blank", "Partial", "Soft block" with emoji indicators
- Confidence format: **Claude's discretion** — pick best format (percentage, words, or visual)
- Classification path (rule-based vs vision LLM): **hidden from user** — implementation detail, same output regardless

### Claude's Discretion
- Retry UX after bypass failure (inline button vs manual resend)
- Confidence score display format
- Error message tone calibration by error type
- Exact emoji choices for classification labels
- Screenshot resize dimensions and quality settings

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `notifier.send_photo(photo_path, caption)` — Telegram photo delivery, already handles bot token resolution and error reporting
- `notifier.send_document(doc_path, caption)` — available if full-res needed
- `_classify_blocker(blocker, page_url, title)` — 3-class classifier in `web_search_resilience.py`, needs extension to 5-class and extraction to shared module
- `_has_cf_signal(text)` — CF detection helper, reusable
- `Storage.upsert_site()` — writes to `site_test_catalog` PostgreSQL table, ready for staging queue enrollment
- `browser-service:9150` — `POST /sessions/{name}/navigate` returns `{ok, screenshot_b64, blocker{blocked, type}, title, url}`
- `cf-bypass-worker:9160` — `POST /bypass` endpoint for SeleniumBase UC mode bypass

### Established Patterns
- Browser session lifecycle: create session → navigate → extract data → cleanup (see `web_search_resilience.py` lines 822-860)
- Retry pattern: 2 attempts with error capture on browser navigate failures
- Artifact storage: `_artifact_dir(run_tag, test_name, artifact_root)` creates structured directories
- Blocker classification: `blocker.get("blocked")` + `blocker.get("type")` + text signal matching

### Integration Points
- openclaw-fresh agent receives Telegram messages → needs to recognize screenshot intent → call browser-service HTTP API
- Classification result feeds into `Storage.upsert_site()` for staging queue enrollment on failure
- `BROWSER_SERVICE_URL` and `CF_BYPASS_URL` env vars already defined in scheduler — need equivalent in openclaw-fresh or direct HTTP calls
- Semaphore must wrap cf-bypass-worker calls — shared resource between user requests and harness runs

</code_context>

<specifics>
## Specific Ideas

- Challenge screenshot shown to user before bypass attempt — "show the problem before trying to fix it" approach
- Full transparency on classification and timing — the system should never hide what happened
- Artifacts saved for every user request — dual purpose: immediate user value + future harness test data
- Auto-retry on BLANK/DEGRADED before reporting — JS-heavy sites deserve a second chance with longer wait

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-l1-screenshot-actor*
*Context gathered: 2026-03-03*
