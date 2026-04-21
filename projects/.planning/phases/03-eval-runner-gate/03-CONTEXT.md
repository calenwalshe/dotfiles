# Phase 3: Eval Runner and Gate — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Write pytest eval runner, eval-gate.py script, and commit initial baseline.json. This phase can run in parallel with Phase 2. Depends on Phoenix running (Phase 1) for the eval runner to submit results.

</domain>

<decisions>
## Implementation Decisions

- **Package:** `arize-phoenix-evals>=2` — separate pip package; there is NO `arize-phoenix[evals]` extra
- **CRITICAL — choices dict form:** `choices={"correct": 1.0, "incorrect": 0.0}` — the list form `choices=["correct", "incorrect"]` silently produces `Score.score=None` and `mean()=NaN`; the assertion always passes, masking all failures
- **Score column unwrap:** Each cell is `{"score": float, "label": str, "explanation": str}` — MUST `.apply(lambda x: x["score"] if isinstance(x, dict) else None).dropna()` before `.mean()`
- **Eval judge:** `gpt-4o-mini` via `LLM(provider="openai", model="gpt-4o-mini")` — requires `OPENAI_API_KEY`
- **Gate logic:** hybrid delta+absolute; fail if `score < min_absolute` OR `score < baseline - max_delta`; exit code 1 on any failure
- **Baseline schema:**
  ```json
  {
    "metadata": { "created_at": "...", "git_sha": "...", "model": "gpt-4o-mini", "eval_suite": "core-v1", "n_cases": 50 },
    "scores": { "correctness": 0.87 },
    "thresholds": { "correctness": { "min_absolute": 0.75, "max_delta": 0.05 } }
  }
  ```
- **Initial thresholds:** `min_absolute: 0.75, max_delta: 0.05` for first eval suite
- **current.json location:** `evals/current.json` — CI-generated, NOT committed to repo
- **baseline.json location:** `evals/baseline.json` — committed to repo; changes via PR

### Claude's Discretion

- Specific eval test cases for `test_ci_gate.py` (correctness questions for the initial suite)
- Whether to use `asyncio.run()` or `pytest-asyncio` for async eval runner
- NaN guard assertion (add `assert scores.dropna().count() == len(df)` to catch silent NaN regression)

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/experiment-control-plane/spec.md (§6 Dependencies, §8 Sequencing steps 8–9, §7 Risks)
- docs/cortex/specs/experiment-control-plane/gsd-handoff.md (Tasks 13–15)
- docs/cortex/contracts/experiment-control-plane/contract-001.md (Done Criteria 7–9)
- docs/cortex/research/experiment-control-plane/implementation-20260421T031706Z.md (Q2 Phoenix eval API, Q4 regression operationalization)

</canonical_refs>

<specifics>
## Specific Ideas

**Full CI pattern from implementation research:**
```python
# test_evals_ci.py
import pytest, pandas as pd, asyncio
from phoenix.evals import ClassificationEvaluator, async_evaluate_dataframe
from phoenix.evals.llm import LLM

@pytest.fixture(scope="module")
def eval_results():
    llm = LLM(provider="openai", model="gpt-4o-mini")
    evaluator = ClassificationEvaluator(
        name="correctness",
        prompt_template=CORRECTNESS_TEMPLATE,
        llm=llm,
        choices={"correct": 1.0, "incorrect": 0.0},  # MUST be dict
    )
    df = pd.DataFrame({"question": [...], "answer": [...]})
    return asyncio.run(async_evaluate_dataframe(dataframe=df, evaluators=[evaluator]))

def test_correctness_gate(eval_results):
    scores = eval_results["correctness_score"].apply(
        lambda x: x["score"] if isinstance(x, dict) else None
    ).dropna()
    assert scores.mean() >= 0.85
```

**Gate script pattern:**
```python
import json, sys
with open("evals/baseline.json") as f: baseline = json.load(f)
with open("evals/current.json") as f: current = json.load(f)
fail = False
for metric, cfg in baseline["thresholds"].items():
    score = current["scores"][metric]
    b = baseline["scores"][metric]
    if score < cfg["min_absolute"]:
        print(f"FAIL [{metric}]: {score:.3f} below floor {cfg['min_absolute']}")
        fail = True
    if score < b - cfg["max_delta"]:
        print(f"FAIL [{metric}]: dropped {b-score:.3f} from baseline {b:.3f}")
        fail = True
sys.exit(1 if fail else 0)
```

</specifics>

<deferred>
## Deferred Ideas

- claude-haiku-4-5 as eval judge (requires Phoenix-compatible Anthropic evaluator wrapper)
- Percentile-based regression detection (requires 20+ run history)
- Multiple eval metrics beyond correctness in initial suite

</deferred>

---

*Phase: 03-eval-runner-gate*
*Context gathered: 2026-04-21 via /cortex-bridge*
