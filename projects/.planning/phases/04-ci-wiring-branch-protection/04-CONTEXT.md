# Phase 4: CI Wiring and Branch Protection — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Write `.github/workflows/ci-evals.yml`, add GitHub Actions secrets, configure branch protection with `ci-evals` as required status check, and verify end-to-end: gate passes on good scores, blocks merge on degraded scores.

</domain>

<decisions>
## Implementation Decisions

- **Workflow trigger:** `on: pull_request` targeting the default branch
- **Job name:** `ci-evals` — this name must match exactly what is set in branch protection
- **Steps:** install deps (`pip install arize-phoenix-evals>=2 pandas pytest`), run eval suite (writes `evals/current.json`), run `python scripts/eval-gate.py` (exits 1 on failure → job fails)
- **Secrets required:** `OPENAI_API_KEY`, `PHOENIX_URL` (set to `http://144.202.81.218:6006`)
- **Branch protection:** Must be configured in GitHub repository Settings → Branches → Add rule → require status check `ci-evals` — a failing CI job does NOT block merge unless this is configured
- **UFW:** Port 6006 already open to `0.0.0.0/0` from Phase 1 — GitHub Actions runners can reach Phoenix

### Claude's Discretion

- Whether to cache pip dependencies in the workflow
- Python version pinning in the workflow
- Whether to upload `evals/current.json` as a workflow artifact for debugging

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/experiment-control-plane/spec.md (§8 Sequencing steps 10–11, §5 Interfaces)
- docs/cortex/specs/experiment-control-plane/gsd-handoff.md (Tasks 16–19)
- docs/cortex/contracts/experiment-control-plane/contract-001.md (Done Criteria 10–11)
- docs/cortex/research/experiment-control-plane/implementation-20260421T031706Z.md (Q4 regression operationalization)

</canonical_refs>

<specifics>
## Specific Ideas

**Workflow skeleton:**
```yaml
name: CI Evals
on:
  pull_request:
    branches: [main]
jobs:
  ci-evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install "arize-phoenix-evals>=2" pandas pytest
      - run: pytest tests/evals/test_ci_gate.py -v
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          PHOENIX_URL: ${{ vars.PHOENIX_URL }}
      - run: python scripts/eval-gate.py
```

**Branch protection verification steps:**
1. Open a PR with baseline scores → verify `ci-evals` job passes → verify PR is mergeable
2. Manually set scores below threshold in test → verify job fails → verify "Merge" button is blocked

**CRITICAL:** A red CI check alone does NOT block merge — branch protection must be configured.

</specifics>

<deferred>
## Deferred Ideas

- Caddy HTTPS proxy for Phoenix (makes `PHOENIX_URL` use HTTPS)
- UFW scoped to GitHub Actions IP ranges with automated refresh
- Uploading eval reports as PR comments

</deferred>

---

*Phase: 04-ci-wiring-branch-protection*
*Context gathered: 2026-04-21 via /cortex-bridge*
