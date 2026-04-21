---
phase: 04-ci-wiring-branch-protection
plan: "04-01"
subsystem: infra
tags: [github-actions, ci, pytest, arize-phoenix-evals, branch-protection]

# Dependency graph
requires:
  - phase: 03-eval-runner-and-gate
    provides: tests/evals/test_ci_gate.py and scripts/eval-gate.py that the workflow runs
provides:
  - .github/workflows/ci-evals.yml — PR gating workflow with job name ci-evals
  - .gitignore with evals/current.json exclusion
affects:
  - Any future phase opening PRs against main (must pass ci-evals)
  - Branch protection configuration (manual — repo must exist on GitHub first)

# Tech tracking
tech-stack:
  added: [github-actions, actions/checkout@v4, actions/setup-python@v5, actions/upload-artifact@v4]
  patterns:
    - CI eval gate via pytest + eval-gate.py exit code
    - OPENAI_API_KEY as secret, PHOENIX_URL as variable (not secret)
    - Upload evals/current.json as artifact on always() for debug visibility

key-files:
  created:
    - .github/workflows/ci-evals.yml
    - .gitignore
  modified: []

key-decisions:
  - "Remote repo calenwalshe/dotfiles does not exist on GitHub — secrets, variables, and branch protection require manual setup after repo creation"
  - "PHOENIX_URL uses public VPS IP http://144.202.81.218:6006 (not localhost) so GitHub Actions runners can reach Phoenix"
  - "evals/current.json added to .gitignore — CI-generated artifact, not for commit"

patterns-established:
  - "ci-evals job name must not change — it is the string registered in branch protection"

# Metrics
duration: 8min
completed: 2026-04-20
---

# Phase 4 Plan 01: GitHub Actions Workflow and Branch Protection Summary

**ci-evals.yml workflow written with exact job name ci-evals, pytest + eval-gate.py gate, artifact upload; secrets/branch protection require manual setup (remote repo does not yet exist on GitHub)**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-20T00:00:00Z
- **Completed:** 2026-04-20T00:08:00Z
- **Tasks:** 1 automated, 2 manual (documented below)
- **Files modified:** 2

## Accomplishments

- Created `.github/workflows/ci-evals.yml` with job name exactly `ci-evals`, triggering on `pull_request` targeting `main`
- Workflow installs `arize-phoenix-evals>=2 pandas pytest`, runs `pytest tests/evals/test_ci_gate.py -v`, then `python scripts/eval-gate.py`
- Uploads `evals/current.json` as artifact with `if: always()` for debug visibility even on failure
- Created `.gitignore` excluding `evals/current.json` (pending todo from 03-01)

## Task Commits

1. **Task 1: Create ci-evals workflow + .gitignore** - `abd3c08` (feat)
2. **Tasks 2-3: GitHub secrets, variables, branch protection** - MANUAL (documented below)

**Plan metadata:** (included in final commit with SUMMARY.md)

## Files Created/Modified

- `.github/workflows/ci-evals.yml` — CI workflow; job `ci-evals` runs pytest + eval-gate.py on PR to main
- `.gitignore` — excludes `evals/current.json`, `__pycache__/`, `.pytest_cache/`

## Decisions Made

- **Remote repo does not exist:** `calenwalshe/dotfiles` returns 404 from GitHub API. All GitHub API operations (secrets, variables, branch protection) require the repo to exist first. Manual steps documented below.
- **PHOENIX_URL uses public IP:** `http://144.202.81.218:6006` used in workflow (not localhost) so GitHub Actions runners on ubuntu-latest can reach Phoenix on the VPS. UFW port 6006 already open from Phase 1.
- **evals/current.json gitignored:** Added during this plan (was a pending todo from 03-01 STATE.md).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added evals/current.json to .gitignore**

- **Found during:** Task 1 (reviewing STATE.md pending todos)
- **Issue:** STATE.md had a pending todo to add evals/current.json to .gitignore; without it the CI artifact gets committed to the repo
- **Fix:** Created `.gitignore` with `evals/current.json` and standard Python exclusions
- **Files modified:** `.gitignore` (new file)
- **Verification:** File exists and contains the exclusion
- **Committed in:** abd3c08 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Gitignore necessary to prevent CI artifacts from polluting commit history. No scope creep.

## Issues Encountered

- **GitHub remote repo does not exist:** The git remote `origin` points to `https://github.com/calenwalshe/dotfiles.git` which returns 404. The `gh secret set`, `gh variable set`, and `gh api` branch protection calls all failed with "not found". This is not a `gh` auth issue — `gh` is authenticated as `calenwalshe` — the repo simply hasn't been created yet.

## Manual Steps Required

The following must be done **after the repo exists on GitHub** (either push creates it, or create it manually first):

### 1. Set OPENAI_API_KEY secret

```bash
gh secret set OPENAI_API_KEY --body "$OPENAI_API_KEY" --repo calenwalshe/dotfiles
```

Or via GitHub UI: Settings → Secrets and variables → Actions → New repository secret
- Name: `OPENAI_API_KEY`
- Value: (the key from the VPS environment)

### 2. Set PHOENIX_URL variable

```bash
gh variable set PHOENIX_URL --body "http://144.202.81.218:6006" --repo calenwalshe/dotfiles
```

Or via GitHub UI: Settings → Secrets and variables → Actions → Variables tab → New repository variable
- Name: `PHOENIX_URL`
- Value: `http://144.202.81.218:6006`

### 3. Configure branch protection on main

```bash
OWNER=calenwalshe
REPO_NAME=dotfiles

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${OWNER}/${REPO_NAME}/branches/main/protection" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": false,
    "contexts": ["ci-evals"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
EOF
```

Or via GitHub UI:
1. Go to: https://github.com/calenwalshe/dotfiles/settings/branches
2. Click "Add branch protection rule"
3. Branch name pattern: `main`
4. Check "Require status checks to pass before merging"
5. Search for and select: `ci-evals`
6. Click "Save changes"

**CRITICAL:** Without step 3, a red CI check does NOT block merge. Branch protection is what enforces the gate.

## Next Phase Readiness

- Workflow file committed and ready — will trigger on first PR to main once the repo exists on GitHub
- Secrets, variables, and branch protection require the repo to be created and pushed first
- Once manual steps are done, open a test PR to verify `ci-evals` appears as required status check

---
*Phase: 04-ci-wiring-branch-protection*
*Completed: 2026-04-20*
