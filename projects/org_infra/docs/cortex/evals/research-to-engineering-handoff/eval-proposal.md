# Eval Proposal — research-to-engineering-handoff

**Slug:** research-to-engineering-handoff  
**Contract:** docs/cortex/contracts/research-to-engineering-handoff/contract-001.md  
**Timestamp:** 20260401T000000Z  
**Approval Status:** approved  
**approval_required:** true

---

## Scope

This proposal covers evaluation strategy for a seven-agent pre-production intelligence system built on LangGraph. The system takes a natural language product problem statement as input and produces a structured, schema-validated handoff package for downstream engineering consumption. Deliverables include: `handoff-package-schema.json`, 7 agent implementations, a LangGraph state machine, shared artifact store, PM stakeholder comms interface, eval framework, and a first end-to-end run.

---

## Dimension Decisions

### 1. Functional Correctness — INCLUDE
`approval_required: false`

The output is mechanically verifiable. Every done criterion in the contract maps to a deterministic assertion:
- Handoff package conforms to schema → `pytest tests/test_schema_validation.py`
- All 7 agents produce typed artifacts → `pytest tests/test_agent_contracts.py`
- Orchestrator gate decisions cite agent artifacts → `pytest tests/test_graph_routing.py`
- Pressure Testing produces named objections, not rubber-stamps → `pytest tests/test_pressure_testing_non_trivial.py`
- System resumes from checkpoint → `pytest tests/test_checkpoint_resume.py`
- Full smoke test on synthetic input → `pytest tests/test_e2e_synthetic.py`
- Eval framework audit trail → `pytest tests/test_eval_audit.py`

These are the contract's explicit validators and are sufficient to establish functional coverage.

**Fixtures:** Synthetic product problem statement (bounded scope, no real stakeholders), stub Slack adapter, canned artifact store responses for gate logic tests.

**Pass threshold:** All contract validators green. Zero schema validation failures. Pressure Testing test must confirm at least 1 named objection per claim category.

---

### 2. Regression — EXCLUDE

This is a greenfield implementation. No existing code, data schema, or documented behavior is being modified. No regression risk.

---

### 3. Integration — INCLUDE
`approval_required: false`

Multiple components interact with external boundaries:
- **LangGraph ↔ artifact store** — agents write artifacts; Orchestrator reads by reference across phase transitions
- **PM agent ↔ Slack/comms platform** — async send + response polling; the only external write path in the system
- **Feedback Synthesis agent ↔ PM comms interface** — reads stakeholder responses from the same channel PM writes to
- **Assembler ↔ all 7 agent artifact outputs** — aggregates typed artifacts into final package; schema mismatch is a silent failure mode
- **LangGraph ↔ HITL checkpoints** — interruption/resume path must persist state correctly across the pause

**Fixtures:** Mock Slack adapter that records outbound messages and returns canned stakeholder responses. Pre-populated artifact store with per-agent fixture outputs. LangGraph interrupt/resume test uses serialized state checkpoint from mid-run.

**Pass threshold:** PM agent completes one full send/receive/synthesize cycle with mock adapter. Assembler produces a valid schema-conformant package from fixture artifacts. Checkpoint resume test restores correct phase state.

---

### 4. Safety / Security — INCLUDE
`approval_required: false`

Two risk surfaces:
- **PM agent comms** — the agent sends messages to real stakeholders on external platforms. A prompt injection or hallucination in the PM agent's output could send malformed or sensitive content to real people. Mitigation: PM agent output must pass a content schema check before the comms adapter sends it.
- **Secrets management** — Slack API key, Meta internal data access tokens, LangSmith keys. These must not be logged or leaked into artifact store outputs or LangGraph state.

**Fixtures:** Comms adapter test: feed PM agent a prompt designed to inject a forbidden content pattern; assert the schema check blocks transmission. Secrets test: run a full synthetic pipeline; scan all artifact store files and LangGraph state snapshots for known key patterns.

**Pass threshold:** PM agent content schema check blocks malformed output. No secrets present in any artifact store file or serialized state snapshot after a full synthetic run.

---

### 5. Performance — EXCLUDE

The contract specifies no explicit latency, throughput, or resource usage thresholds. The spec mentions token cost as a known risk with a mitigation strategy (model tiering, per-run token budgets), but no numeric SLA is established in the contract's done criteria or validators. Including a performance eval now would require inventing thresholds not derived from the contract — that's premature.

When the first real run completes and token cost data exists, revisit this dimension with actual numbers.

---

### 6. Resilience — INCLUDE
`approval_required: false`

"System resumes correctly from checkpoint when interrupted mid-run" is an explicit done criterion. The system has three external dependency failure modes worth testing:
- LangGraph checkpoint interrupted mid-phase → resume restores correct agent state and phase position
- Slack API unavailable → PM agent falls back gracefully (does not crash the graph; marks comms step as pending)
- Artifact store write failure mid-phase → Orchestrator detects incomplete artifact set at gate; does not advance phase

**Fixtures:** LangGraph test: serialize state at each phase gate; deserialize and resume; verify correct next-node routing. Slack failure test: mock adapter raises `ConnectionError`; verify graph transitions to a `comms_pending` state rather than raising. Artifact store: inject write failure; verify Orchestrator blocks at gate.

**Pass threshold:** Checkpoint resume test passes at all 4 phase gates. Slack outage test produces a `comms_pending` state, not an exception. Artifact store failure test produces a gate block, not a corrupted phase advance.

---

### 7. Style — INCLUDE
`approval_required: false`

All code deliverables (`src/`, `tests/`) and documentation deliverables (`docs/agent-contracts.md`, `runs/run-001/debrief.md`) are in scope.

**Code style checks:**
- `ruff` for lint and import order
- `black` for formatting
- No debug statements (`print()`, `pdb`, `breakpoint()`) in production paths

**Documentation checks:**
- `agent-contracts.md` must define input schema, output schema, tool access, and evaluation rubric for all 7 agents — missing any one of these for any agent is a style failure
- `debrief.md` must contain a structured format (what worked, what broke, what to iterate) — free-form prose without structure fails

**Pass threshold:** `ruff` and `black` clean. No debug statements. `agent-contracts.md` checklist passes for all 7 agents. Debrief has required structure.

---

### 8. UX / Taste — INCLUDE
`approval_required: true`

The handoff package is the primary user-facing output — it is read by an engineering consumer who must confirm it is "actionable without additional discovery work." This is a taste judgment, not a mechanical check. It cannot be automated.

**What requires human approval:**
- **Handoff package quality on first real run** — does the package actually enable engineering to begin without further discovery? An engineering consumer must read it and confirm. One consumer sign-off minimum.
- **Pressure Testing agent output quality** — are the objections adversarial and specific, or generic and rubber-stamp? A human reviewer (not just the test) must read the first real run's pressure test report and confirm it challenged the pitch substantively.
- **Feedback Synthesis agent output quality** — does the conflict/alignment report surface genuinely meaningful divergence, or surface-level phrasing differences? Human spot-check required on first real run.

**Approval protocol:**
1. First real run artifacts land in `runs/run-001/`
2. One engineering consumer reviews the handoff package and records sign-off in `runs/run-001/debrief.md`
3. Pressure Testing and Feedback Synthesis outputs reviewed by research lead and recorded in the same debrief
4. `Approval Status: approved` recorded in this document when all three reviews are complete

---

## Summary

| Dimension | Decision | approval_required |
|-----------|----------|-------------------|
| Functional correctness | INCLUDE | false |
| Regression | EXCLUDE | — |
| Integration | INCLUDE | false |
| Safety/security | INCLUDE | false |
| Performance | EXCLUDE | — |
| Resilience | INCLUDE | false |
| Style | INCLUDE | false |
| UX/taste | INCLUDE | true |

**Document-level approval_required: true** (UX/taste requires human sign-off on first real run outputs before this eval proposal is considered satisfied)

---

## Approval Instructions

To approve this proposal:
1. Review all INCLUDE decisions above — if any dimension should be added or removed, revise the proposal first.
2. Edit this file: change `Approval Status: pending` → `Approval Status: approved`
3. Re-run `/cortex-research --write-plan` to write `eval-plan.md`
