# GSD Handoff — research-to-engineering-handoff

**Status:** pending human import into GSD  
**Contract:** docs/cortex/contracts/research-to-engineering-handoff/contract-001.md  
**DO NOT auto-execute — human must import this into GSD explicitly**

---

## Objective

Build a seven-agent pre-production intelligence system (Research Orchestrator + UX Research + PM + DS + Evaluation + Pressure Testing + Feedback Synthesis) that takes a product problem statement as input and produces a validated, schema-typed handoff package for a downstream engineering system. The system owns everything before implementation: discovery, pitch, evaluation criteria, test harness concept, stakeholder feedback. Engineering owns everything after handoff. Success = a downstream engineering team confirms the handoff package is actionable without additional discovery work.

---

## Deliverables

| Artifact | Path |
|---|---|
| Handoff package schema | `src/schemas/handoff-package-schema.json` |
| Agent role contracts | `docs/agent-contracts.md` |
| LangGraph skeleton | `src/graph/graph.py` |
| Artifact store | `src/store/artifact_store.py` |
| Research Orchestrator agent | `src/agents/orchestrator.py` |
| UX Research agent | `src/agents/uxr.py` |
| PM agent + comms interface | `src/agents/pm.py`, `src/integrations/comms.py` |
| DS agent | `src/agents/ds.py` |
| Evaluation agent | `src/agents/evaluation.py` |
| Pressure Testing agent | `src/agents/pressure_test.py` |
| Feedback Synthesis agent | `src/agents/feedback_synthesis.py` |
| Handoff package assembler | `src/assembler/assembler.py` |
| Eval framework | `src/eval/eval_framework.py`, `src/eval/rubrics/` |
| First run artifacts | `runs/run-001/` |
| First run debrief | `runs/run-001/debrief.md` |

---

## Requirements

None formalized in REQUIREMENTS.md — this is a greenfield system.

---

## Tasks

1. - [ ] Define handoff package JSON schema (`src/schemas/handoff-package-schema.json`) — co-signed by at least one engineering consumer
2. - [ ] Define agent role contracts for all 7 agents (`docs/agent-contracts.md`)
3. - [ ] Implement LangGraph graph skeleton with stub nodes (`src/graph/graph.py`)
4. - [ ] Write routing logic unit tests for skeleton
5. - [ ] Implement artifact store read/write/list API (`src/store/artifact_store.py`)
6. - [ ] Implement Research Orchestrator agent + gate logic (`src/agents/orchestrator.py`)
7. - [ ] Implement UX Research agent (`src/agents/uxr.py`)
8. - [ ] Implement PM agent (`src/agents/pm.py`)
9. - [ ] Implement PM agent Slack/comms integration (`src/integrations/comms.py`)
10. - [ ] Implement DS agent (`src/agents/ds.py`)
11. - [ ] Implement Evaluation agent (`src/agents/evaluation.py`)
12. - [ ] Implement Pressure Testing agent (`src/agents/pressure_test.py`)
13. - [ ] Implement Feedback Synthesis agent (`src/agents/feedback_synthesis.py`)
14. - [ ] Wire full LangGraph graph with all agents + phase gates
15. - [ ] Implement HITL checkpoints at all 4 phase gates
16. - [ ] Implement handoff package assembler + schema validation (`src/assembler/assembler.py`)
17. - [ ] Build eval framework + rubric definitions (`src/eval/`)
18. - [ ] Run first end-to-end smoke test on synthetic input
19. - [ ] Run first real end-to-end run on bounded Meta product problem
20. - [ ] Write debrief document (`runs/run-001/debrief.md`)

---

## Acceptance Criteria

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

## Contract Link

docs/cortex/contracts/research-to-engineering-handoff/contract-001.md
