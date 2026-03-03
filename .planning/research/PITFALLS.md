# Pitfalls Research

**Domain:** URL screenshot capture + LLM perception classification + CF bypass for agent systems
**Researched:** 2026-03-03
**Confidence:** MEDIUM — CF/Playwright findings verified by multiple sources; LLM perception pitfalls from community + research; harness management from direct codebase analysis

---

## Critical Pitfalls

### Pitfall 1: CF Bypass Silently Breaks Between Deployments

**What goes wrong:**
Cloudflare ships silent detection updates (fingerprint checks, TLS JA3 analysis, new JS challenges) that invalidate previously working bypass strategies with no announcement. A bypass that works today is detected next week. The system continues returning screenshots, but they are now challenge pages — silently mis-classified as PASS_CONTENT if the detector isn't updated in sync.

**Why it happens:**
The bot-detection arms race is asymmetric: Cloudflare sees exactly how each open-source bypass technique works (the code is public) and can patch detection for it specifically. Community bypass tools (playwright-extra stealth, nodriver, patchright, camoufox) lag Cloudflare updates by days to weeks. A February 2025 Chrome bug-based detection broke all major frameworks simultaneously.

**How to avoid:**
- Never assume CF bypass is in a "solved" state; treat it as a perishable capability that must be tested continuously
- The existing `web_search_resilience.py` Discogs test IS the regression canary — keep it running and treat any new BLOCKED_CHALLENGE result on a previously-passing URL as a P0 signal
- Pin CF_INDICATORS to the current known strings AND classify "challenge page returned screenshot" as a distinct harness failure class, not a generic BLOCKED_CHALLENGE
- Add a "bypass health" metric tracked over time: if bypass success rate drops below threshold over a 24h window, alert immediately

**Warning signs:**
- Discogs harness test flips from PASS to BLOCKED_CHALLENGE
- Screenshots are returned without error but LLM perception calls them challenge pages
- CF bypass worker latency increases significantly (longer challenge-solving means harder challenges)
- `cf-bypass-worker` logs show repeated `ok: false` responses

**Phase to address:**
L1 Screenshot Actor — build CF detection as a first-class output state, not an afterthought. The bypass health metric must be wired into alerts before user-facing features ship.

---

### Pitfall 2: LLM Perception Classifying Challenge Pages as PASS_CONTENT

**What goes wrong:**
A Cloudflare challenge page or a degraded render can look enough like legitimate content that the LLM returns PASS_CONTENT. Modern challenge pages increasingly resemble real pages (minimal styling, fast presentation). The system then returns a clean classification, the user receives a "successful" screenshot, and nobody notices the content is garbage. This is the "never silently return garbage" anti-goal made real.

**Why it happens:**
LLMs used for visual/text classification are confidently wrong when input is ambiguous. A challenge page with a logo and one sentence can match the semantic structure of legitimate sparse content. The LLM has no ground truth to compare against — it only sees what was captured. Additionally, the existing `_classify_blocker` function in `web_search_resilience.py` depends on page title, URL, and blocker metadata from the browser service — none of which may be present if the CF challenge was soft (no hard block flag set).

**How to avoid:**
- Build the perception query to explicitly ask about the presence of challenge indicators, not just whether content "looks real"
- Include a separate low-cost HTML/title string check (the existing `CF_INDICATORS` list) as a pre-filter *before* invoking the LLM — cheap signals first
- Require the LLM to name the page type AND cite a specific visible content element; a response that cannot cite a real content element should default to DEGRADED_CONTENT
- Add known-good reference screenshots for each test URL in the harness and compare structurally (not pixel-exact, but "does it have the expected navigation region, body region")

**Warning signs:**
- Harness PASS rate is high but manual spot-checks show challenge pages
- L2 perception returns PASS_CONTENT for URLs that are known Cloudflare-protected
- Classification latency is fast (LLM answering confidently without much content to analyze)

**Phase to address:**
L2 Perception Harness — the perception prompt must be tuned and validated against known challenge page screenshots before the harness goes live. Build a small ground-truth fixture set (5-10 labeled screenshots) for regression.

---

### Pitfall 3: Screenshot Timing — Capturing Before Page Has Rendered

**What goes wrong:**
`page.goto()` returns as soon as the navigation event fires. For SPAs, React apps, and heavily JavaScript-rendered sites, the DOM is present but content is blank or loading spinners are visible. The screenshot is taken and classified as BLANK_PAGE or DEGRADED_CONTENT when the page would have been fine with a 2-second wait.

**Why it happens:**
`networkidle` is the "safe" wait condition but it is unreliable for sites with persistent background polling (analytics, WebSocket keepalives, ad networks). Using `load` fires too early. Using `domcontentloaded` is even earlier. There is no universally correct `waitUntil` value — it depends on the target site. The existing browser-service abstracts this, but its defaults may not match all screenshot targets.

**How to avoid:**
- Default wait strategy: `waitUntil: 'load'` then an additional explicit `waitForTimeout(1500)` before screenshot — catches most cases without being brittle
- For known JS-heavy sites, add a `waitForSelector` on a stable content element (configurable per URL in the harness test list)
- For lazy-loaded images: scroll to bottom before screenshot, wait for `networkidle` with a short timeout, then screenshot — this ensures below-fold images load
- Classify "screenshot captured in under 200ms wall time" as a suspicious fast-capture warning — real pages rarely render that fast

**Warning signs:**
- Screenshots show loading spinners or skeleton screens
- Screenshots are mostly white with a small amount of content
- Timing logs show very short capture times

**Phase to address:**
L1 Screenshot Actor — the wait strategy must be decided and implemented in the first working version, not added later. Retrofitting timing changes is hard because it affects every test case.

---

### Pitfall 4: Auto-Added URLs Growing the Harness into Noise

**What goes wrong:**
The design calls for "URLs that fail in user requests are auto-added to the harness test suite." Without curation, this creates a test suite that grows unboundedly with one-off URLs, transient failures, and time-sensitive pages (news articles, time-limited auth pages, login-wall pages). The harness becomes noisy, operators stop paying attention to alerts, and real regressions are missed.

**Why it happens:**
Auto-accumulation is convenient for capturing real-world failures but produces fundamentally different test cases: transient (page no longer exists), ephemeral (content changes daily), login-required (screenshot will always fail without auth), or too site-specific to be a meaningful regression signal.

**How to avoid:**
- Auto-add to a *staging queue*, not directly to the live test suite. New URLs sit in the queue and are reviewed/promoted by the operator via Telegram before they become permanent test cases
- Tag each URL at add-time with: `source=user_request`, `first_seen=timestamp`, `failure_class=...` — this makes curation decisions data-driven
- Enforce a maximum harness size (e.g., 20 URLs) until the operator actively manages it; alert when the limit is approached
- Exclude clearly transient URLs at capture time: URLs containing session tokens, auth redirects, timestamps in path, or single-article news URLs

**Warning signs:**
- Harness has more than 15 URLs and most were added automatically
- Alert fatigue: operator stops acting on harness failure alerts
- Many BLOCKED_CHALLENGE failures in the harness for URLs that legitimately require auth

**Phase to address:**
L2 Perception Harness — the auto-add design decision must be made explicitly during harness setup. Default to staging queue + operator promotion, not silent direct addition.

---

### Pitfall 5: CF Bypass Worker Becomes a Shared Resource Bottleneck

**What goes wrong:**
The `cf-bypass-worker` at port 9160 is a shared container service. If the screenshot feature triggers multiple CF bypass attempts concurrently (e.g., harness schedule + user request at the same time), the bypass worker queues up or exhausts browser contexts, causing timeouts and confusing failure logs. The current `_cf_bypass_fetch` already has retry logic with `timeout_step_s` increase per attempt — if requests pile up, retries stack up further and the system appears "stuck."

**Why it happens:**
CF bypass is computationally expensive (real browser, JS execution, wait cycles). The worker was designed for serial use by the existing `web_search_resilience` harness, not for concurrent user requests plus scheduled harness runs.

**How to avoid:**
- Implement a simple concurrency guard: one CF bypass attempt in flight at a time (asyncio.Semaphore), queue additional requests with a max queue depth
- Do not run harness CF bypass attempts during user-facing request handling — give user requests priority
- Add a `bypass_in_progress` status endpoint or flag that the harness runner checks before scheduling CF-bypass tests
- Set a hard cap on total bypass timeout: if the combined retry chain exceeds 120s, fail fast rather than holding a browser context open indefinitely

**Warning signs:**
- User screenshot requests time out during harness runs
- `cf-bypass-worker` logs show overlapping requests with close timestamps
- Docker stats show cf-bypass-worker container consistently at high CPU during harness windows

**Phase to address:**
L1 Screenshot Actor — when wiring in CF bypass for user requests, add the concurrency guard at that point. Do not bolt it on after the harness is also using the same worker.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode `CF_INDICATORS` string list | Quick detection, no LLM cost | Cloudflare changes challenge wording; misses new challenge types | MVP only — add LLM visual check in next iteration |
| Use `networkidle` as universal wait | One config covers all sites | Timeouts on polling-heavy sites; too slow for fast sites | Never for general-purpose screenshot — site-specific only |
| Auto-add failed URLs directly to harness | Captures real failures immediately | Harness grows noisy; transient URLs cause permanent test flakiness | Never — always use staging queue |
| Single LLM perception prompt for all 4 classes | Simple to implement | Ambiguous cases between DEGRADED_CONTENT and BLOCKED_CHALLENGE; hallucination risk | MVP acceptable if ground-truth fixture set is built early |
| Trust blocker metadata from browser-service | Existing infrastructure reuse | `blocked: false` is returned on soft CF challenges that still show a challenge page | Never as sole signal — always cross-check with HTML content |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `browser-service:9150` | Assuming `screenshot` response is always a valid rendered page | Check `blocker` dict AND HTML title AND page_url after every call; a 200 response can still be a challenge page |
| `cf-bypass-worker:9160` | Treating `ok: true` as "content retrieved" | Verify the bypass result HTML does not contain CF_INDICATORS; `ok: true` means bypass attempt completed, not that content is clean |
| `smart-router:9080` (LLM perception) | Sending full-resolution screenshot binary to LLM | Compress/resize to ≤1280px wide before sending; large images slow the call and may hit token limits |
| `master_harness` (test suite) | Inserting harness test records for every user-triggered URL visit | Write to harness only on explicit fail or explicit promotion; not every visit |
| Telegram bot response | Returning screenshot before classification is complete | Always return classification WITH screenshot in one message; never send screenshot alone as "here you go" |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| LLM call per screenshot in harness | Harness takes 5+ minutes for 10 URLs; costs accumulate | Cache perception results for same URL+screenshot hash; only re-classify on screenshot change | From first harness run if >5 URLs with LLM classification |
| Full-page screenshot on very tall pages | 10+ second screenshot time; huge image file; LLM context overflow | Cap screenshot height at 3000px or use viewport-only shot; send summary section not full page | Any page with infinite scroll or very long content |
| Sequential CF bypass retries in harness | Total harness run time = N * retry_timeout | Run harness CF bypass tests concurrently (controlled by semaphore); log cumulative bypass time | When harness has more than 3 CF-protected URLs |
| Artifact storage unbounded growth | `harness-artifacts/` fills disk; old runs not purged | Add retention policy: keep last 7 days of artifacts per test; prune on each harness run | After ~2 weeks of daily harness runs without pruning |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging full screenshot URLs from user requests | Leaks URLs the operator investigated to logs that may be read by others | Log URL domain only (strip path/query) in info logs; full URL only in debug/artifact |
| Passing arbitrary user-provided URLs directly to Playwright | SSRF: user can screenshot `http://localhost:9080/v1/chat/completions` or internal services | Validate URL scheme is `http/https`; block private IP ranges (10.x, 172.16-31.x, 192.168.x, localhost) before passing to browser |
| Storing raw screenshots in harness artifacts indefinitely | Screenshots may capture authenticated pages with PII | Apply retention policy; treat screenshot artifacts as potentially sensitive; do not expose artifact path in public-facing responses |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Returning only the classification label without explanation | "BLOCKED_CHALLENGE" is not useful; user doesn't know why or what to do | Return: classification + one-sentence plain-English explanation + what the system attempted |
| Reporting "CF detected, attempting bypass..." then going silent for 60+ seconds | User thinks the bot crashed | Send intermediate progress: "...bypass attempt 1 of 2..." with elapsed time |
| Sending a large screenshot image in Telegram without compression | Images >5MB fail to send or are very slow on mobile | Resize/compress to JPEG 80% quality, max 1280px wide before sending to Telegram |
| Only reporting the final classification without bypass attempt detail | Operator can't debug why bypass failed | Always include in the response: what bypass strategy was tried, how many attempts, final status code |

---

## "Looks Done But Isn't" Checklist

- [ ] **L1 screenshot:** Verify the `blocker` dict AND HTML content check happen on every response, not just when `blocked: true` is set — soft CF challenges do not set `blocked: true`
- [ ] **L2 perception:** Verify classification has been tested against actual challenge page screenshots (not just clean pages) before shipping
- [ ] **CF bypass:** Verify the bypass worker returns `ok: true` AND the resulting page HTML does not contain `CF_INDICATORS` — these are separate checks
- [ ] **Harness auto-add:** Verify URLs from user failures go to a staging queue, not directly into scheduled test runs
- [ ] **Telegram response:** Verify the screenshot + classification are sent in a single message, and that the classification is always present (never sends screenshot without label)
- [ ] **Artifact pruning:** Verify old harness artifacts are pruned automatically; no cron job = disk fills up
- [ ] **Concurrency guard:** Verify simultaneous user request + harness run does not cause cf-bypass-worker contention

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| CF bypass silently broken | MEDIUM | 1) Identify new CF detection method from community (undetected-chromedriver, patchright GitHub issues); 2) Update cf-bypass-worker strategy; 3) Re-run Discogs canary test |
| Harness overloaded with noisy URLs | LOW | 1) Archive current harness URL list; 2) Manually curate to 5-10 stable URLs; 3) Implement staging queue before re-enabling auto-add |
| LLM perception returning wrong classes | MEDIUM | 1) Collect 10 mis-classified screenshots as ground truth; 2) Revise perception prompt with explicit counter-examples; 3) Validate against ground-truth fixture set |
| Screenshot blank/white due to timing | LOW | 1) Add `waitForTimeout(2000)` after goto; 2) Re-test affected URLs; 3) Add per-URL `waitForSelector` config for persistent offenders |
| cf-bypass-worker contention causing timeouts | LOW | 1) Add asyncio.Semaphore(1) around bypass calls; 2) Prioritize user requests over harness; 3) Add queue depth cap |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CF bypass silently breaks | L1 Screenshot Actor | Discogs harness canary passes consistently; bypass health metric wired to alert |
| LLM classifies challenge as PASS | L2 Perception Harness | Ground-truth fixture set (5+ labeled screenshots) tested before harness goes live |
| Screenshot before page renders | L1 Screenshot Actor | Test suite includes a known JS-rendered SPA; screenshot shows content, not spinner |
| Auto-add URL noise | L2 Perception Harness | Confirm auto-added URLs land in staging queue, not directly in scheduled test list |
| CF bypass worker contention | L1 Screenshot Actor | Concurrency test: simultaneous user + harness run, no timeout observed |
| Over-confident wrong classification | L2 Perception Harness | Misclassification rate measured on labeled fixture set is <10% |
| Disk fill from artifacts | L2 Perception Harness | Pruning policy present and confirmed running after first full harness execution |

---

## Sources

- [How to Bypass Cloudflare with Playwright in 2026 — ZenRows](https://www.zenrows.com/blog/playwright-cloudflare-bypass) — CF detection methods, arms race dynamics (MEDIUM confidence)
- [Bypass Cloudflare with Playwright BQL 2025 Guide — Browserless](https://www.browserless.io/blog/bypass-cloudflare-with-playwright) — current bypass strategies (MEDIUM confidence)
- [Google patches 100% precise Cloudflare Turnstile bot check — WebScraper.io](https://webscraper.io/blog/google-patches-100-precise-cloudflare-turnstile-bot-check) — Chrome bug-based detection, Feb 2025 (MEDIUM confidence)
- [CloakBrowser GitHub](https://github.com/CloakHQ/CloakBrowser) — stealth patches passing 30/30 detection tests (LOW confidence — single source)
- [How to bypass Cloudflare (updated for 2025) — Apify Blog](https://blog.apify.com/bypass-cloudflare/) — arms race overview, source-level vs config-level patches (MEDIUM confidence)
- [Full page screenshot not rendering correctly — Playwright GitHub #620](https://github.com/microsoft/playwright/issues/620) — timing/rendering issues (HIGH confidence — official repo)
- [Is there any good solution for making fullpage screenshots on lazy load pages — Playwright GitHub #19861](https://github.com/microsoft/playwright/issues/19861) — lazy load problem confirmed (HIGH confidence — official repo)
- [Distinguishing Ignorance from Error in LLM Hallucinations — arXiv](https://arxiv.org/html/2410.22071v2) — confident wrong answer mechanics (MEDIUM confidence)
- [Rethinking VLMs and LLMs for image classification — Nature Scientific Reports](https://www.nature.com/articles/s41598-025-04384-8) — VLM accuracy trade-offs (MEDIUM confidence)
- `web_search_resilience.py` — direct codebase analysis of existing CF detection, bypass, and classification patterns (HIGH confidence — primary source)

---
*Pitfalls research for: URL screenshot capture + LLM perception classification + CF bypass (openclaw-fresh milestone)*
*Researched: 2026-03-03*
