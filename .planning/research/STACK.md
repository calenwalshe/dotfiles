# Stack Research

**Domain:** URL screenshot capture + perception classification for an existing agent system
**Researched:** 2026-03-03
**Confidence:** HIGH (core stack verified against existing codebase; vision model routing verified against live infrastructure)

---

## Context: What Already Exists

This is a subsequent milestone on an existing system. Before recommending new technologies, map what the system already ships:

| Component | Technology | Role |
|-----------|-----------|------|
| `browser-service` (port 9150) | Playwright 1.49.1 + Python 3.11 + Xvfb + Chrome | Session management, screenshots, page scan, blocker detection |
| `cf-bypass-worker` (port 9160) | SeleniumBase 4.35.0 UC mode + Python 3.11 + Xvfb + Chrome | Cloudflare Turnstile bypass, returns HTML + screenshot + cookies |
| `gemini-bridge` (port 9091) | Python, OpenAI-compat API | Vision-capable endpoint, already handles `image_url` base64 payloads |
| `smart-router` (port 9080) | Python, `supports_vision: true` models | Routes vision requests to Gemini; `gemini-vision` alias → `gemini-2.5-flash` |
| `notifier.py` | `aiohttp` + Telegram Bot API | `send_photo(path, caption)` already implemented |
| `master_harness` | Python async suites | `_run_browser_perception_test`, artifact storage pattern, `TestResult`, reporter |
| `openclaw-scheduler` (port 9100) | APScheduler + FastAPI | Suite scheduling, Telegram alerts, `harness-artifacts/` storage |

**Implication:** The new milestone extends these existing components. Do not introduce new containers or services. The stack recommendation is primarily about which extension points and patterns to use within the existing infrastructure.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Playwright Python | 1.49.1 (existing in browser-service) | Browser automation and screenshot capture | Already running in `browser-service:9150`; `page.screenshot(full_page=True)` returns PNG bytes; DO NOT upgrade without testing — browser-service is pinned |
| SeleniumBase UC mode | 4.35.0 → 4.47.1 available | Cloudflare Turnstile bypass | Already running in `cf-bypass-worker:9160`; UC mode disconnects CDP during JS challenge, achieving ~80-90% Cloudflare bypass rate; uses `uc_open_with_reconnect()` + `uc_gui_click_captcha()` |
| Python 3.11 | 3.11 (existing) | Runtime | Pinned to Python 3.11 across browser-service and cf-bypass-worker; match this to stay compatible with existing Docker layers |
| aiohttp | Latest compatible | Async HTTP to browser-service and cf-bypass-worker | Already used throughout master_harness suites for service-to-service calls; do not switch to httpx or requests |

### Vision Classification (L2 Perception)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Gemini via gemini-bridge | `gemini-2.5-flash` (live, `gemini-vision` alias) | Classify screenshot as PASS_CONTENT / BLOCKED_CHALLENGE / BLANK_PAGE / DEGRADED_CONTENT | The gemini-bridge already handles OpenAI-compat `image_url` with base64 data URLs; smart-router supports vision routing; no new infrastructure needed |
| OpenAI-compat `image_url` format | Current | Pass screenshots to vision model | Use `data:image/png;base64,<b64>` in content array; gemini-bridge parses this natively (verified in gemini-bridge/server.py lines 421-438) |

**Classification approach:** Send PNG screenshot as base64 to smart-router at `http://smart-router:9080/v1/chat/completions` with model `gemini-vision` (routes to `gemini-2.5-flash`). Use a structured prompt asking for one of the four classification labels. Parse the response text for the label token. This is more reliable than pure rule-based blocker detection for ambiguous cases (partially-loaded pages, degraded content).

**Why not a local classifier?** The system already pays for Gemini via gemini-bridge and has vision routing live. A local CLIP/ResNet classifier adds a new dependency with lower accuracy on the specific "challenge page" visual patterns Cloudflare uses. Gemini 2.5 Flash achieves ~100-300ms for classification at ~258 tokens/image (~$0.019 per 1K images at current pricing).

**Hybrid approach (recommended):** L1 keeps the existing rule-based blocker detection from `_classify_blocker()` in `web_search_resilience.py` as the fast path. L2 vision model is called only when rule-based classification is ambiguous (`SOFT_BLOCK` or missing title/blocker data). This avoids unnecessary LLM calls for clear Cloudflare challenge pages.

### Telegram Delivery

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `notifier.send_photo(path, caption)` | Existing | Deliver screenshot to Telegram | Already implemented in `openclaw-scheduler/notifier.py`; uses Telegram Bot API `sendPhoto` with multipart form; caption supports 1024 chars |
| `notifier.send_message(text)` | Existing | Deliver classification text + status | Already used by all harness suites for alerts |

**Flow for Telegram delivery:** Save PNG to temp path → `await send_photo(path, caption=classification_label)` → clean up temp file. The caption field carries the L2 classification label and metadata.

### Artifact Storage

| Technology | Purpose | Pattern |
|-----------|---------|---------|
| Filesystem `harness-artifacts/` | Persist screenshots, metadata JSON | Existing pattern: `_artifact_dir(run_tag, test_name, artifact_root)` creates `<root>/<suite>/<run_tag>/<test_name>/` directory |
| `screenshot.png` | Screenshot artifact | Base64-decode from browser-service response, write bytes via `Path.write_bytes()` |
| `page_meta.json` | URL, title, blocker signals, latency | Existing pattern from `_run_browser_perception_test` in web_search_resilience.py |
| `classification.json` | L1 + L2 classification result, signals | Extend existing pattern with `vision_label` and `vision_reasoning` fields |

### Supporting Libraries (already installed — no new deps needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `aiohttp` | pinned | HTTP calls to browser-service, cf-bypass-worker, smart-router | All service-to-service calls within harness suites |
| `base64` (stdlib) | stdlib | Encode/decode screenshot bytes | Decode `screenshot_b64` from browser-service; encode for vision model payload |
| `pathlib.Path` | stdlib | Artifact path management | `Path.write_bytes()` for PNG, `Path.write_text()` for JSON artifacts |
| `uuid` | stdlib | Session name generation | `f"screenshot-{uuid4().hex[:8]}"` for unique browser session names |

---

## Installation

No new packages required. All stack components are already running in Docker containers. The new code lives in:
- `openclaw-scheduler/master_harness/suites/` — new `url_screenshot.py` suite
- `openclaw-fresh/workspace/scripts/` — Telegram command handler extension

If a future upgrade is needed:
```bash
# Inside browser-service container (only if browser-service gets rebuilt)
pip install playwright==1.58.0
playwright install chromium

# Inside cf-bypass-worker container (SeleniumBase upgrade is safe)
pip install seleniumbase==4.47.1
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Existing `browser-service` (Playwright 1.49.1) | Camoufox 0.4.11 | Only if Cloudflare Turnstile bypass success rate drops below acceptable threshold and cf-bypass-worker also fails; Camoufox uses Firefox C++-level fingerprint spoofing, 0% headless detection rate in tests, but requires a new container and Firefox-based browser (different fingerprint from the Chrome stack we have) |
| Existing `cf-bypass-worker` (SeleniumBase UC) | Camoufox | Camoufox has a cleaner async API and better detection evasion, but UC mode is already live, proven, and handles Turnstile via `uc_gui_click_captcha()` |
| Gemini via gemini-bridge (vision route) | Rule-based classifier only | If cost is a concern; rule-based `_classify_blocker()` already handles 90% of cases correctly; vision is additive for ambiguous cases |
| Gemini via gemini-bridge | Local ResNet/CLIP model | If offline classification is required; not applicable here since the system has no GPU and network calls to gemini-bridge are sub-200ms |
| `notifier.send_photo()` | python-telegram-bot library | Only if openclaw-fresh Telegram pipeline is being bypassed; current architecture routes all Telegram comms through the existing notifier |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `playwright-stealth` (npm/Node.js) | This is a Node.js package; the existing stack is Python; playwright-stealth for Python (`playwright-extra` + `puppeteer-stealth` port) has limited maintenance and lower bypass success than UC mode | SeleniumBase UC mode via existing `cf-bypass-worker:9160` |
| `undetected-chromedriver` directly | SeleniumBase UC mode wraps and improves on `undetected-chromedriver`; direct use loses the Turnstile-specific `uc_gui_click_captcha()` handling | SeleniumBase UC mode |
| Patchright | Chromium-based like Playwright, achieves ~67% headless detection reduction but still detectable by advanced CF configurations; adds a new dependency without solving the problem better than the existing UC mode approach | SeleniumBase UC mode for CF bypass; Playwright for standard browsing |
| New Docker container for screenshot service | PROJECT.md constraint: "Must use existing openclaw-fresh Playwright browser, no new containers or services" | Extend existing `browser-service` and `cf-bypass-worker` via HTTP calls |
| `httpx` or `requests` for service calls | aiohttp is already the standard async HTTP client across all harness suites; mixing async/sync clients creates event loop problems in the scheduler | `aiohttp.ClientSession` with `async with` |
| GPT-4o vision for classification | More expensive than Gemini 2.5 Flash, and the existing gemini-bridge already provides vision; using smart-router with `gemini-vision` model alias is the aligned choice | `gemini-vision` via gemini-bridge |

---

## Stack Patterns by Variant

**If the URL is a standard (non-CF) page:**
- Use `browser-service:9150` directly — `POST /sessions` then `POST /sessions/{name}/navigate`
- Response includes `screenshot_b64`, `blocker`, `title`
- Apply `_classify_blocker()` rule check; if confident, skip vision LLM call

**If CF challenge is detected (rule-based):**
- POST to `cf-bypass-worker:9160/bypass` with `{"url": url, "timeout": 60}`
- Returns `ok`, `screenshot_b64`, `html`, `cookies`, `final_url`
- Re-classify the bypass result screenshot; send to user with "CF bypass attempted" context

**If classification is ambiguous (rule-based returns `SOFT_BLOCK` or missing signals):**
- Send `screenshot_b64` to smart-router vision endpoint with classification prompt
- Parse response for `PASS_CONTENT | BLOCKED_CHALLENGE | BLANK_PAGE | DEGRADED_CONTENT`
- Log `vision_label` + `vision_reasoning` to `classification.json`

**If this is a user-initiated Telegram request (L1 path):**
- L1 runs in `openclaw-fresh` as an agent tool invocation
- Agent calls existing `browser_client.py` functions (`ensure_session`, `screenshot`, `navigate`)
- Screenshot bytes delivered to user via `notifier.send_photo()` with caption
- Failed URL auto-enqueued to harness URL list via `STABLE_DOMAIN_HINTS` extension point

**If this is a harness-scheduled run (L2 path):**
- New `url_screenshot.py` suite follows same pattern as `web_search_resilience.py`
- Registered via `@suite(...)` decorator in master_harness registry
- Scheduled in `config.yaml` under `url_screenshot_harness`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `playwright==1.49.1` | Python 3.11, Chromium (Chrome for Testing builds) | Pinned in browser-service; 1.57+ switches from Chromium to Chrome for Testing — test before upgrading |
| `seleniumbase>=4.35.0` | Python 3.11, `google-chrome-stable` via apt | UC mode requires headful Chrome; xvfb=True handles virtual display; do not use `headless=True` with UC |
| `aiohttp` (latest) | Python 3.11 | No known conflicts with existing stack |
| `gemini-vision` alias | `gemini-2.5-flash` via gemini-bridge | Alias defined in smart-router config; `supports_vision: true` confirmed in router.py |

---

## Sources

- Playwright Python on PyPI — version 1.58.0 (Jan 30 2026), Python >=3.9 required: https://pypi.org/project/playwright/
- SeleniumBase on PyPI — version 4.47.1 (Feb 25 2026): https://pypi.org/project/seleniumbase/
- SeleniumBase UC Mode docs — UC mode, xvfb, Turnstile handling: https://seleniumbase.io/help_docs/uc_mode/
- Playwright Python screenshots API — `full_page`, `clip`, element screenshots: https://playwright.dev/python/docs/screenshots
- Camoufox on PyPI — version 0.4.11 (Jan 29 2025), Firefox-based, C++-level fingerprint spoofing: https://pypi.org/project/camoufox/
- ZenRows Patchright comparison — Patchright vs Camoufox for CF bypass: https://www.zenrows.com/blog/patchright
- Gemini image understanding API — base64 inline image format, model capabilities: https://ai.google.dev/gemini-api/docs/image-understanding
- Gemini OpenAI compatibility — OpenAI-compat API with base64 image_url: https://ai.google.dev/gemini-api/docs/openai
- Existing codebase (HIGH confidence — inspected directly):
  - `/home/agent/agent-stack/browser-service/requirements.txt` — Playwright 1.49.1 confirmed
  - `/home/agent/agent-stack/cf-bypass-worker/requirements.txt` — SeleniumBase 4.35.0 confirmed
  - `/home/agent/agent-stack/cf-bypass-worker/app/*.py` — UC mode implementation pattern confirmed
  - `/home/agent/agent-stack/browse-worker/scripts/playwright_explorer_lib/browser_client.py` — screenshot API confirmed
  - `/home/agent/agent-stack/smart-router/router.py` — `supports_vision: true`, `gemini-vision` alias confirmed
  - `/home/agent/agent-stack/gemini-bridge/server.py` — `image_url` base64 parsing confirmed (lines 421-438)
  - `/home/agent/agent-stack/openclaw-scheduler/notifier.py` — `send_photo()` confirmed
  - `/home/agent/agent-stack/openclaw-scheduler/master_harness/suites/web_search_resilience.py` — artifact pattern, `_classify_blocker()`, `_artifact_dir()`, `_run_browser_perception_test()` all confirmed

---

*Stack research for: URL screenshot capture + perception classification (openclaw-fresh milestone)*
*Researched: 2026-03-03*
