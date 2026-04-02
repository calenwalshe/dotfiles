# Contract — research-to-engineering-handoff-001

**ID:** research-to-engineering-handoff-001  
**Slug:** research-to-engineering-handoff  
**Phase:** execute  
**Status:** approved  
**Timestamp:** 20260401T000000Z

---

## Objective

Build a seven-agent pre-production intelligence system that takes a product problem statement as input and produces a validated, schema-typed handoff package consumable by a downstream engineering system — covering research, product pitch, evaluation criteria, test harness concept, and stakeholder feedback — so that engineering can begin implementation without any additional discovery work.

---

## Deliverables

- `src/schemas/handoff-package-schema.json` — typed schema for all handoff package fields
- `docs/agent-contracts.md` — role contracts for all 7 agents
- `src/graph/graph.py` — LangGraph state machine (nodes, edges, phase gates, HITL)
- `src/store/artifact_store.py` — shared artifact persistence layer
- `src/agents/orchestrator.py` — Research Orchestrator + gate logic
- `src/agents/uxr.py` — UX Research agent
- `src/agents/pm.py` + `src/integrations/comms.py` — PM agent + stakeholder comms
- `src/agents/ds.py` — Data Science agent
- `src/agents/evaluation.py` — Evaluation agent
- `src/agents/pressure_test.py` — Pressure Testing agent
- `src/agents/feedback_synthesis.py` — Feedback Synthesis agent
- `src/assembler/assembler.py` — handoff package assembler + schema validator
- `src/eval/eval_framework.py` + `src/eval/rubrics/` — eval framework + rubrics
- `runs/run-001/` — first real run artifacts
- `runs/run-001/debrief.md` — first run debrief

---

## Scope

**In Scope:**
- All 7 agent implementations
- LangGraph orchestration layer
- Artifact store
- Handoff package schema + assembler
- PM agent stakeholder comms interface (Model B)
- Eval framework
- First end-to-end run on real Meta product problem

**Out of Scope:**
- Implementation code for the product being researched
- The downstream engineering system
- Production deployment / DevOps
- Visual design tooling
- Test suite implementation (harness concept only)
- Post-handoff operation

---

## Write Roots

The executing agent is authorized to write to:
- `src/`
- `docs/agent-contracts.md`
- `runs/`
- `tests/`

All other paths are read-only during execution.

---

## Done Criteria

- [ ] System accepts NL product problem statement and produces handoff package conforming to `handoff-package-schema.json`
- [ ] All 7 agents produce typed artifacts persisted in artifact store
- [ ] Orchestrator gates all 4 phase transitions with citable, auditable decisions
- [ ] PM agent completes async stakeholder review cycle end-to-end
- [ ] Pressure Testing agent produces specific named objections (not generic feedback)
- [ ] Feedback Synthesis agent surfaces at least one alignment and one conflict per run
- [ ] First real run handoff package confirmed actionable by at least one engineering consumer
- [ ] System resumes correctly from checkpoint when interrupted mid-run
- [ ] Eval framework produces auditable quality scores per artifact type

---

## Validators

```bash
# Schema validation
python -m pytest tests/test_schema_validation.py

# Agent artifact compliance
python -m pytest tests/test_agent_contracts.py

# Graph routing logic
python -m pytest tests/test_graph_routing.py

# Pressure Testing produces objections (not rubber-stamps)
python -m pytest tests/test_pressure_testing_non_trivial.py

# Checkpoint resume
python -m pytest tests/test_checkpoint_resume.py

# End-to-end smoke test
python -m pytest tests/test_e2e_synthetic.py

# Eval framework audit trail
python -m pytest tests/test_eval_audit.py
```

---

## Eval Plan

docs/cortex/evals/research-to-engineering-handoff/eval-plan.md

---

## Approvals

- [x] Spec approved
- [x] Contract approved

---

## Rollback Hints

If execution needs to be undone:
- Delete `src/` directory
- Delete `runs/`
- Delete `docs/agent-contracts.md`
- Delete `tests/`
- Reset `.cortex/state.json` `mode` to `clarify`
- No external systems modified until PM agent comms integration is wired (step 9) — rollback is clean before that point
