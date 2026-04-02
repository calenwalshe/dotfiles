# Eval Plan — research-to-engineering-handoff

**Slug:** research-to-engineering-handoff  
**Contract:** docs/cortex/contracts/research-to-engineering-handoff/contract-001.md  
**Source proposal:** docs/cortex/evals/research-to-engineering-handoff/eval-proposal.md  
**Timestamp:** 20260401T000000Z  
**Status:** active

---

## Approved Dimensions

6 of 8 dimensions included. 2 excluded (Regression — greenfield; Performance — no SLA in contract).

---

## 1. Functional Correctness

**What:** Every contract done criterion maps to a deterministic test assertion.

**Test suite:**

| Test file | What it validates |
|-----------|-------------------|
| `tests/test_schema_validation.py` | Handoff package conforms to `handoff-package-schema.json` |
| `tests/test_agent_contracts.py` | All 7 agents produce typed artifacts matching their contract schemas |
| `tests/test_graph_routing.py` | Orchestrator gates all 4 phase transitions with citable decisions |
| `tests/test_pressure_testing_non_trivial.py` | Pressure Testing produces ≥1 named objection per claim category |
| `tests/test_checkpoint_resume.py` | System resumes from checkpoint at each phase gate |
| `tests/test_e2e_synthetic.py` | Full pipeline on synthetic input produces valid handoff package |
| `tests/test_eval_audit.py` | Eval framework produces auditable quality scores |

**Fixtures:**
- `tests/fixtures/synthetic_problem.json` — bounded product problem statement (no real stakeholders)
- `tests/fixtures/stub_slack_adapter.py` — records outbound messages, returns canned responses
- `tests/fixtures/canned_artifacts/` — pre-built per-agent artifacts for gate logic tests

**Pass criteria:**
- All 7 test files green
- Zero schema validation failures
- Pressure Testing confirms ≥1 named objection per claim category

**Run command:**
```bash
python -m pytest tests/test_schema_validation.py tests/test_agent_contracts.py tests/test_graph_routing.py tests/test_pressure_testing_non_trivial.py tests/test_checkpoint_resume.py tests/test_e2e_synthetic.py tests/test_eval_audit.py -v
```

---

## 2. Integration

**What:** Component boundaries work correctly when composed.

**Test cases:**

| Test | Components | What it validates |
|------|------------|-------------------|
| Artifact cross-phase | Agents → artifact store → Orchestrator | Agent writes artifact; Orchestrator reads by reference in next phase |
| PM comms cycle | PM agent → Slack adapter → Feedback Synthesis | PM sends, adapter records, canned response returned, Feedback Synthesis reads |
| Assembler aggregation | All 7 agent artifacts → Assembler | Assembler produces schema-conformant package from real agent outputs |
| HITL interrupt/resume | LangGraph → checkpoint → resume | State serialized at phase gate; deserialized; correct next-node routing |

**Fixtures:**
- Mock Slack adapter (records + replays)
- Pre-populated artifact store with per-agent fixture outputs
- Serialized LangGraph state checkpoint from mid-run

**Pass criteria:**
- PM agent completes one full send/receive/synthesize cycle with mock adapter
- Assembler produces valid package from fixture artifacts
- Checkpoint resume restores correct phase state and routes to correct next node

**Run command:**
```bash
python -m pytest tests/test_integration.py -v
```

---

## 3. Safety / Security

**What:** PM agent cannot send malformed content; secrets do not leak into artifacts or state.

**Test cases:**

| Test | What it validates |
|------|-------------------|
| Content schema gate | PM agent output passes content schema check before comms adapter sends |
| Prompt injection block | Feed PM agent adversarial prompt; assert schema check blocks transmission |
| Secrets scan | After full synthetic run, no API keys in artifact store files or serialized state |

**Fixtures:**
- Adversarial prompt payload targeting PM agent output injection
- Known key patterns for scan: Slack token (`xoxb-`), LangSmith key, OpenAI key prefixes

**Pass criteria:**
- Schema check blocks malformed PM output (does not reach comms adapter)
- Zero secrets found in artifact store or serialized state after synthetic run

**Run command:**
```bash
python -m pytest tests/test_safety.py -v
```

---

## 4. Resilience

**What:** System handles interruptions and external failures gracefully.

**Test cases:**

| Test | Failure mode | Expected behavior |
|------|-------------|-------------------|
| Checkpoint resume | LangGraph interrupted mid-phase | Resumes at correct phase gate with correct state |
| Slack outage | Mock adapter raises `ConnectionError` | Graph transitions to `comms_pending` state, does not crash |
| Artifact store failure | Write fails mid-phase | Orchestrator blocks at gate, does not advance with incomplete artifacts |

**Fixtures:**
- Serialized state checkpoints at all 4 phase gates
- Mock Slack adapter with injectable `ConnectionError`
- Artifact store with injectable write failure

**Pass criteria:**
- Resume test passes at all 4 phase gates
- Slack outage produces `comms_pending` state, not exception
- Artifact store failure produces gate block, not corrupted phase advance

**Run command:**
```bash
python -m pytest tests/test_resilience.py -v
```

---

## 5. Style

**What:** Code and documentation meet structural standards.

**Automated checks:**

| Check | Tool | Target |
|-------|------|--------|
| Lint | `ruff check src/ tests/` | All Python code |
| Format | `black --check src/ tests/` | All Python code |
| Debug statements | `grep -rn "print\|pdb\|breakpoint" src/` | Zero matches in production paths |

**Documentation checks (manual or scripted):**
- `docs/agent-contracts.md` defines for all 7 agents: input schema, output schema, tool access, evaluation rubric
- `runs/run-001/debrief.md` contains structured sections: what worked, what broke, what to iterate

**Pass criteria:**
- `ruff` and `black` clean
- Zero debug statements in `src/`
- `agent-contracts.md` complete for all 7 agents
- Debrief has required structure

**Run command:**
```bash
ruff check src/ tests/ && black --check src/ tests/ && ! grep -rn "print\|pdb\|breakpoint" src/
```

---

## 6. UX / Taste (Human Approval Required)

**What:** Handoff package and key agent outputs are genuinely useful, not just schema-valid.

**Human review protocol:**

| Review item | Reviewer | Artifact | Sign-off location |
|-------------|----------|----------|-------------------|
| Handoff package actionability | 1 engineering consumer | `runs/run-001/handoff-package.json` | `runs/run-001/debrief.md` |
| Pressure Testing quality | Research lead | `runs/run-001/pressure_test_report.md` | `runs/run-001/debrief.md` |
| Feedback Synthesis quality | Research lead | `runs/run-001/feedback_synthesis_report.md` | `runs/run-001/debrief.md` |

**Acceptance questions:**
- Handoff package: "Can you begin implementation from this package without asking any clarifying questions?"
- Pressure Testing: "Did this report challenge the pitch with specific, substantive objections — or was it generic?"
- Feedback Synthesis: "Does this report surface meaningful divergence between internal findings and stakeholder input — or just paraphrase?"

**Pass criteria:**
- Engineering consumer confirms actionability (recorded in debrief)
- Research lead confirms Pressure Testing and Feedback Synthesis quality (recorded in debrief)
- All three sign-offs present in `runs/run-001/debrief.md`

---

## Full Eval Run

**Automated (CI-safe):**
```bash
python -m pytest tests/ -v --tb=short
ruff check src/ tests/
black --check src/ tests/
```

**Human review:** Triggered after first real run (`runs/run-001/`). Requires 2 reviewers (1 engineering consumer + 1 research lead). Sign-offs recorded in `runs/run-001/debrief.md`.

**Eval is complete when:** All automated checks green AND all 3 human sign-offs recorded.
