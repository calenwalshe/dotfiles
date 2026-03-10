# Requirements: URL Screenshot & Perception System

**Defined:** 2026-03-03
**Core Value:** Given any URL, return a screenshot with an honest classification of what was captured — never silently return garbage.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Screenshot Capture

- [x] **CAPT-01**: L1 captures full-page screenshot of any URL via Playwright browser-service

### Classification

- [x] **CLSF-01**: 5-class taxonomy implemented: PASS_CONTENT, BLOCKED_CHALLENGE, BLANK_PAGE, DEGRADED_CONTENT, SOFT_BLOCK
- [x] **CLSF-02**: Rule-based fast path classifies clear cases without LLM call
- [x] **CLSF-03**: Vision LLM fallback (Gemini 2.5 Flash) classifies ambiguous screenshots
- [x] **CLSF-04**: Confidence score (0.0–1.0) attached to each classification result

### Infrastructure

- [x] **INFR-01**: Concurrency guard (asyncio.Semaphore) on shared cf-bypass-worker prevents contention
- [ ] **INFR-02**: Bypass health metric tracks CF bypass success rate over time
- [ ] **INFR-03**: Screenshot artifacts stored with metadata (URL, timestamp, classification, confidence)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### User Interaction

- **UINX-01**: `/screenshot <url>` command trigger in Telegram
- **UINX-02**: Natural language screenshot requests ("show me discogs.com")
- **UINX-03**: CF bypass status reporting to user ("CF detected, attempting bypass...")

### Harness & Tracking

- **HARN-01**: `url_screenshot` harness suite with scheduled runs against site_test_catalog
- **HARN-02**: Failed user URLs enrolled to staging queue
- **HARN-03**: Operator promotion from staging to active test suite via Telegram
- **HARN-04**: Telegram alerts on new failure patterns with context

### Safety & Quality

- **SAFE-01**: SSRF validation blocks internal IPs, localhost, metadata endpoints
- **QUAL-01**: Ground-truth fixture set for validating classifier accuracy
- **QUAL-02**: Viewport options (mobile vs desktop rendering)
- **QUAL-03**: Consecutive failure escalation in alerts

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-investigation dev loop | v2+ — ship failure tracking first, prove classification works |
| PDF rendering | URL must be a web page |
| Video/dynamic content capture | Static screenshot only |
| Public API exposure | Internal capability, not external service |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAPT-01 | Phase 1 | Complete |
| CLSF-01 | Phase 1 | Complete |
| CLSF-02 | Phase 1 | Complete |
| CLSF-03 | Phase 1 | Complete |
| CLSF-04 | Phase 1 | Complete |
| INFR-01 | Phase 1 | Complete |
| INFR-02 | Phase 3 | Pending |
| INFR-03 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 — traceability populated after roadmap creation*
