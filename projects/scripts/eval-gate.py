#!/usr/bin/env python3
"""
Eval gate: compare current.json scores against baseline.json thresholds.
Exits 1 if any metric fails (used as CI gate).
"""
import json
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
baseline_path = repo_root / "evals" / "baseline.json"
current_path = repo_root / "evals" / "current.json"

if not baseline_path.exists():
    print(f"ERROR: baseline.json not found at {baseline_path}")
    sys.exit(1)

if not current_path.exists():
    print(f"ERROR: current.json not found at {current_path}")
    print("Run pytest tests/evals/test_ci_gate.py first to generate current.json")
    sys.exit(1)

with open(baseline_path) as f:
    baseline = json.load(f)

with open(current_path) as f:
    current = json.load(f)

fail = False

for metric, cfg in baseline["thresholds"].items():
    if metric not in current["scores"]:
        print(f"ERROR: metric '{metric}' missing from current.json")
        fail = True
        continue

    score = current["scores"][metric]
    b = baseline["scores"][metric]
    min_absolute = cfg["min_absolute"]
    max_delta = cfg["max_delta"]

    if score < min_absolute:
        print(f"FAIL [{metric}]: {score:.3f} below floor {min_absolute:.3f}")
        fail = True
    elif score < b - max_delta:
        print(f"FAIL [{metric}]: {score:.3f} dropped {b - score:.3f} from baseline {b:.3f} (max_delta={max_delta})")
        fail = True
    else:
        print(f"PASS [{metric}]: {score:.3f} (baseline={b:.3f}, floor={min_absolute:.3f}, delta_allowed={max_delta:.3f})")

sys.exit(1 if fail else 0)
