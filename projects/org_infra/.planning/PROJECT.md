# Research-to-Engineering Handoff System

## What This Is

A seven-agent pre-production intelligence system that takes a product problem statement as input and produces a validated, schema-typed handoff package for a downstream engineering system. The system owns everything before implementation — research, product pitch, evaluation criteria, test harness concept, stakeholder feedback. Engineering owns everything after handoff.

## Core Value

A downstream engineering team can begin implementation from the handoff package without any additional discovery work.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] SCHEMA-01: Handoff package JSON schema defined and versioned
- [ ] SCHEMA-02: Schema validated by at least one engineering consumer
- [ ] AGENT-01: Research Orchestrator gates all 4 phase transitions with citable, auditable decisions
- [ ] AGENT-02: UX Research agent produces typed user research artifacts
- [ ] AGENT-03: PM agent generates product pitch and prioritized requirements
- [ ] AGENT-04: PM agent completes async stakeholder review cycle end-to-end
- [ ] AGENT-05: DS agent produces quantitative feasibility assessment
- [ ] AGENT-06: Evaluation agent defines success criteria and test harness concept
- [ ] AGENT-07: Pressure Testing produces specific named objections (not rubber-stamps)
- [ ] AGENT-08: Feedback Synthesis surfaces at least one alignment and one conflict per run
- [ ] ORCH-01: LangGraph state machine routes correctly across all 4 phases
- [ ] ORCH-02: HITL checkpoints at all 4 phase gates
- [ ] ORCH-03: System resumes from checkpoint when interrupted mid-run
- [ ] INTG-01: All 7 agents produce typed artifacts persisted in artifact store
- [ ] INTG-02: Handoff package assembler produces schema-conformant output
- [ ] EVAL-01: Eval framework produces auditable quality scores per artifact type
- [ ] VALID-01: First real run handoff package confirmed actionable by engineering consumer

### Out of Scope

- Implementation code for the product being researched — engineering's responsibility downstream
- The downstream engineering system — treated as black box
- Production deployment / DevOps / CI/CD — not in contract scope
- Visual design tooling — beyond text-based design specifications
- Test suite implementation — system produces harness concept only, not executable tests
- Post-handoff operation — system's job ends when package is delivered

## Context

- **Architecture:** LangGraph-based orchestrator-worker. Research Orchestrator = root node (high-reasoning model). 6 specialist agents = worker nodes (lighter model). Artifact store persists outputs; agents pass references, not content.
- **Pipeline:** Four phases — Discovery → Definition → Pitch & Evaluation → Handoff. Explicit gate nodes at each transition requiring Orchestrator approval + human review.
- **PM comms model:** Model B — PM agent communicates directly with stakeholders via Slack/async platform. No human intermediary for routine feedback cycles.
- **Cortex contract:** `docs/cortex/contracts/research-to-engineering-handoff/contract-001.md`
- **Eval plan:** `docs/cortex/evals/research-to-engineering-handoff/eval-plan.md`
- **Prior research:** Concept and implementation research from prior slug `agentic-business-role-systems` remains valid.

## Constraints

- **Framework:** LangGraph ≥0.2 — native HITL, typed state, resumable execution
- **LLM:** Llama (large for orchestrator, medium for workers) — model-swappable if capability gaps surface
- **Runtime:** Python ≥3.12
- **Handoff format:** JSON schema + prose documents — format is the API contract with downstream engineering
- **Production boundary:** Hard architectural constraint — no implementation code crosses into this system
- **Write roots:** `src/`, `docs/agent-contracts.md`, `runs/`, `tests/` only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph over CrewAI/AutoGen | Native HITL checkpoints, typed state, resumable execution, conditional routing | — Pending |
| Orchestrator-worker pattern | Production-proven for intelligence tasks; Research Orchestrator as structural control plane | — Pending |
| PM agent Model B (direct comms) | Removes human intermediary bottleneck for routine feedback cycles | — Pending |
| Artifact store (references not content) | Prevents context window bloat; enables independent agent execution | — Pending |
| Eval: 6 of 8 dimensions | Regression excluded (greenfield), Performance excluded (no SLA in contract) | — Pending |

---
*Last updated: 2026-04-01 after GSD import from Cortex handoff*
