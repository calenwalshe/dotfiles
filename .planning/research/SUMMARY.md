# Project Research Summary

**Project:** URL Screenshot Capture + Perception Classification (openclaw-fresh milestone)
**Domain:** Browser automation, visual perception classification, CF bypass, agent tooling
**Researched:** 2026-03-03
**Confidence:** HIGH

## Executive Summary

This milestone extends an already-complete infrastructure stack rather than building from scratch. Every major building block — Playwright browser sessions, Cloudflare bypass, vision model routing, Telegram delivery, artifact storage, harness scheduling, and PostgreSQL persistence — is already operational in the existing agent-stack containers. The work is primarily integration wiring: connect these pieces into two new entry points (an L1 user-facing tool in openclaw-fresh and an L2 scheduled harness suite in openclaw-scheduler), share a single classification contract between them, and hand off failures from L1 to L2 via the existing `site_test_catalog` table.

The recommended approach is a strict two-layer design. L1 is a thin tool callable by the main agent: accept URL from Telegram, navigate via browser-service, classify the result with the existing `_classify_blocker()` function (extended to add `BLANK_PAGE` and `DEGRADED_CONTENT`), attempt CF bypass via cf-bypass-worker if blocked, then return screenshot + classification label to the user in one Telegram photo message. L2 is a new harness suite that reads from `site_test_catalog`, runs the same perception cycle on a schedule, and feeds results into the existing Reporter for new-failure Telegram alerts. The L1-to-L2 handoff is a single `upsert_site()` call when a user request fails — no direct coupling between containers.

The primary risks are operational, not technical. Cloudflare's bot detection evolves continuously and silently — a bypass that passes today can fail next week without any error signal. The existing Discogs harness test must serve as the ongoing canary. The second risk is classification accuracy: both the rule-based `_classify_blocker()` function and any future LLM perception layer can return `PASS_CONTENT` for challenge pages when signals are soft. Defense-in-depth (CF indicator string check + blocker metadata + optional LLM visual check for ambiguous cases) is the required pattern. The third operational risk is harness URL noise: auto-adding every user failure URL directly to scheduled test runs produces alert fatigue within days. A staging queue with explicit operator promotion is mandatory from the start.

## Key Findings

### Recommended Stack

The stack is entirely determined by the existing infrastructure — no new packages, containers, or services are needed. All components are already running in Docker and confirmed by direct codebase inspection.

**Core technologies:**
- Playwright 1.49.1 (browser-service:9150): navigate + screenshot — pinned version, do not upgrade without testing
- SeleniumBase 4.35.0 UC mode (cf-bypass-worker:9160): Cloudflare Turnstile bypass — `uc_gui_click_captcha()` handles Turnstile; headful only (xvfb=True)
- Gemini 2.5 Flash via gemini-bridge (smart-router:9080, alias `gemini-vision`): optional L2 visual classification for ambiguous cases — vision routing confirmed live
- aiohttp: all service-to-service HTTP calls — already standard across all harness suites; do not mix httpx or requests
- notifier.send_photo() + send_message(): Telegram delivery — already implemented; caption supports 1024 chars
- harness-artifacts/ filesystem + PostgreSQL harness schema: artifact and result persistence — tables and storage patterns already exist

**Decision point on LLM classification:** The hybrid approach is recommended. Keep rule-based `_classify_blocker()` as the fast path for clear cases. Call the vision model (gemini-vision) only when classification is ambiguous (`SOFT_BLOCK` or missing title/blocker signals). This avoids per-screenshot LLM cost on the majority of cases while adding accuracy for edge cases. Full LLM-per-screenshot scoring is a v2+ feature.

See `.planning/research/STACK.md` for version compatibility table and all "What NOT to Use" guidance.

### Expected Features

**Must have (table stakes — v1):**
- Telegram `/screenshot <url>` command handler in openclaw-fresh — returns screenshot image + classification label in one message
- CF bypass on BLOCKED_CHALLENGE — attempt cf-bypass-worker before returning failure result to user
- Extended classification taxonomy: `PASS_CONTENT / BLOCKED_CHALLENGE / BLANK_PAGE / DEGRADED_CONTENT / NAV_FAILURE` — BLANK_PAGE and DEGRADED_CONTENT are new additions to existing 3-class taxonomy
- Auto-add failed user URLs to staging queue (not directly to scheduled test runs) — staging queue requires explicit operator promotion
- Scheduled `url_screenshot` harness suite — iterates site_test_catalog, runs captures, stores results in harness schema
- New-failure Telegram alert — fires when a previously-passing URL starts failing; Reporter already supports this pattern

**Should have (v1.x — add after validation):**
- Consecutive-failure count in alert messages ("discogs.com: BLOCKED_CHALLENGE for 3 consecutive runs")
- Content confidence heuristic score using link count, text length, heading count as proxy

**Defer (v2+):**
- Auto-investigation dev loop — explicitly out of scope per PROJECT.md; add only after tracking proves reliable
- LLM vision scoring per screenshot — expensive; worth it only after baseline data accumulates

**Anti-features to reject immediately:** PDF rendering, video capture, public screenshot API endpoint, user-configurable viewport/delay toggles, storing raw HTML.

See `.planning/research/FEATURES.md` for full prioritization matrix and dependency graph.

### Architecture Approach

The system decomposes into L1 (user-facing, synchronous) and L2 (autonomous, scheduled), sharing a classification contract and connected by a single database handoff point. L1 runs inside openclaw-fresh; L2 runs inside openclaw-scheduler. browser-service, cf-bypass-worker, and all supporting infrastructure are unchanged.

**Major components:**
1. `screenshot_tool.py` (openclaw-fresh/workspace/tools/) — L1 actor: parse URL, call browser-service, classify, attempt CF bypass, return photo + label to user, upsert failure to site_test_catalog
2. `url_screenshot.py` (openclaw-scheduler/master_harness/suites/) — L2 harness suite: read site_test_catalog, run perception cycle, write results to storage, feed Reporter
3. `_classify_blocker()` in a shared module — classification contract used by both L1 and L2; single canonical location; must not be duplicated
4. `site_test_catalog` (PostgreSQL harness schema) — the L1-to-L2 handoff; L1 writes on failure, L2 reads for scheduling; staging queue column distinguishes promoted vs pending URLs
5. Reporter + notifier pipeline (existing) — new-failure detection and Telegram alerts; no changes needed to reporter.py

**Key patterns:**
- Thin Actor, Fat Harness: L1 is intentionally minimal; all scheduling, comparison, and alerting complexity belongs in L2
- Shared classification contract: one function, one location, imported by both layers
- Artifact directory per test run: PNG to filesystem, metadata to JSONB; never store screenshots in PostgreSQL
- Session cleanup in finally blocks: always DELETE browser sessions to prevent Chromium process leaks

See `.planning/research/ARCHITECTURE.md` for full data flow diagrams and anti-patterns.

### Critical Pitfalls

1. **CF bypass silently failing between deployments** — Cloudflare updates detection without announcement; existing bypass returns challenge page screenshots mis-classified as PASS_CONTENT. Prevention: treat the existing Discogs harness test as a P0 canary; any new BLOCKED_CHALLENGE on a previously-passing URL is an immediate alert. Wire "bypass health" metric (success rate over 24h) into the alerting system from day one of L1.

2. **LLM or rule-based classifier returning PASS_CONTENT for challenge pages** — Soft CF challenges do not set `blocked: true` in browser-service response; LLMs are confidently wrong on ambiguous inputs. Prevention: always cross-check blocker metadata AND HTML title AND CF_INDICATORS string list; never trust a single signal. For LLM calls, require the model to cite a specific visible content element — inability to cite real content should default to DEGRADED_CONTENT.

3. **Screenshot captured before page has rendered** — JS-heavy sites return blank or spinner screenshots on `load` event. Prevention: default wait strategy is `waitUntil: load` plus explicit `waitForTimeout(1500)`; classify "capture completed in under 200ms" as suspicious fast-capture warning.

4. **Auto-added URLs growing harness into noise** — User failures auto-enrolled directly into scheduled test runs create alert fatigue within days. Prevention: auto-add goes to staging queue, not the live test suite; operator promotes URLs explicitly via Telegram; enforce maximum harness size (20 URLs) until actively managed.

5. **CF bypass worker contention** — Concurrent user request + harness run exhaust the cf-bypass-worker browser contexts, causing timeouts. Prevention: `asyncio.Semaphore(1)` around all bypass calls; user requests take priority; hard cap on total bypass timeout at 120s.

## Implications for Roadmap

Based on the architecture's explicit build-order dependency graph and pitfall phase assignments, three phases are the right structure:

### Phase 1: L1 Screenshot Actor

**Rationale:** L1 is independently testable from day one — a user can request a screenshot and verify the result immediately. L1 failures populate site_test_catalog with real URLs, giving L2 real test data before L2 is even written. All critical pitfalls (CF bypass health, screenshot timing, bypass worker concurrency guard) are L1-phase concerns — they must be addressed here, not retrofitted.

**Delivers:** User-facing screenshot capability via Telegram; `screenshot_tool.py` tool in openclaw-fresh; extended 5-class taxonomy (`_classify_blocker()` updated); CF bypass integration with concurrency guard; staging queue upsert on failure; SSRF URL validation.

**Addresses (from FEATURES.md):** Telegram `/screenshot <url>`, screenshot + classification label in one message, CF bypass on BLOCKED_CHALLENGE, BLANK_PAGE/DEGRADED_CONTENT classification, staging queue auto-add.

**Avoids (from PITFALLS.md):** Screenshot timing pitfall (wait strategy decided here), CF bypass contention (semaphore added here), SSRF security mistake (URL validation at intake).

**Research flag:** Standard patterns — browser-service API, aiohttp async calls, notifier.send_photo() are all verified. No additional research needed.

---

### Phase 2: L2 Perception Harness Suite

**Rationale:** L2 depends on a stable classification contract from L1 (classifications must match between user requests and scheduled runs). L2 also needs real URLs in site_test_catalog — those come from L1 usage. Building L2 second ensures there is data to test against and that the classification contract is not changing under the harness.

**Delivers:** `url_screenshot.py` harness suite in master_harness/suites/; `@suite` registration and scheduler job; site_test_catalog integration (reads next site, records scores); artifact storage with pruning policy; Reporter wired to produce new-failure and recovered alerts for per-URL classification changes.

**Addresses (from FEATURES.md):** Scheduled perception harness sweep, new-failure Telegram alert, screenshot artifact retention, consecutive-failure tracking.

**Avoids (from PITFALLS.md):** Auto-add URL noise (staging queue enforced, not direct enrollment), LLM mis-classification (ground-truth fixture set of 5-10 labeled screenshots tested before harness goes live), disk fill (pruning policy present from first run).

**Research flag:** Standard patterns — web_search_resilience.py is the direct template; @suite decorator, Storage API, Reporter are all confirmed. No additional research needed.

---

### Phase 3: Failure Pattern Alerting and Operator Workflow

**Rationale:** Alerting requires historical data — the Reporter's new-failure detection only works when there are at least 2 runs to compare. Building this last ensures there is a baseline before alert logic is tuned. This phase also covers the operator-facing staging queue promotion workflow (how does the operator see and promote pending URLs).

**Delivers:** Tuned alert messages for per-URL failure class changes ("New failure pattern on discogs.com"); operator Telegram command to list and promote staging queue entries; consecutive-failure count in alert messages; "bypass health" daily digest showing bypass success rate.

**Addresses (from FEATURES.md):** New-failure alert (wired and verified with real data), consecutive-failure count in alerts (v1.x feature pulled forward if data confirms value).

**Avoids (from PITFALLS.md):** Alert fatigue from noisy harness (staging queue promotion workflow gives operator control); CF bypass silent failure (bypass health metric wired to alert).

**Research flag:** Reporter and notifier patterns are standard. The staging queue operator workflow (Telegram command handler for queue management) may benefit from reviewing existing openclaw-fresh command dispatch patterns before implementation.

---

### Phase Ordering Rationale

- L1 before L2: L2 reads from site_test_catalog populated by L1; classification contract must be stable before L2 is built
- L2 before alerting: Alert comparison requires baseline data that only exists after L2 has run at least twice
- CF bypass contention guard in Phase 1: If this is deferred, concurrent user + harness runs cause timeouts the moment L2 is activated — must be in place before L2 ships
- Staging queue in Phase 2: If auto-add goes directly to scheduled runs (the shortcut), harness becomes noisy before Phase 3 alerting is in place to detect the problem

### Research Flags

Phases with standard patterns (skip research-phase):
- **Phase 1:** browser-service API, aiohttp, notifier.send_photo() all verified against live codebase with HIGH confidence
- **Phase 2:** web_search_resilience.py is the direct template; @suite, Storage, Reporter are confirmed; harness suite pattern is well-documented in existing code
- **Phase 3:** Reporter and notifier patterns are standard; Telegram command dispatch patterns exist in openclaw-fresh

Phases likely needing targeted investigation during planning:
- **Phase 3 (staging queue operator workflow):** Review existing openclaw-fresh command handler dispatch before designing the "list/promote staging queue" Telegram commands — confirm the command routing pattern and whether a menu-style reply or free-text command is more appropriate given the existing UX

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Direct codebase inspection of all 7 existing components; version numbers confirmed from requirements.txt files; API surfaces verified from source |
| Features | HIGH | Codebase-verified which building blocks exist; feature list is grounded in what Storage, Reporter, and browser-service already support |
| Architecture | HIGH | Complete data flow diagrams derived from direct inspection of web_search_resilience.py, storage.py, runner.py, reporter.py, registry.py |
| Pitfalls | MEDIUM | CF bypass pitfalls from multiple community sources (MEDIUM confidence); LLM perception pitfalls from research literature (MEDIUM); harness management and session pitfalls from direct codebase analysis (HIGH) |

**Overall confidence:** HIGH

### Gaps to Address

- **CF bypass future-proofing:** The bypass success rate metric and "bypass health alert" are identified as necessary but the implementation details (what threshold, what window, where to store the metric) are not specified in research. Decide during Phase 1 planning: likely a running count in site_test_scores or a dedicated bypass_health table.

- **SSRF URL validation scope:** Research identifies blocking private IP ranges as required, but the exact blocklist (IPv6 link-local, cloud metadata endpoints like 169.254.169.254) needs to be enumerated during Phase 1 implementation.

- **Staging queue promotion UX:** How the operator reviews and promotes URLs from staging to active is not fully specified. This is a small UX decision (Telegram inline keyboard vs /promote command) that should be made during Phase 3 planning based on existing openclaw-fresh UX patterns.

- **Screenshot resize before Telegram delivery:** Research identifies "compress to JPEG 80%, max 1280px wide" as the correct approach, but the existing notifier.send_photo() takes a file path. Whether to resize before writing to temp file, or to add resize capability to the tool, needs to be decided during Phase 1 implementation.

## Sources

### Primary (HIGH confidence)
- `/home/agent/agent-stack/browser-service/app/server.py` — navigate endpoint, session API, screenshot response format
- `/home/agent/agent-stack/browser-service/app/detector.py` — BlockerInfo types, CF signal detection
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/suites/web_search_resilience.py` — classification contract, artifact pattern, CF bypass integration, suite structure
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/storage.py` — site_test_catalog, site_test_scores, get_consecutive_failures(), upsert_site()
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/runner.py` — HarnessRunner, concurrency, timeout handling
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/reporter.py` — new-failure detection, alert level classification, Telegram formatting
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/registry.py` — @suite decorator, auto-discovery
- `/home/agent/agent-stack/smart-router/router.py` — gemini-vision alias, supports_vision: true confirmed
- `/home/agent/agent-stack/gemini-bridge/server.py` — image_url base64 parsing confirmed (lines 421-438)
- `/home/agent/agent-stack/openclaw-scheduler/notifier.py` — send_photo(), send_message() confirmed
- `/home/agent/.planning/PROJECT.md` — explicit scope constraints (no new containers, auto-investigation deferred)

### Secondary (MEDIUM confidence)
- [ZenRows: How to Bypass Cloudflare with Playwright 2026](https://www.zenrows.com/blog/playwright-cloudflare-bypass) — CF detection arms race, bypass failure modes
- [Browserless: Bypass Cloudflare with Playwright 2025](https://www.browserless.io/blog/bypass-cloudflare-with-playwright) — current bypass strategies
- [WebScraper.io: Chrome bug-based Cloudflare detection Feb 2025](https://webscraper.io/blog/google-patches-100-precise-cloudflare-turnstile-bot-check) — silent detection update risk confirmed
- [ZenRows: Playwright Screenshot 2026](https://www.zenrows.com/blog/playwright-screenshot) — anti-bot evasion during screenshot capture
- [Playwright GitHub #620](https://github.com/microsoft/playwright/issues/620) — screenshot timing/rendering issues (HIGH confidence as official repo)
- [Playwright GitHub #19861](https://github.com/microsoft/playwright/issues/19861) — lazy load screenshot problem confirmed
- [Gemini image understanding API](https://ai.google.dev/gemini-api/docs/image-understanding) — base64 inline image format, model capabilities
- [Nature Scientific Reports: VLM accuracy trade-offs](https://www.nature.com/articles/s41598-025-04384-8) — LLM confident wrong answer mechanics

### Tertiary (LOW confidence)
- [CloakBrowser GitHub](https://github.com/CloakHQ/CloakBrowser) — stealth patches (single source; not used in recommended approach)

---
*Research completed: 2026-03-03*
*Ready for roadmap: yes*
