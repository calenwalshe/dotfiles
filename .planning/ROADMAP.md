# Roadmap: URL Screenshot & Perception System + Player Continuity Tracker

## Overview

**Milestone v1.0 (complete):** URL Screenshot & Perception System — L1 screenshot actor, L2 perception harness, alerting and operator workflow.

**Milestone v2.0 (active):** Player Continuity Tracker — pre-processing ByteTrack + OSNet Re-ID pass over the full Veo followcam match video, persistent per-frame player ID annotations, and integration with the existing `clip_extractor.py` Gemini pipeline. Four phases build the system in strict dependency order.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): v1.0 milestone work (complete)
- Integer phases (4, 5, 6, 7): v2.0 milestone work (player continuity tracker)
- Decimal phases: Urgent insertions

- [x] **Phase 1: L1 Screenshot Actor** - Telegram command captures any URL, classifies the result, returns screenshot to user (complete 2026-03-10)
- [x] **Phase 2: L2 Perception Harness** - Scheduled suite monitors URL catalog, stores classified artifacts, feeds reporter (complete 2026-03-30)
- [x] **Phase 3: Alerting and Operator Workflow** - Tuned failure alerts, bypass health metric, staging queue promotion (complete 2026-03-30)
- [ ] **Phase 4: Environment Setup & Benchmark** - Install tracker stack, verify CPU inference, benchmark first 5 minutes
- [ ] **Phase 5: Core Tracker Build** - player_tracker.py with frame-streaming loop, player profile construction, annotation output
- [ ] **Phase 6: Full-Video Run & Post-Processing** - Full 71-minute tracking pass, tracklet gap-merge, validate player_ids.json
- [ ] **Phase 7: Integration & End-to-End Validation** - clip_extractor.py shim, 15-minute end-to-end test, eval plan execution

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
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Build screenshot_tool.py: full capture/classify/bypass pipeline (self-contained Python)
- [x] 01-02-PLAN.md — Wire tool into openclaw-fresh agent: Node.js bridge, intent routing, Telegram delivery, staging enrollment

### Phase 2: L2 Perception Harness
**Goal**: The system autonomously monitors a URL catalog on a schedule, storing classified screenshots and artifacts for every run
**Depends on**: Phase 1
**Requirements**: INFR-03
**Success Criteria** (what must be TRUE):
  1. The `url_screenshot` harness suite runs on the configured schedule and processes every active URL in site_test_catalog
  2. Each run produces a stored artifact: PNG on filesystem and metadata (URL, timestamp, classification, confidence) in JSONL; artifacts older than the pruning window are removed automatically
  3. The harness suite is visible in the existing master_harness registry and its runs appear in harness result storage alongside existing suites
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Build l2_perception harness suite: capture/classify/store pipeline, artifact management, drift detection, config wiring

### Phase 3: Alerting and Operator Workflow
**Goal**: The operator receives actionable alerts when failure patterns change, can review bypass health, and can promote URLs from staging to the active test suite
**Depends on**: Phase 2
**Requirements**: INFR-02
**Success Criteria** (what must be TRUE):
  1. When a previously-passing URL starts failing, the operator receives a Telegram alert with the URL, new failure class, and how many consecutive failures have occurred
  2. A daily or per-run bypass health digest shows the CF bypass success rate over the last 24 hours — a rate below threshold triggers an alert without requiring manual inspection
  3. The operator can list staging queue entries and promote a URL to the active test suite via Telegram command, without editing any config files
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Write failing test scaffolds for alerting module and promote_bridge (TDD RED phase)
- [x] 03-02-PLAN.md — Build l2_perception_alerting.py and wire into l2_perception.py and config.yaml (TDD GREEN)
- [x] 03-03-PLAN.md — Build promote_bridge.py and wire into workspace/TOOLS.md (staging queue promotion)

### Phase 4: Environment Setup & Benchmark
**Goal**: Tracker dependency stack installed and verified; first 5-minute benchmark run establishes CPU FPS, memory usage, and OSNet cosine similarity baseline
**Depends on**: Nothing (first phase of v2.0)
**Requirements**: None formalized
**Success Criteria** (what must be TRUE):
  1. `ultralytics`, `easyocr`, `torchreid`/ONNX installed in `claude-stack-env` and import without error
  2. `yolov8n.pt` and `osnet_ain_x1_0` weights download and run CPU inference successfully
  3. 5-minute benchmark on `standard-1920x1080-followcam.mp4` produces FPS measurement, peak RAM reading, and OSNet cosine similarity distribution
**Plans**: 1 plan

Plans:
- [ ] 04-01-PLAN.md — Install ultralytics/easyocr/torchreid, download weights, run 5-minute benchmark on veo footage

### Phase 5: Core Tracker Build
**Goal**: player_tracker.py exists, streams frames, builds a player profile from reference frames, and writes per-frame player ID annotations to player_ids.json
**Depends on**: Phase 4
**Requirements**: None formalized
**Success Criteria** (what must be TRUE):
  1. `player_tracker.py` runs on the benchmark segment without crash, producing `player_ids.json` with frame-level annotations
  2. Player profile is constructed from first 30 seconds of footage where jersey number is readable
  3. Per-frame output includes track_id, bbox, jersey_ocr result, and OSNet cosine similarity score
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md — Write player_tracker.py: frame-streaming loop (YOLOv8 → OSNet → EasyOCR → ByteTrack ID assignment)
- [ ] 05-02-PLAN.md — Implement player profile construction and per-frame annotation output to player_ids.json

### Phase 6: Full-Video Run & Post-Processing
**Goal**: Full 71-minute tracking pass completes within the ≤ 8h threshold; tracklet gap-merge eliminates spurious ID switches for sub-5s occlusions
**Depends on**: Phase 5
**Requirements**: None formalized
**Success Criteria** (what must be TRUE):
  1. Full tracking pass on `standard-1920x1080-followcam.mp4` completes in ≤ 8 hours wall-clock, CPU-only, without OOM or crash
  2. `player_ids.json` covers the full video duration with frame-level annotations
  3. Tracklet gap-merge post-processing eliminates ID switches for gaps < 5 seconds (verified on benchmark segment)
**Plans**: 1 plan

Plans:
- [ ] 06-01-PLAN.md — Run full-video tracking pass; implement and apply tracklet gap-merge; validate player_ids.json coverage

### Phase 7: Integration & End-to-End Validation
**Goal**: clip_extractor.py consumes tracker output; 15-minute end-to-end pipeline produces correctly attributed clips in ≥ 80% of cases; all eval plan dimensions pass
**Depends on**: Phase 6
**Requirements**: None formalized
**Success Criteria** (what must be TRUE):
  1. Integration shim in `clip_extractor.py` injects tracker frame ranges into Gemini prompt; clip extraction runs without manual intervention
  2. `clip_extractor.py` still runs correctly with no tracker output present (regression: baseline parity)
  3. 15-minute end-to-end test produces clips attributed to the correct player in ≥ 80% of cases (human review)
  4. All File API uploads deleted immediately after Gemini extraction (File API list returns empty)
  5. All 8 eval plan dimensions pass (see `docs/cortex/evals/player-continuity-tracking/eval-plan.md`)
**Plans**: 2 plans

Plans:
- [ ] 07-01-PLAN.md — Write clip_extractor.py integration shim; regression test with no tracker output
- [ ] 07-02-PLAN.md — Run 15-minute end-to-end test; execute eval plan; record results

## Progress

**Execution Order:**
v1.0 phases complete. v2.0 phases execute in order: 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. L1 Screenshot Actor | 2/2 | Complete | 2026-03-10 |
| 2. L2 Perception Harness | 1/1 | Complete | 2026-03-30 |
| 3. Alerting and Operator Workflow | 3/3 | Complete | 2026-03-30 |
| 4. Environment Setup & Benchmark | 0/1 | Not started | — |
| 5. Core Tracker Build | 0/2 | Not started | — |
| 6. Full-Video Run & Post-Processing | 0/1 | Not started | — |
| 7. Integration & End-to-End Validation | 0/2 | Not started | — |
