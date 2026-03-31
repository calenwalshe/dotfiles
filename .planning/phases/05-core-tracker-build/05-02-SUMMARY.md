# Summary 05-02: Benchmark segment run and output validation

**Status:** COMPLETE
**Date:** 2026-03-31

## What Was Done

### Output Validation (20-second test segment)
- `validate_tracker_output.py` written and validated
- Test on 20-second segment output:
  - 2173 annotations, 200 unique frames (100% coverage)
  - All schema fields present
  - 29 jersey OCR detections (numbers 9, 13, 21, 71, etc.)

### Player Profile Note
- Profile for jersey #4 not built in 20s segment — player was not facing camera with visible jersey
- This is expected behavior; profile requires jersey #4 to be OCR-readable in first 30s
- Full-video run will encounter more front-torso frames and build the profile

### Gap-Merge Validated (synthetic data)
- Gap of 40 frames (<150 = <5s) between segments: correctly merged
- Gap of 199 frames (>150 = >5s) between segments: correctly preserved as two segments

## Files Written
- `/home/agent/validate_tracker_output.py`

## Acceptance Criteria Status
1. ✅ test_player_tracker.py: 21/21 tests PASS
2. ✅ player_tracker.py runs on test segment without crash
3. ✅ player_ids.json format validated (schema, coverage)
4. ✅ --test-frame black and blur: no exceptions
