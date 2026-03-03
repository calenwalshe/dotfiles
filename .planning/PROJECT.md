# URL Screenshot & Perception System

## What This Is

A two-layer system that turns any URL into a classified screenshot, delivered through the existing openclaw-fresh Telegram/browser UI. L1 is the screenshot actor — it navigates to URLs using Playwright, handles Cloudflare challenges and other blocks, and returns rendered screenshots. L2 is a perception harness that classifies each screenshot (real content / challenge page / blank / degraded), tracks failure patterns over time, and alerts the operator when new failure classes emerge.

## Core Value

Given any URL, return a screenshot with an honest classification of what was captured — never silently return garbage.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can request a screenshot of any URL via Telegram (natural language or `/screenshot <url>`)
- [ ] L1 navigates to URL using Playwright in openclaw-fresh, captures full-page screenshot
- [ ] L1 detects Cloudflare challenges and other blocks, reports status to user ("CF detected, attempting bypass...")
- [ ] L1 attempts bypass strategies automatically when a challenge is detected
- [ ] Screenshot is returned to user in Telegram chat with L2 perception classification
- [ ] L2 classifies screenshots into categories: PASS_CONTENT, BLOCKED_CHALLENGE, BLANK_PAGE, DEGRADED_CONTENT
- [ ] L2 perception harness runs on a scheduled basis against a curated URL test list
- [ ] URLs that fail in user requests are auto-added to the harness test suite
- [ ] Failure patterns are logged with URL, failure class, timestamp, and screenshot artifact
- [ ] New failure patterns trigger a Telegram alert to the operator ("New failure pattern on X — want me to investigate?")
- [ ] Harness results and artifacts are stored in the existing master_harness infrastructure

### Out of Scope

- Auto-investigation dev loop (L2 auto-researches failures and proposes fixes) — v2, after v1 harness proves the failure tracking works
- PDF rendering or non-web-page content — URL must be a web page
- Video or dynamic content capture — static screenshot only
- Public API exposure — this is an internal capability, not a service for external users

## Context

- **openclaw-fresh** already has Playwright browser infrastructure used for web search, page browsing, and CF bypass attempts
- The `web_search_resilience` harness suite already tests browser perception for Python docs, OpenAI docs, and Discogs (just added)
- The `_run_browser_perception_test` function in `web_search_resilience.py` handles the full loop: search → browse → classify → CF bypass fallback → artifacts
- CF bypass is the known hard problem — Discogs (Cloudflare-protected) was the motivating case
- The master_harness framework in `openclaw-scheduler` provides test infrastructure: suites, runners, storage, reporting, Telegram alerts
- All communication goes through the existing Telegram/browser UI pathway — no new services needed
- The `STABLE_DOMAIN_HINTS` dict and perception queries list are the extension points for adding test cases

## Constraints

- **Infrastructure**: Must use existing openclaw-fresh Playwright browser, no new containers or services
- **Communication**: Must go through existing Telegram/browser UI pathway (openclaw-fresh agent)
- **Storage**: Harness artifacts use existing `harness-artifacts/` structure in openclaw-scheduler
- **Deployment**: All local on agent-stack machine — edit files, restart containers

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| L1 lives in openclaw-fresh, not a separate service | Reuses existing Playwright + Telegram pipeline, no new infrastructure | — Pending |
| L2 extends master_harness, not a standalone system | Leverages existing test infrastructure, storage, reporting | — Pending |
| Failed user URLs auto-join harness test suite | Test surface grows organically from real usage, catches regressions | — Pending |
| v1 excludes auto-investigation dev loop | Ship tracking first, prove the failure classification works, then automate investigation | — Pending |

---
*Last updated: 2026-03-03 after initialization*
