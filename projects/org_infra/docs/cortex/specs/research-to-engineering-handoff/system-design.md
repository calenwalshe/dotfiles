# The System — Autonomous R&D Platform

**Status:** design (pending Phase 0 validation)  
**Date:** 2026-04-02  
**Revision:** 2 — restructured for composability

---

## Design Principle: Protocol, Not Plumbing

Every component communicates through **typed artifacts in a shared store**. No component calls another directly. No component knows the internals of any other. Each one reads what it needs, writes what it produces, and can be replaced without touching anything else.

The architectural metaphor is Unix pipes, not microservices. Components are small, single-purpose, and composable. The "pipe" is the artifact store.

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Component│     │ Component│     │ Component│     │ Component│
│    A     │────▶│    B     │────▶│    C     │────▶│    D     │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
      │                │                │                │
      ▼                ▼                ▼                ▼
 ═══════════════════════════════════════════════════════════════
                    ARTIFACT STORE
            (typed records, shared state)
 ═══════════════════════════════════════════════════════════════
```

**The rule:** If you can't describe what a component reads and writes without mentioning another component's name, the interface is wrong.

---

## The Six Protocols

These are the interfaces. Everything else is implementation detail.

### Protocol 1: Claim

The atomic unit of knowledge. Everything the system knows is a claim.

```yaml
Claim:
  id: uuid
  text: string                    # human-readable assertion
  level: L0 | L1 | L2 | L3       # raw → extracted → validated → actionable
  confidence: float (0.0–1.0)
  domain: string                  # codebase | product | competitive | user | operational
  topic: string                   # free-text tag for grouping
  entity: string | null           # if this claim is about a specific thing/person
  source_type: file | url | commit | conversation | experiment
  source_ref: string              # path, URL, SHA, session ID
  valid_from: datetime
  valid_until: datetime | null    # null = still valid
  created_at: datetime
  promoted_at: datetime | null
```

**Any component can write claims.** Perception agents write L0. Consolidation promotes L0→L1→L2→L3. Execution engines write experiment-derived claims. The loop controller reads claims to discover problems. No component needs to know who wrote a claim — only what level it's at and how confident it is.

### Protocol 2: Evidence

Links to claims. Supports, contradicts, or is neutral.

```yaml
Evidence:
  id: uuid
  claim_id: uuid (FK)
  content: string
  strength: supports | contradicts | neutral
  source_type: file | url | commit | conversation | experiment
  source_ref: string
  timestamp: datetime
```

### Protocol 3: Decision

A choice made by any component, with full reasoning.

```yaml
Decision:
  id: uuid
  topic: string
  chosen_option: string
  reasoning: string               # why this, not that
  alternatives_rejected:          # array of {option, reason}
    - option: string
      reason: string
  evidence_ids: [uuid]            # what evidence informed this
  confidence: float
  timestamp: datetime
  outcome: string | null          # filled in post-hoc if evaluated
```

### Protocol 4: Experiment

A hypothesis tested empirically. Written by any execution engine.

```yaml
Experiment:
  id: uuid
  hypothesis: string
  method: string
  inputs: json
  outputs: json
  metric_name: string
  metric_value: float
  baseline_value: float
  kept: bool
  commit_sha: string | null
  duration_seconds: float
  timestamp: datetime
```

### Protocol 5: Problem

A discovered issue worth investigating. Written by any discovery source.

```yaml
Problem:
  id: uuid
  description: string
  source_claim_ids: [uuid]        # what claims led to this problem
  impact: float (0.0–1.0)
  confidence: float (0.0–1.0)
  actionability: float (0.0–1.0)
  score: float                    # impact × confidence × actionability
  classification: open-ended | bounded | hybrid | unclassified
  status: discovered | approved | in-progress | completed | rejected
  timestamp: datetime
```

### Protocol 6: Artifact

Any file or document produced by a component. The generic output type.

```yaml
Artifact:
  id: uuid
  type: string                    # spec | contract | handoff-package | report | projection
  path: string                    # where it lives on disk
  produced_by: string             # component name
  timestamp: datetime
  metadata: json                  # component-specific data
```

---

## The Components (independently replaceable)

Each component is defined only by what protocols it reads and writes. Internals are its own business.

### Store

**What it is:** The shared state layer. Currently: Postgres + pgvector. Could be: SQLite + LanceDB. Could be: flat Markdown files with YAML frontmatter. The store is an adapter — swap the backend without changing any component.

```
READS:  nothing (it IS the state)
WRITES: nothing (it IS the state)

EXPOSES:
  write_claim(Claim) → uuid
  write_evidence(Evidence) → uuid
  write_decision(Decision) → uuid
  write_experiment(Experiment) → uuid
  write_problem(Problem) → uuid
  write_artifact(Artifact) → uuid
  
  query_claims(filters) → [Claim]
  query_evidence(claim_id) → [Evidence]
  query_decisions(filters) → [Decision]
  query_experiments(filters) → [Experiment]
  query_problems(filters) → [Problem]
  
  search_semantic(text, top_k) → [Claim | Evidence]
  search_lexical(text, top_k) → [Claim | Evidence]
  
  validate_recall(Claim) → ValidatedClaim | RejectedClaim
    # the retrieval-as-proposal gate lives HERE, in the store,
    # not in any component. Every read goes through it.
```

**Why this matters:** You can start with SQLite and flat files (Phase 1). Migrate to Postgres when you need it (Phase 3). Add pgvector when semantic search matters. Add a graph projection when relational queries demand it. Every migration is a store adapter swap. Zero component changes.

### Perceiver (pluggable, N instances)

**What it is:** Anything that ingests external data and writes L0 claims. Each perceiver is a standalone script or scheduled agent.

```
READS:  external data source (git, Slack, web, experiment platform, etc.)
WRITES: Claim (level=L0), Evidence
```

**Perceivers are plugins.** Each one is a single file/script with one job:
- `perceiver-codebase.py` — reads git log, test coverage, lint output → writes L0 claims
- `perceiver-competitive.py` — runs Power Search on tracked topics → writes L0 claims
- `perceiver-comms.py` — reads Telegram/Slack via OpenClaw → writes L0 claims
- `perceiver-experiments.py` — reads experiment platform results → writes L0 claims

**To add a new data source:** Write a new perceiver that calls `store.write_claim()`. Done. No other component changes. No configuration. No wiring.

**To test a perceiver:** Run it in isolation, check it produces valid Claims. No other component needed.

### Consolidator

**What it is:** The sleep-time compute agent. Runs between sessions. Promotes, compresses, detects contradictions, decays stale facts, regenerates projections.

```
READS:  Claim (all levels), Evidence
WRITES: Claim (promoted), Contradiction, Artifact (markdown projections)
```

**Independently improvable:** You can tune promotion thresholds, add new contradiction detection heuristics, change compression ratios — all without touching any other component. The consolidator only talks to the store.

**To test:** Load the store with synthetic claims at various levels. Run consolidator. Assert promotions and contradictions are correct.

### Discoverer

**What it is:** Queries the store for problems worth solving. Produces a ranked problem list.

```
READS:  Claim (L2/L3 tagged "problem" or "risk"), Contradiction, Experiment (negative outcomes)
WRITES: Problem
```

**Independently improvable:** Better scoring algorithms, different ranking strategies, domain-specific filters — all local changes. To test: load store with known claims, assert correct problems surface.

### Classifier

**What it is:** Takes a Problem, determines execution mode. Pure function.

```
READS:  Problem
WRITES: Problem (with classification field set: open-ended | bounded | hybrid)
```

**The four questions:**
1. Has clear metric? (yes/no)
2. Constrained to ≤3 files? (yes/no)
3. Auto-evaluable? (yes/no)
4. Safely revertible? (yes/no)

All yes → bounded. Any no → open-ended. Mix → hybrid.

**Independently improvable.** Start with rule-based (the four questions). Replace with LLM-as-judge. Replace with a trained classifier. The interface doesn't change.

**To test:** Feed it 20 known problems with known correct classifications. Assert accuracy.

### Executor (pluggable, N types)

**What it is:** Takes an approved Problem and produces results. Multiple executor types, selected by classification.

```
READS:  Problem (approved, classified)
WRITES: Experiment, Claim, Decision, Artifact
```

**Executor types are plugins:**

```
executor-ratchet     (bounded problems)
├── Reads: Problem + relevant Claims from store
├── Runs: edit → test → eval → keep/revert loop
├── Writes: Experiment per attempt, Claim for findings
└── Config: write-root scope, metric name, timeout, budget ceiling

executor-pipeline    (open-ended problems)
├── Reads: Problem + relevant Claims from store
├── Runs: 7-agent handoff → Cortex spec → GSD execution
├── Writes: Artifact (handoff package, spec, contract), Decision, Claim
└── Config: HITL gate settings, model tier, phase definitions

executor-quick       (trivial problems)
├── Reads: Problem + relevant Claims from store
├── Runs: single Claude Code session, atomic commit
├── Writes: Experiment, Claim
└── Config: max tokens, write-root scope
```

**To add a new execution strategy:** Write a new executor that reads Problems and writes Experiments/Claims/Decisions. Register it with the classifier's routing table. No other component changes.

**To test an executor:** Feed it a synthetic Problem, assert it produces valid Experiments and Claims. No store needed (mock it).

### Evaluator

**What it is:** Scores execution output. Determines keep/revert.

```
READS:  Experiment, Artifact, Claim (produced by executor)
WRITES: Decision (keep/revert with reasoning), Claim (evaluation findings)
```

**Independently improvable:** Add new eval dimensions, change scoring rubrics, swap LLM-as-judge models — all local. The evaluator only reads experiments/artifacts and writes decisions.

**To test:** Feed it known good and bad experiment outputs. Assert correct keep/revert decisions.

### Graduator

**What it is:** Takes evaluation results and writes durable knowledge back to the store.

```
READS:  Decision (from evaluator), Experiment, Claim (from executor)
WRITES: Claim (L1, tagged for promotion), Evidence (linking results to claims)
```

**What it does:**
- Positive results → L1 claim: "Approach X improved metric Y by Z%"
- Negative results → L1 claim: "Approach X did not improve metric Y" (tagged negative)
- New questions → L0 claim: "During execution, discovered that Z is also a problem"
- Agent learnings → agent_memory update

**To test:** Feed it known decisions and experiments. Assert correct claims are produced at correct levels.

### Projector

**What it is:** Generates human-readable Markdown from the store. Runs after consolidation.

```
READS:  Claim (L3), Decision, Experiment, Contradiction
WRITES: Artifact (MEMORY.md, decision-journal.md, daily-logs/, knowledge-bank/)
```

**Independently improvable:** Change Markdown format, add new projection types (e.g., weekly digest), change what gets included — all local to this component.

---

## How Components Compose

The components don't know about each other. They compose through the store:

```
Perceiver ──writes──▶ Claims (L0)
                          │
Consolidator ──reads──────┘──writes──▶ Claims (L1, L2, L3)
                                           │
Discoverer ──reads─────────────────────────┘──writes──▶ Problems
                                                            │
Classifier ──reads──────────────────────────────────────────┘──writes──▶ Problems (classified)
                                                                             │
Executor ──reads─────────────────────────────────────────────────────────────┘──writes──▶ Experiments, Claims, Decisions
                                                                                              │
Evaluator ──reads─────────────────────────────────────────────────────────────────────────────┘──writes──▶ Decisions (keep/revert)
                                                                                                              │
Graduator ──reads─────────────────────────────────────────────────────────────────────────────────────────────┘──writes──▶ Claims (L1)
                                                                                                                              │
                                                                                                              (back to Consolidator)
```

**Any component can be:**
- Run independently (`python perceiver-codebase.py`)
- Tested in isolation (mock the store)
- Replaced with a different implementation (same read/write interface)
- Run on a different schedule (cron, on-demand, event-triggered)
- Skipped entirely (system still works, just without that capability)

**The loop controller is NOT a component.** It's a thin script that triggers components in sequence:

```bash
# The entire loop controller:
python discoverer.py          # writes Problems
python classifier.py          # classifies Problems
# human approves (or auto-approves if gate is removed)
python executor-ratchet.py    # or executor-pipeline.py, based on classification
python evaluator.py           # scores results
python graduator.py           # writes knowledge back
```

You could run this as a cron job. Or a Claude Code `/schedule`. Or manually. Or replace it with a LangGraph state machine. The components don't care what triggers them.

---

## Independence Matrix

Can this component be improved without touching others?

| Component | Improve independently? | Test independently? | Replace entirely? | Skip entirely? |
|---|---|---|---|---|
| **Store** | Yes (swap backend) | Yes (unit tests on API) | Yes (SQLite → Postgres → whatever) | No (everything needs it) |
| **Perceiver** (any) | Yes (add sources, change extraction) | Yes (mock store) | Yes (write new perceiver) | Yes (system works without that data source) |
| **Consolidator** | Yes (tune thresholds, add heuristics) | Yes (synthetic claims → assert promotions) | Yes (different promotion strategy) | Yes (claims stay at L0/L1, no promotion) |
| **Discoverer** | Yes (better scoring, domain filters) | Yes (known claims → assert problems) | Yes (different discovery strategy) | Yes (human picks problems manually) |
| **Classifier** | Yes (rules → LLM → trained model) | Yes (known problems → assert modes) | Yes (different classification strategy) | Yes (human classifies manually) |
| **Executor** (any) | Yes (different execution strategy) | Yes (synthetic problem → assert outputs) | Yes (write new executor type) | No (at least one needed) |
| **Evaluator** | Yes (add dimensions, change rubrics) | Yes (known outputs → assert scores) | Yes (different eval strategy) | Yes (keep everything, no quality gate) |
| **Graduator** | Yes (change what gets written back) | Yes (known decisions → assert claims) | Yes (different knowledge capture) | Yes (results don't feed back to memory) |
| **Projector** | Yes (change Markdown format) | Yes (known store → assert output files) | Yes (different output format) | Yes (no human-readable views) |

**Every component except Store is optional.** You can run the system with just Store + one Perceiver + one Executor and it works. Everything else adds capability without changing what exists.

---

## Concrete Example: Improving One Component

Say the Classifier is too conservative — it routes everything to Mode A (full pipeline) when many problems are actually bounded.

**What you change:** `classifier.py` — tune the four-question heuristic, or replace it with an LLM call that evaluates the problem description.

**What you don't change:** Nothing. The Discoverer still writes Problems. The Executor still reads classified Problems. The Store interface is unchanged. No other component knows or cares that the Classifier got smarter.

**How you test:** Run `python -m pytest tests/test_classifier.py` with 20 known problems and assert correct classification. No other component involved.

**How you deploy:** Replace `classifier.py`. Next loop cycle uses the new one.

---

## Concrete Example: Adding a New Data Source

Say you want to ingest experiment results from an A/B testing platform.

**What you build:** `perceiver-ab-tests.py` — reads the platform API, writes L0 Claims like "Feature X showed +3% conversion in segment Y (p=0.02)".

**What you change in existing code:** Nothing.

**How you deploy:** Add `perceiver-ab-tests.py` to the cron schedule. Next consolidation cycle picks up its L0 claims and processes them.

---

## Concrete Example: Swapping the Store Backend

Say you outgrow SQLite and need Postgres.

**What you change:** The store adapter. Implement the same API (`write_claim`, `query_claims`, `search_semantic`, etc.) against Postgres + pgvector.

**What you don't change:** Every component. They all call `store.write_claim()` and `store.query_claims()`. They don't know or care what's behind those calls.

**How you test:** Run the full test suite. Every component test uses the store API. If they all pass with the new backend, the migration is done.

---

## What Gets Built, In Order (revised)

| Phase | What | Composability proof |
|---|---|---|
| **0** | Manual loop (existing tools) | Proves the cycle produces value |
| **1** | Store (SQLite + flat files) + Protocols (Claim/Evidence/Decision/Experiment/Problem/Artifact schemas) | Every future component is written against these schemas |
| **2** | 1 Perceiver (codebase) + Consolidator + Projector | Can run independently: `python perceiver-codebase.py && python consolidator.py && python projector.py` |
| **3** | Discoverer + Classifier | Test: known claims → correct problems → correct classification |
| **4** | Executor-ratchet (autoresearch mode) | Test: synthetic bounded problem → experiments → keep/revert |
| **5** | Evaluator + Graduator | Closes the loop: results feed back to store |
| **6** | Executor-pipeline (7-agent handoff, contract-001) | Adds open-ended capability. Ratchet still works independently. |
| **7** | More perceivers, gate removal, Postgres migration | Each one independent. Add when needed. |

**At every phase, everything built so far works independently.** Phase 2 is useful without Phase 3 (you get codebase awareness + Markdown projections). Phase 4 is useful without Phase 6 (you get bounded optimization). Nothing depends on the full system being complete.

---

## The Five Pressure-Test Queries (unchanged)

1. "What did we decide about X, and what evidence supported it?" → `store.query_decisions(topic='X')` + `store.query_evidence(decision.evidence_ids)`
2. "What was true about X last month?" → `store.query_claims(topic='X', valid_at='2026-03-02')`
3. "What does the system think it knows about Calen, and how confident is it?" → `store.query_claims(entity='Calen')`
4. "Which memories are stale because the source changed?" → `store.query_stale_claims()`
5. "Why did the agent recommend path A over path B?" → `store.query_decisions(topic='path choice')` → `alternatives_rejected`

All five queries resolve to store API calls. No component involved. Any component can answer them by calling the store.

---

## Cost Model (unchanged)

~$100/month at moderate usage. Each component's cost is independent and trackable.

---

## What Changed From v1

| v1 (monolith) | v2 (composable) |
|---|---|
| Components call each other | Components read/write the store |
| Loop controller is a complex orchestrator | Loop controller is a bash script that triggers components |
| Adding a data source requires wiring | Adding a data source = one new perceiver script |
| Changing the store requires touching components | Store is an adapter behind a fixed API |
| Full system required for any value | Each component independently useful |
| Testing requires the full stack | Each component testable with mock store |
| "The System" is one big thing | "The System" is a bag of small tools that share a protocol |
