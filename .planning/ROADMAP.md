# Roadmap: URL Screenshot & Perception System

## Overview

Three phases build the system in strict dependency order. Phase 1 delivers the L1 screenshot actor — a working Telegram command that captures any URL and returns a classified screenshot. Phase 2 delivers the L2 perception harness — a scheduled suite that continuously monitors a URL catalog and stores artifacts. Phase 3 delivers the operator workflow — tuned alerts, bypass health metrics, and staging queue management. Each phase is independently testable and produces real output before the next phase begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: L1 Screenshot Actor** - Telegram command captures any URL, classifies the result, returns screenshot to user
- [ ] **Phase 2: L2 Perception Harness** - Scheduled suite monitors URL catalog, stores classified artifacts, feeds reporter
- [ ] **Phase 3: Alerting and Operator Workflow** - Tuned failure alerts, bypass health metric, staging queue promotion

## Phase Details

### Phase 1: L1 Screenshot Actor
**Goal**: Users can request a screenshot of any URL via Telegram and receive a classified screenshot in return
**Depends on**: Nothing (first phase)
**Requirements**: CAPT-01, CLSF-01, CLSF-02, CLSF-03, CLSF-04, INFR-01
**Success Criteria** (what must be TRUE):
  1. User sends `/screenshot <url>` (or natural language equivalent) and receives a screenshot image in Telegram within the timeout window
  2. Every screenshot response includes a classification label (PASS_CONTENT, BLOCKED_CHALLENGE, BLANK_PAGE, DEGRADED_CONTENT, or SOFT_BLOCK) and a confidence score
  3. When a Cloudflare challenge is detected, the actor attempts CF bypass and reports the outcome — never silently returns a challenge page labeled as PASS_CONTENT
  4. A failed user URL is written to the staging queue in site_test_catalog; it does not appear in scheduled harness runs until promoted
  5. Concurrent screenshot requests and harness runs do not exhaust the CF bypass worker (semaphore enforced)
**Plans**: TBD

### Phase 2: L2 Perception Harness
**Goal**: The system autonomously monitors a URL catalog on a schedule, storing classified screenshots and artifacts for every run
**Depends on**: Phase 1
**Requirements**: INFR-03
**Success Criteria** (what must be TRUE):
  1. The `url_screenshot` harness suite runs on the configured schedule and processes every active URL in site_test_catalog
  2. Each run produces a stored artifact: PNG on filesystem and metadata (URL, timestamp, classification, confidence) in JSONL; artifacts older than the pruning window are removed automatically
  3. The harness suite is visible in the existing master_harness registry and its runs appear in harness result storage alongside existing suites
**Plans**: TBD

### Phase 3: Alerting and Operator Workflow
**Goal**: The operator receives actionable alerts when failure patterns change, can review bypass health, and can promote URLs from staging to the active test suite
**Depends on**: Phase 2
**Requirements**: INFR-02
**Success Criteria** (what must be TRUE):
  1. When a previously-passing URL starts failing, the operator receives a Telegram alert with the URL, new failure class, and how many consecutive failures have occurred
  2. A daily or per-run bypass health digest shows the CF bypass success rate over the last 24 hours — a rate below threshold triggers an alert without requiring manual inspection
  3. The operator can list staging queue entries and promote a URL to the active test suite via Telegram command, without editing any config files
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. L1 Screenshot Actor | 0/TBD | Not started | - |
| 2. L2 Perception Harness | 0/TBD | Not started | - |
| 3. Alerting and Operator Workflow | 0/TBD | Not started | - |
