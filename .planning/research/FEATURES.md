# Feature Research

**Domain:** URL screenshot capture and perception classification system (internal agent tool)
**Researched:** 2026-03-03
**Confidence:** HIGH — existing codebase studied directly; external sources verified current patterns

## Context: What Already Exists

The system extends infrastructure already in place. This shapes the feature list significantly — some "table stakes" features already exist as building blocks:

| Already Built | Where |
|--------------|-------|
| Playwright browser sessions (create/navigate/screenshot) | `browser-service:9150` |
| CF indicator detection (`_has_cf_signal`) | `web_search_resilience.py` lines 42-71 |
| Block classifier returning `BLOCKED_CHALLENGE / SOFT_BLOCK / PASS_CONTENT` | `_classify_blocker()` |
| CF bypass worker | `cf-bypass-worker:9160` with retry logic |
| Artifact storage (screenshot PNG, page_meta.json, classification.json) | `_artifact_dir()` in `web_search_resilience.py` |
| PostgreSQL harness storage (runs, results, site_catalog, site_scores) | `master_harness/storage.py` |
| Telegram alert reporting with new-failure detection | `master_harness/reporter.py` |
| Scheduled harness runner | `openclaw-scheduler` |
| `STABLE_DOMAIN_HINTS` + `SEMANTIC_SCENARIOS` extension points | `web_search_resilience.py` lines 53-66 |

The new milestone needs to **wire** these together into a user-facing capability and extend the harness, not rebuild from scratch.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must exist or the system is broken / incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Accept URL via Telegram (`/screenshot <url>`) | The whole point — user initiates captures | LOW | Natural language also acceptable; command routing already exists in openclaw-fresh |
| Return screenshot image to Telegram | Useless without seeing the result | LOW | Playwright already returns `screenshot_b64`; need to send via `sendPhoto` |
| Label every screenshot with a classification | "Never silently return garbage" is the core value prop | LOW | `_classify_blocker()` already implemented; wire to user message |
| Report Cloudflare/block detection inline | User needs to know when content is unreliable | LOW | Text prefix on response: "Blocked — CF challenge detected" vs "Content captured" |
| Navigate with wait-for-load (not just DOM ready) | JS-heavy pages render blank without networkidle wait | MEDIUM | Playwright supports `waitUntil: networkidle`; must be in browser-service navigate call |
| Return error message on complete failure | Silent failures are worse than explicit errors | LOW | Already handled in `_run_browser_perception_test` error paths |
| Full-page screenshot option | Many sites have meaningful content below the fold | LOW | Playwright supports `fullPage: true`; expose as option or use as default |

### Differentiators (Competitive Advantage)

Features that go beyond basic capture and make this a capable perception system.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Auto-add failed user URLs to harness test suite | Test surface grows organically from real usage without manual curation | MEDIUM | On BLOCKED_CHALLENGE or blank result, upsert URL into `harness.site_test_catalog`; site_key = hostname |
| Scheduled harness sweeps over accumulated URL catalog | Regression detection catches when previously-working sites break | MEDIUM | Extend existing scheduler job to iterate `site_test_catalog` active entries |
| New-failure Telegram alert ("X now failing — want me to investigate?") | Surfaces regressions the moment they happen, not when user notices | LOW | Reporter already supports new-failure detection; need to wire site perception into it |
| Classification taxonomy beyond binary pass/fail: `PASS_CONTENT / BLOCKED_CHALLENGE / BLANK_PAGE / DEGRADED_CONTENT / NAV_FAILURE` | Richer signal for understanding what went wrong | MEDIUM | `BLANK_PAGE` = screenshot exists but no content signals; `DEGRADED_CONTENT` = partial render; `NAV_FAILURE` = no screenshot at all. Current code has 3 classes; need 2 more |
| Screenshot artifact retention with URL + timestamp index | Enables before/after comparison and failure archaeology | LOW | File system already used (`harness-artifacts/` structure); just need consistent naming |
| Consecutive-failure tracking per URL | Distinguishes "flaky this once" from "site is reliably broken" | LOW | `get_consecutive_failures()` already in `Storage`; just need to use it for per-site context |
| Perception confidence score alongside classification | Quantitative signal more useful than binary; enables trend graphs | HIGH | Would require LLM scoring of screenshot content or heuristic content-signal scoring. Defer to v1.x unless heuristic approach is acceptable |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-investigate failures and propose fixes | Seems like natural next step after detecting failures | v1 milestone explicitly defers this; adds complexity before tracking is proven; easy to implement badly | Track → alert → let operator decide to investigate. Auto-investigation is explicitly scoped to v2 |
| PDF rendering or document capture | Users sometimes want to capture non-HTML content | Out of scope; entirely different rendering path; complicates URL validation | Reject with clear error message: "Only web pages supported" |
| Video/animated capture | Seems useful for dynamic sites | Static screenshot is sufficient for classification; video adds storage, latency, complexity | Return static screenshot + note when page is detected as highly dynamic |
| Public screenshot API endpoint | "Make it available for other systems" | Internal capability; external API needs auth, rate limiting, abuse prevention | Not needed — Telegram is the interface |
| Real-time browser session streaming | "Show me the page as it loads" | Entirely different architecture (WebSocket); massively increases complexity | Return final screenshot; user can re-request if needed |
| User-configurable viewport, delay, and JS toggles | Power users want tuning | UI complexity that doesn't serve the core use case; operator can tune defaults in config | Operator sets defaults; user gets sensible defaults |
| Storing raw HTML alongside screenshot | Seems like useful artifact | Large storage; HTML is less actionable than screenshot + classification for the use case | Store `page_meta.json` (title, URL, blocker signals) which captures the useful metadata |
| Retry loop with automatic proxy rotation | Bypass CF by rotating proxies | Not aligned with this system's architecture (no proxy pool); not the right layer | `cf-bypass-worker` is the designated CF bypass mechanism; its retry behavior is already tunable |

---

## Feature Dependencies

```
[Telegram URL intake command]
    └──requires──> [browser-service: navigate + screenshot] (already exists)
                       └──requires──> [classification logic] (already exists, needs extension)
                                          └──requires──> [Telegram sendPhoto response] (new wiring)

[Auto-add failed URLs to catalog]
    └──requires──> [classification at request time] (above)
    └──requires──> [harness.site_test_catalog upsert] (already in Storage)

[Scheduled harness sweep]
    └──requires──> [site_test_catalog populated] (above)
    └──requires──> [classification logic] (existing)
    └──requires──> [artifact storage] (existing)

[New-failure Telegram alert]
    └──requires──> [scheduled harness sweep] (above)
    └──requires──> [consecutive failure tracking] (already in Storage)
    └──enhances──> [auto-add failed URLs] (more alerts = better coverage)

[BLANK_PAGE / DEGRADED_CONTENT classification]
    └──requires──> [screenshot artifact exists] (existing)
    └──enhances──> [classification taxonomy] (extends existing 3-class taxonomy)

[Consecutive-failure context in alerts]
    └──requires──> [scheduled harness sweep running]
    └──requires──> [Storage.get_consecutive_failures()] (already exists)
```

### Dependency Notes

- **Telegram URL intake requires browser-service:** The `browser-service:9150` API already exists and is used by `web_search_resilience.py`. The new feature re-uses the same `/sessions` + `/sessions/{name}/navigate` + screenshot API.
- **Auto-add to catalog requires classification first:** You need to know a URL failed before auto-enrolling it. The catalog upsert happens at the end of the user request handler.
- **New-failure alert requires the scheduled sweep:** The alert fires when a URL that previously passed now fails. Without a baseline established by scheduled runs, there's nothing to compare against.
- **BLANK_PAGE class is independent:** Can add it to the classifier without the scheduled sweep being complete.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — validates the core concept end-to-end.

- [ ] Telegram command handler: `screenshot <url>` in openclaw-fresh — routes URL to browser-service, returns screenshot + classification label
- [ ] Extend `_classify_blocker()` with `BLANK_PAGE` and `DEGRADED_CONTENT` classes — screenshot exists but content signals are absent
- [ ] Wire sendPhoto response back to user with classification prefix in caption: e.g. "PASS_CONTENT — discogs.com" or "BLOCKED_CHALLENGE — CF detected"
- [ ] On BLOCKED_CHALLENGE result, attempt CF bypass via `cf-bypass-worker` and re-capture before responding
- [ ] On any non-PASS_CONTENT result for a user request, upsert URL into `harness.site_test_catalog` for ongoing monitoring
- [ ] Add `perception_screenshot` harness suite that iterates active `site_test_catalog` entries and runs captures on a schedule (weekly or daily)
- [ ] Wire harness suite results into the existing Reporter for new-failure Telegram alerts

### Add After Validation (v1.x)

Features to add once the v1 harness has accumulated data and the tracking proves useful.

- [ ] Consecutive-failure count in alert messages — "discogs.com has been BLOCKED_CHALLENGE for 3 consecutive runs"
- [ ] `content_confidence` score using heuristic content-signal count (link count, text length, heading count) as proxy — stored in `site_test_scores`
- [ ] Harness result page in chat-frontend showing site catalog health over time

### Future Consideration (v2+)

Features to defer until v1 tracking proves the failure classification works.

- [ ] Auto-investigation dev loop — L2 detects new failure pattern, proposes a fix via LLM, operator approves — explicitly out of scope for v1 per PROJECT.md
- [ ] LLM-based screenshot scoring (send screenshot to vision model, get content confidence 0.0-1.0) — expensive, adds cost; worth it only after baseline established

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Telegram `/screenshot <url>` → image + classification | HIGH | LOW (wiring existing pieces) | P1 |
| CF bypass on BLOCKED_CHALLENGE | HIGH | LOW (cf-bypass-worker already exists) | P1 |
| BLANK_PAGE / DEGRADED_CONTENT classification extension | HIGH | LOW (extend existing classifier) | P1 |
| Auto-add failed URLs to site catalog | HIGH | LOW (Storage.upsert_site exists) | P1 |
| Scheduled perception harness sweep | HIGH | MEDIUM (new suite, schedule config) | P1 |
| New-failure Telegram alert | HIGH | LOW (Reporter already does this) | P1 |
| Consecutive-failure count in alerts | MEDIUM | LOW | P2 |
| Content confidence heuristic score | MEDIUM | MEDIUM | P2 |
| LLM vision scoring of screenshots | LOW | HIGH | P3 |
| Auto-investigation dev loop | LOW (v1) | HIGH | P3 |

---

## Sources

- Codebase: `/home/agent/agent-stack/openclaw-scheduler/master_harness/suites/web_search_resilience.py` — existing perception test patterns, CF detection, classification taxonomy, artifact storage
- Codebase: `/home/agent/agent-stack/openclaw-scheduler/master_harness/storage.py` — `site_test_catalog`, `site_test_scores`, `get_consecutive_failures()` already exist
- Codebase: `/home/agent/agent-stack/openclaw-scheduler/master_harness/reporter.py` — new-failure detection and Telegram alert formatting already implemented
- PROJECT.md: explicit anti-features and out-of-scope items (auto-investigation, PDF, video, public API)
- [Playwright Screenshots docs](https://playwright.dev/docs/screenshots) — fullPage, networkidle, animations:disabled options (HIGH confidence)
- [ZenRows: Playwright Screenshot 2026](https://www.zenrows.com/blog/playwright-screenshot) — current state of anti-bot evasion during screenshot capture (MEDIUM confidence)
- [Scrapfly: Cloudflare-protected screenshots](https://scrapfly.io/blog/posts/how-to-screenshot-cloudflare-protected-websites) — CF bypass approaches for screenshot capture (MEDIUM confidence)
- [Browserless: Bypass Cloudflare with Playwright 2025](https://www.browserless.io/blog/bypass-cloudflare-with-playwright) — behavioral analysis evasion patterns (MEDIUM confidence)

---
*Feature research for: URL screenshot capture and perception classification system*
*Researched: 2026-03-03*
