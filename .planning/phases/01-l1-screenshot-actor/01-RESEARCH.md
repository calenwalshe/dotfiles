# Phase 1: L1 Screenshot Actor - Research

**Researched:** 2026-03-03
**Domain:** Browser automation, Cloudflare bypass, image classification, Telegram delivery, Python async HTTP
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Response Format**
- Screenshot delivered as photo + caption in Telegram (not separate message)
- Caption is detailed: URL, classification label, confidence, load time, challenge status
- Screenshots resized to Telegram-friendly dimensions (~1280px wide max) before sending via `notifier.send_photo()`
- All user-triggered screenshots saved locally with metadata (URL, timestamp, classification, confidence) — builds artifact history for future harness use

**Challenge UX Flow**
- When CF challenge detected: send the challenge page screenshot first, then text "Attempting bypass..." — user sees what's happening
- Bypass timeout: 60 seconds — moderate, gives CF bypass time for Turnstile
- On bypass failure: send both challenge screenshot + explanation text — full transparency
- On bypass success: send the real content screenshot with classification
- Retry UX after failure: Claude's discretion — may offer retry prompt or let user resend manually

**Failure Communication**
- Error message tone: Claude's discretion based on error type (technical for DNS/timeout, friendly for "site might be down")
- Diagnostics: always included in error messages — error class, latency, retry count — useful for iterating on the system
- BLANK_PAGE or DEGRADED_CONTENT: auto-retry once with longer wait (JS-heavy sites may need more time), then send whatever we got with classification

**Classification Display**
- Labels shown as emoji + human-readable: "OK", "Blocked", "Blank", "Partial", "Soft block" with emoji indicators
- Confidence format: Claude's discretion — pick best format (percentage, words, or visual)
- Classification path (rule-based vs vision LLM): hidden from user — implementation detail, same output regardless

### Claude's Discretion
- Retry UX after bypass failure (inline button vs manual resend)
- Confidence score display format
- Error message tone calibration by error type
- Exact emoji choices for classification labels
- Screenshot resize dimensions and quality settings

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAPT-01 | L1 captures full-page screenshot of any URL via Playwright browser-service | browser-service POST /sessions + POST /sessions/{name}/navigate pattern confirmed; screenshot_b64 returned in navigate response |
| CLSF-01 | 5-class taxonomy: PASS_CONTENT, BLOCKED_CHALLENGE, BLANK_PAGE, DEGRADED_CONTENT, SOFT_BLOCK | Existing `_classify_blocker()` covers 3 classes (PASS_CONTENT, BLOCKED_CHALLENGE, SOFT_BLOCK); must add BLANK_PAGE (empty screenshot_b64 or near-zero content) and DEGRADED_CONTENT (content present but sparse) |
| CLSF-02 | Rule-based fast path classifies clear cases without LLM call | Existing `_classify_blocker()` is the fast path — extend it with BLANK_PAGE and DEGRADED_CONTENT rules before LLM fallback |
| CLSF-03 | Vision LLM fallback (Gemini 2.5 Flash) classifies ambiguous screenshots | gemini-vision alias confirmed on smart-router:9080; gemini-bridge confirmed to parse base64 inline images; only call on SOFT_BLOCK or ambiguous fast-path result |
| CLSF-04 | Confidence score (0.0–1.0) attached to each classification result | Rule-based fast path returns high confidence (0.9+); LLM path asks model to return explicit confidence; manual heuristics for BLANK (content byte length) |
| INFR-01 | Concurrency guard (asyncio.Semaphore) on shared cf-bypass-worker prevents contention | `asyncio.Semaphore(1)` wraps all `POST http://cf-bypass-worker:9160/bypass` calls; shared module-level semaphore in screenshot_tool.py |
</phase_requirements>

---

## Summary

Phase 1 builds `screenshot_tool.py` — a Python tool callable by the openclaw-fresh `main` agent via its filesystem tool dispatch. The tool accepts a URL from a Telegram user, calls browser-service:9150 to capture a full-page screenshot, classifies the result using an extended 5-class taxonomy, handles Cloudflare challenges with a 60-second bypass attempt via cf-bypass-worker:9160, and returns the screenshot + classification caption as a Telegram photo. The entire pipeline is async Python using aiohttp, matching the established pattern in `web_search_resilience.py`.

The critical integration question — how openclaw-fresh (a Node.js agent) triggers Python tools — is answered by the workspace tool mount pattern. Tools placed in `/home/agent/openclaw-fresh/workspace/tools/` are available to the agent at `/var/lib/openclaw/workspace/tools/` inside the container. The `main` agent dispatches them as subprocess calls (the agent has `security: "full"` exec permissions). The screenshot tool runs as a Python subprocess; results are written to a temp file or stdout; the agent reads the result and calls `notifier.send_photo()` to deliver the screenshot.

The classification contract (`_classify_blocker()`) must be extracted from `web_search_resilience.py` into a shared module (`perception_classifier.py`) that both this tool and the future L2 harness import. This is the single most important architectural decision for Phase 1 — getting the shared contract right avoids a rewrite when L2 is built.

**Primary recommendation:** Build `screenshot_tool.py` as a self-contained Python script in `openclaw-fresh/workspace/tools/`, extract `_classify_blocker()` to `openclaw-scheduler/master_harness/perception_classifier.py` as the shared contract, and wire the tool call through the agent's normal exec path.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | existing (see requirements.txt) | All HTTP calls to browser-service, cf-bypass-worker, smart-router | Already standard across all harness suites; do NOT mix httpx or requests |
| browser-service | running at :9150 | Playwright-based navigate + full-page screenshot | Only browser automation service in stack; confirmed API surface |
| cf-bypass-worker | running at :9160 | SeleniumBase UC mode Cloudflare Turnstile bypass | Only CF bypass service; POST /bypass endpoint confirmed |
| notifier.py | /openclaw-scheduler/notifier.py | Telegram photo + message delivery | Already implemented; send_photo() + send_message() confirmed |
| Pillow (PIL) | existing in scheduler requirements | JPEG resize before Telegram delivery | Standard Python image lib; already available in scheduler container |
| asyncio.Semaphore | stdlib | Concurrency guard on cf-bypass-worker | Zero-dependency; correct tool for single-worker guard |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gemini-vision (smart-router alias) | live at :9080 | Vision LLM fallback for ambiguous classification | Only when rule-based fast path returns SOFT_BLOCK or insufficient signals |
| Storage.upsert_site() | /master_harness/storage.py | Write failed URL to site_test_catalog staging queue | On any non-PASS_CONTENT classification, enqueue for L2 |
| base64 (stdlib) | stdlib | Decode screenshot_b64 from browser-service response | Required to write PNG to temp file for notifier.send_photo() |
| ipaddress (stdlib) | stdlib | SSRF URL validation — block private/loopback/link-local ranges | Required at URL intake before any HTTP call |
| pathlib.Path | stdlib | Artifact directory creation and file writes | Standard across all harness code; use instead of os.path |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiohttp | httpx, requests | httpx/requests not used anywhere in stack; mixing breaks session reuse patterns |
| Pillow resize | Telegram auto-resize | Telegram resizes client-side but does not guarantee max-width; explicit resize gives predictable captions and file sizes |
| subprocess tool dispatch | Direct Python import in Node.js agent | Python tool as subprocess is the established pattern for openclaw-fresh workspace tools; no FFI needed |

**Installation:** No new packages. All dependencies already in scheduler container or stdlib.

---

## Architecture Patterns

### Recommended Project Structure

```
openclaw-fresh/workspace/tools/
└── screenshot_tool.py          # L1 actor: the main deliverable

openclaw-scheduler/master_harness/
├── perception_classifier.py    # NEW: shared classification contract (extracted from web_search_resilience.py)
└── suites/
    └── web_search_resilience.py  # EXISTING: import perception_classifier, remove local _classify_blocker()
```

`screenshot_tool.py` runs inside the openclaw-fresh container at `/var/lib/openclaw/workspace/tools/screenshot_tool.py`. It can import from the scheduler container's mounted paths only if volumes are configured; otherwise it is self-contained with a local copy of the classifier. **Decision required:** either make `perception_classifier.py` accessible via a shared volume mount, or duplicate the minimal classifier logic in `screenshot_tool.py` and commit to keeping them in sync manually.

Recommended: **duplicate the classifier in screenshot_tool.py for Phase 1** (it is ~15 lines), then consolidate to shared module when L2 is built (Phase 2). This avoids cross-container import complexity now while preserving the refactor path.

### Pattern 1: Browser Session Lifecycle

**What:** Create session → navigate → extract screenshot_b64 + blocker → cleanup in finally block
**When to use:** Every screenshot capture request

```python
# Source: web_search_resilience.py lines 822-888 (verified from codebase)
import aiohttp, asyncio, base64, uuid
from pathlib import Path

BROWSER_SERVICE_URL = os.environ.get("BROWSER_SERVICE_URL", "http://browser-service:9150")

async def capture_screenshot(url: str, timeout_s: int = 30) -> dict:
    sess_name = f"l1-{uuid.uuid4().hex[:12]}"
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Create session
            async with session.post(
                f"{BROWSER_SERVICE_URL}/sessions",
                json={"name": sess_name, "url": url},
                timeout=aiohttp.ClientTimeout(total=timeout_s),
            ) as resp:
                create_json = await resp.json()
            if not create_json.get("ok"):
                return {"ok": False, "error": create_json.get("error", "session create failed")}

            # 2. Navigate + capture
            async with session.post(
                f"{BROWSER_SERVICE_URL}/sessions/{sess_name}/navigate",
                json={"url": url},
                timeout=aiohttp.ClientTimeout(total=timeout_s),
            ) as resp:
                nav_json = await resp.json()

            return nav_json  # {ok, screenshot_b64, blocker{blocked, type}, title, url}
        finally:
            # 3. ALWAYS cleanup — prevents Chromium process leaks
            try:
                await session.delete(
                    f"{BROWSER_SERVICE_URL}/sessions/{sess_name}",
                    timeout=aiohttp.ClientTimeout(total=8),
                )
            except Exception:
                pass
```

### Pattern 2: Extended 5-Class Classifier

**What:** Rule-based fast path returning class + confidence; falls through to LLM only for ambiguous cases
**When to use:** After every navigate response

```python
# Source: web_search_resilience.py lines 96-109 + Phase 1 extensions
CF_INDICATORS = [
    "just a moment", "attention required", "cloudflare", "cdn-cgi",
    "verify you are human", "please wait while your request is being verified",
    "captcha", "access denied",
]

def _classify_screenshot(
    blocker: dict | None,
    page_url: str,
    title: str,
    screenshot_b64: str,
    nav_latency_ms: int,
) -> tuple[str, float]:
    """Returns (class_label, confidence 0.0-1.0)."""
    blocker = blocker or {}
    blocked = bool(blocker.get("blocked"))
    btype = str(blocker.get("type", "")).lower()
    combined = f"{page_url} {title} {str(blocker)}"
    cf_like = any(t in combined.lower() for t in CF_INDICATORS) or btype in {"cloudflare", "captcha"}

    # CF challenge — clear signal
    if blocked and cf_like:
        return "BLOCKED_CHALLENGE", 0.95
    if cf_like:
        return "BLOCKED_CHALLENGE", 0.90

    # Blank page — no screenshot data or suspiciously fast load
    if not screenshot_b64 or len(screenshot_b64) < 500:
        return "BLANK_PAGE", 0.90
    if nav_latency_ms < 200:  # suspicious fast-capture
        return "BLANK_PAGE", 0.70

    # Soft block — browser flagged but no CF signal
    if blocked:
        return "SOFT_BLOCK", 0.75

    # Degraded content — screenshot exists but title is empty or generic
    if not title or title.lower() in {"", "untitled", "about:blank"}:
        return "DEGRADED_CONTENT", 0.65

    # Clear pass
    return "PASS_CONTENT", 0.85
    # Ambiguous cases (confidence < 0.70) should fall through to LLM vision
```

### Pattern 3: CF Bypass with Concurrency Guard

**What:** asyncio.Semaphore wraps all bypass calls; user sees challenge screenshot before attempt
**When to use:** On BLOCKED_CHALLENGE classification

```python
# Source: web_search_resilience.py lines 1525-1556 (bypass integration pattern)
CF_BYPASS_URL = os.environ.get("CF_BYPASS_URL", "http://cf-bypass-worker:9160")
_bypass_semaphore = asyncio.Semaphore(1)  # module-level; shared across concurrent requests

async def attempt_bypass(url: str, timeout_s: int = 60) -> dict:
    async with _bypass_semaphore:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CF_BYPASS_URL}/bypass",
                json={"url": url},
                timeout=aiohttp.ClientTimeout(total=timeout_s),
            ) as resp:
                return await resp.json()
    # Returns {ok, screenshot_b64, url, title} or {ok: false, error}
```

### Pattern 4: Screenshot Resize and Telegram Delivery

**What:** Decode base64 PNG, resize to max 1280px wide, write to temp file, call notifier.send_photo()
**When to use:** Final delivery step for every screenshot result

```python
# Source: notifier.py (confirmed), PIL resize pattern
import base64, tempfile
from pathlib import Path

async def deliver_screenshot(
    screenshot_b64: str,
    caption: str,
    chat_id: str,
) -> None:
    # Decode + resize
    img_bytes = base64.b64decode(screenshot_b64.encode("ascii"))
    # PIL resize — import Pillow
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(img_bytes))
    max_w = 1280
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    buf.seek(0)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(buf.read())
        tmp_path = f.name

    # Deliver via notifier
    await notifier.send_photo(tmp_path, caption=caption)
    Path(tmp_path).unlink(missing_ok=True)
```

### Pattern 5: SSRF URL Validation

**What:** Block private IP ranges, loopback, link-local, cloud metadata endpoints before any HTTP call
**When to use:** At URL intake, before calling browser-service

```python
import ipaddress
from urllib.parse import urlparse

BLOCKED_HOSTS = {"169.254.169.254", "metadata.google.internal", "metadata.internal"}

def validate_url(url: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message). Call before any HTTP call."""
    try:
        p = urlparse(url)
        if p.scheme not in {"http", "https"}:
            return False, "URL must use http or https"
        host = p.hostname or ""
        if not host:
            return False, "URL has no host"
        if host.lower() in BLOCKED_HOSTS:
            return False, "URL points to blocked host"
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                return False, "URL resolves to private/reserved address"
        except ValueError:
            pass  # host is a domain name, not an IP — allow
        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {e}"
```

### Anti-Patterns to Avoid

- **Storing screenshots in PostgreSQL:** Store PNGs on filesystem under `harness-artifacts/`, write only path + metadata to DB. Blob storage in Postgres kills query performance.
- **Skipping session cleanup:** Always delete browser sessions in a `finally` block. Leaked sessions accumulate Chromium processes and exhaust browser-service capacity within hours.
- **Calling cf-bypass-worker without semaphore:** Without `asyncio.Semaphore(1)`, concurrent Telegram requests + harness runs exhaust the single bypass worker, causing silent timeouts.
- **Returning challenge screenshot as PASS_CONTENT:** Never trust only `blocker.blocked == False`. Also check CF_INDICATORS against title and URL. Soft challenges do not set the blocked flag.
- **Auto-enrolling user failure URLs directly to scheduled test suite:** Write to staging queue only (a `staging: true` flag in `site_test_catalog`). Direct enrollment creates alert noise before L2 is operational.
- **Importing from openclaw-scheduler inside screenshot_tool.py via Python path hacks:** The two containers do not share a Python environment. Keep the tool self-contained for Phase 1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Telegram photo delivery | Custom multipart/form-data upload | `notifier.send_photo(path, caption)` | Already handles token resolution, error logging, 1024-char caption limit |
| Browser session management | Direct Playwright subprocess | `browser-service:9150` POST /sessions | Session lifecycle, Chromium process management, crash recovery all handled |
| CF Turnstile bypass | Custom Selenium/UC code | `cf-bypass-worker:9160` POST /bypass | UC mode `uc_gui_click_captcha()` + xvfb headful config already tuned |
| Vision LLM calls | Direct Gemini API client | `smart-router:9080` with model `gemini-vision` | Routing, retries, cost tracking, base64 parsing all handled by gemini-bridge |
| URL validation against RFC | Custom regex | `ipaddress` + `urlparse` from stdlib | Edge cases in IPv6, link-local, encoded hosts are handled by stdlib |
| JPEG resize | Manual bytes manipulation | `Pillow` (PIL) | Handles all image format edge cases; one-liner resize |

**Key insight:** Every hard problem in this phase (browser automation, CF bypass, Telegram delivery, vision LLM routing) has a running service or existing function. Phase 1 is integration wiring, not building.

---

## Common Pitfalls

### Pitfall 1: Screenshot captured before page renders

**What goes wrong:** `browser-service` returns screenshot_b64 of a spinner, blank page, or partial render for JS-heavy sites.
**Why it happens:** Playwright's default `waitUntil: load` fires on DOMContentLoaded; React/SPA apps render after JS execution.
**How to avoid:** Classify screenshot_b64 length < 500 bytes as BLANK_PAGE and trigger auto-retry with longer wait (controlled by `waitForTimeout` in navigate payload if browser-service supports it — check API). For BLANK_PAGE result: auto-retry once, then return whatever we got with honest classification.
**Warning signs:** `nav_latency_ms < 200` on a real-world URL; screenshot_b64 < 500 chars; BLANK_PAGE on a site known to have content.

### Pitfall 2: CF challenge mis-classified as PASS_CONTENT

**What goes wrong:** Soft Cloudflare challenges (Turnstile embedded in page, not full-page interstitial) do not set `blocker.blocked = true`. Rule-based classifier returns PASS_CONTENT. User receives challenge page screenshot labelled as "OK".
**Why it happens:** `_classify_blocker()` in its current 3-class form only checks `blocked` flag + type. Soft challenges use JS injection without setting the blocker metadata.
**How to avoid:** Defense-in-depth: check CF_INDICATORS against page title AND URL AND blocker JSON. Never trust a single signal. The extended classifier in this research does this — use it exactly as written.
**Warning signs:** User reports screenshot shows "Just a moment" but label says PASS_CONTENT.

### Pitfall 3: bypass worker contention / timeout cascade

**What goes wrong:** Two Telegram requests arrive simultaneously. Both detect BLOCKED_CHALLENGE. Both call `POST /bypass` concurrently. cf-bypass-worker handles one; the other times out silently after 60s. User receives no response.
**Why it happens:** cf-bypass-worker is a single-instance SeleniumBase UC mode runner — one browser context, no parallelism.
**How to avoid:** Module-level `asyncio.Semaphore(1)` in `screenshot_tool.py`. The second caller blocks until the first bypass completes. Set explicit timeout message if semaphore wait exceeds 90 seconds ("bypass worker busy, try again shortly").
**Warning signs:** Occasional 60s timeout on BLOCKED_CHALLENGE URLs; increases under concurrent load.

### Pitfall 4: Telegram photo caption truncated

**What goes wrong:** Caption exceeds 1024 characters. Telegram API silently truncates or rejects. User sees incomplete classification info.
**Why it happens:** Detailed captions with URL + classification + confidence + load time + error details can easily exceed 1024 chars on long URLs.
**How to avoid:** Cap caption at 900 chars (buffer for safety). Truncate URL to 80 chars with `...` if needed. Keep classification line first (most important).
**Warning signs:** Caption ends mid-sentence; missing fields in output.

### Pitfall 5: Tool dispatch failure in openclaw-fresh (silent)

**What goes wrong:** The agent calls the screenshot tool subprocess but Python is not on PATH, or the tool path is wrong, or the virtualenv is not activated. The agent receives empty stdout and reports "done" without delivering a photo.
**Why it happens:** openclaw-fresh is a Node.js container. Python tool execution depends on the container having Python installed and the tool being on a mounted path.
**How to avoid:** Verify Python availability in openclaw-fresh container before Phase 1 implementation: `docker exec openclaw-fresh which python3`. If absent, the tool must be invoked via `docker exec openclaw-scheduler python3 /path/to/tool.py` from inside openclaw-fresh, or the scheduler exposes an HTTP endpoint for the screenshot action.
**Warning signs:** Tool returns empty output; agent does not send photo; no error message in Telegram.

---

## Code Examples

### Full navigate + classify cycle

```python
# Source: web_search_resilience.py lines 822-888 + Phase 1 extensions
async def screenshot_and_classify(url: str) -> dict:
    """Full pipeline: validate → capture → classify → return result dict."""
    valid, err = validate_url(url)
    if not valid:
        return {"ok": False, "error": err, "class": "NAV_FAILURE", "confidence": 1.0}

    nav = await capture_screenshot(url, timeout_s=30)
    if not nav.get("ok"):
        return {"ok": False, "error": nav.get("error"), "class": "NAV_FAILURE", "confidence": 1.0}

    shot_b64 = nav.get("screenshot_b64", "")
    blocker = nav.get("blocker") or {}
    title = nav.get("title", "")
    final_url = nav.get("url", url)
    latency_ms = nav.get("latency_ms", 0)

    cls, conf = _classify_screenshot(blocker, final_url, title, shot_b64, latency_ms)

    # Auto-retry once on BLANK_PAGE
    if cls == "BLANK_PAGE":
        await asyncio.sleep(2.0)
        nav2 = await capture_screenshot(url, timeout_s=45)
        if nav2.get("ok") and nav2.get("screenshot_b64"):
            shot_b64 = nav2["screenshot_b64"]
            cls, conf = _classify_screenshot(
                nav2.get("blocker") or {}, nav2.get("url", url),
                nav2.get("title", ""), shot_b64, latency_ms,
            )

    return {
        "ok": True,
        "class": cls,
        "confidence": conf,
        "screenshot_b64": shot_b64,
        "title": title,
        "url": final_url,
        "latency_ms": latency_ms,
    }
```

### CF bypass full flow

```python
# Source: web_search_resilience.py lines 1525-1556
async def handle_cf_challenge(url: str, challenge_b64: str) -> dict:
    """
    Called after BLOCKED_CHALLENGE detection.
    Returns result dict with 'bypassed' bool and new screenshot if successful.
    """
    bypass = await attempt_bypass(url, timeout_s=60)
    if not bypass.get("ok"):
        return {"bypassed": False, "screenshot_b64": challenge_b64, "error": bypass.get("error")}

    # Re-classify bypass result
    bypass_b64 = bypass.get("screenshot_b64", "")
    bypass_title = bypass.get("title", "")
    bypass_url = bypass.get("url", url)
    cls, conf = _classify_screenshot({}, bypass_url, bypass_title, bypass_b64, 0)

    if cls == "BLOCKED_CHALLENGE":
        return {"bypassed": False, "screenshot_b64": bypass_b64, "class": cls, "confidence": conf}

    return {"bypassed": True, "screenshot_b64": bypass_b64, "class": cls, "confidence": conf}
```

### Telegram caption format

```python
# Source: CONTEXT.md decision — detailed caption with emoji labels
CLASS_LABELS = {
    "PASS_CONTENT":      "OK",
    "BLOCKED_CHALLENGE": "Blocked",
    "BLANK_PAGE":        "Blank",
    "DEGRADED_CONTENT":  "Partial",
    "SOFT_BLOCK":        "Soft block",
    "NAV_FAILURE":       "Failed",
}

def build_caption(url: str, cls: str, conf: float, latency_ms: int, challenge_status: str = "") -> str:
    label = CLASS_LABELS.get(cls, cls)
    conf_pct = f"{int(conf * 100)}%"
    latency = f"{latency_ms / 1000:.1f}s"
    parts = [
        f"URL: {url[:80]}{'...' if len(url) > 80 else ''}",
        f"Classification: {label} ({conf_pct})",
        f"Load time: {latency}",
    ]
    if challenge_status:
        parts.append(f"Challenge: {challenge_status}")
    return "\n".join(parts)[:900]
```

---

## Open Questions

1. **Is Python available in openclaw-fresh container?**
   - What we know: openclaw-fresh is a Node.js container. The workspace tools directory does not currently exist.
   - What's unclear: Whether `python3` is installed in the container image, and whether it has access to `aiohttp` and `Pillow`.
   - Recommendation: Run `docker exec openclaw-fresh which python3` before implementation. If absent, the screenshot tool must be invoked via `docker exec openclaw-scheduler python3 /path/...` from within openclaw-fresh, OR the scheduler exposes an HTTP endpoint that openclaw-fresh calls. This is the most critical unknown for Phase 1.

2. **How does openclaw-fresh agent dispatch workspace tools?**
   - What we know: Tools are placed in `/home/agent/openclaw-fresh/workspace/tools/` and mounted at `/var/lib/openclaw/workspace/tools/`. The main agent has `security: "full"` exec permissions.
   - What's unclear: Whether the agent auto-discovers Python scripts in that directory and runs them as subprocesses, or whether an explicit tool registration step is required (e.g., a manifest file or Node.js wrapper).
   - Recommendation: Inspect the openclaw-fresh container's tool discovery mechanism before writing screenshot_tool.py. Run `docker exec openclaw-fresh ls /var/lib/openclaw/workspace/` and check for existing tool examples or a `tools.json` manifest.

3. **Does browser-service navigate endpoint support custom wait timeout?**
   - What we know: POST /sessions/{name}/navigate accepts `{url}`. Returns screenshot after page load.
   - What's unclear: Whether an additional `waitTimeout` or `waitUntil` parameter is accepted for JS-heavy sites.
   - Recommendation: Check `/home/agent/agent-stack/browser-service/app/server.py` navigate handler for accepted params. If not supported, the BLANK_PAGE auto-retry with `asyncio.sleep(2.0)` is the fallback.

4. **Where does `notifier.send_photo()` live relative to screenshot_tool.py?**
   - What we know: `notifier.py` is in `openclaw-scheduler/notifier.py` and is used by scheduler jobs.
   - What's unclear: Whether screenshot_tool.py (running in openclaw-fresh) can import notifier.py, or whether photo delivery must be handled by the openclaw-fresh agent itself (via its own Telegram API calls).
   - Recommendation: Most likely, screenshot_tool.py outputs the screenshot file path + caption JSON to stdout, and the openclaw-fresh agent (which already has Telegram access) handles delivery. Confirm by checking how openclaw-fresh sends photos to users currently.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 3-class blocker taxonomy (PASS, BLOCKED, SOFT) | 5-class taxonomy adding BLANK_PAGE, DEGRADED_CONTENT | Phase 1 | L1 can honestly report blank/degraded captures rather than mis-labeling as PASS |
| LLM called on every screenshot | Rule-based fast path + LLM only on ambiguous | Design decision | Eliminates per-screenshot LLM cost; fast path handles 80%+ of cases |

---

## Sources

### Primary (HIGH confidence)
- `/home/agent/agent-stack/openclaw-scheduler/master_harness/suites/web_search_resilience.py` — `_classify_blocker()` (lines 96-109), browser session lifecycle (lines 822-888), CF bypass integration (lines 1525-1556), CF_INDICATORS list (lines 42-51)
- `/home/agent/agent-stack/openclaw-scheduler/notifier.py` — `send_photo()`, `send_message()` signatures confirmed
- `/home/agent/.planning/research/SUMMARY.md` — stack versions, service URLs, pitfall analysis
- `/home/agent/.planning/phases/01-l1-screenshot-actor/01-CONTEXT.md` — locked decisions, UX flow

### Secondary (MEDIUM confidence)
- SUMMARY.md secondary sources: ZenRows CF bypass 2026, Playwright screenshot timing GitHub issues #620 and #19861

### Tertiary (LOW confidence)
- openclaw-fresh tool dispatch mechanism: inferred from container mount config + exec permissions; NOT directly verified from source — must confirm during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all services verified from live codebase with port/API confirmation
- Architecture: HIGH — browser session pattern verified line-by-line from web_search_resilience.py
- Classifier extension: HIGH — existing 3-class function read directly; 2 new classes have clear detection rules
- Tool dispatch mechanism: LOW — openclaw-fresh tool invocation not directly verified; see Open Questions #1 and #2
- Pitfalls: MEDIUM-HIGH — session leaks and bypass contention from direct code analysis (HIGH); CF soft-challenge mis-classification from multiple external sources (MEDIUM)

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable infra stack; CF bypass effectiveness may change sooner)
