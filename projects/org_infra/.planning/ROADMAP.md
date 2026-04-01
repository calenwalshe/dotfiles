# Roadmap: Research-to-Engineering Handoff

## Overview

Build the seven-agent intelligence system in six phases: define the contracts and schema (foundation), build infrastructure (graph + store), implement the orchestrator, implement all worker agents (parallelizable), wire integration + HITL, then validate with eval framework and first real run.

## Phases

- [ ] **Phase 1: Schema & Contracts** — Define the handoff package schema and all 7 agent role contracts
- [ ] **Phase 2: Infrastructure** — LangGraph skeleton with stub nodes + artifact store
- [ ] **Phase 3: Orchestrator** — Research Orchestrator agent with gate logic
- [ ] **Phase 4: Worker Agents** — All 6 specialist agents (UXR, PM, DS, Eval, Pressure Test, Feedback Synthesis)
- [ ] **Phase 5: Integration** — Wire full graph, HITL checkpoints, handoff package assembler
- [ ] **Phase 6: Eval & Validation** — Eval framework, synthetic smoke test, first real run, debrief

## Phase Details

### Phase 1: Schema & Contracts
**Goal**: Define the typed contracts that every downstream phase builds against — the handoff package schema and all 7 agent role contracts.
**Depends on**: Nothing (first phase)
**Requirements**: SCHEMA-01, SCHEMA-02
**Success Criteria** (what must be TRUE):
  1. `handoff-package-schema.json` exists with typed fields for all 9 package sections
  2. `agent-contracts.md` defines input schema, output schema, tool access, and evaluation rubric for all 7 agents
  3. At least one engineering consumer has reviewed the schema
**Plans**: 2 plans

Plans:
- [ ] 01-01: Define handoff package JSON schema
- [ ] 01-02: Define agent role contracts for all 7 agents

### Phase 2: Infrastructure
**Goal**: Build the LangGraph orchestration skeleton and artifact store — the runtime foundation all agents plug into.
**Depends on**: Phase 1 (agent contracts define node interfaces)
**Requirements**: ORCH-01, INTG-01
**Success Criteria** (what must be TRUE):
  1. LangGraph graph with 7 agent stub nodes + 4 phase gate nodes runs end-to-end on synthetic input
  2. Routing logic unit tests pass for all conditional edges
  3. Artifact store read/write/list API works with typed agent output schemas
**Plans**: 2 plans (parallelizable)

Plans:
- [ ] 02-01: LangGraph graph skeleton with stub nodes + routing tests
- [ ] 02-02: Artifact store implementation

### Phase 3: Orchestrator
**Goal**: Implement the Research Orchestrator — the gate agent that controls all phase transitions.
**Depends on**: Phase 2 (graph skeleton + artifact store must exist)
**Requirements**: AGENT-01
**Success Criteria** (what must be TRUE):
  1. Orchestrator makes gate decisions that cite specific agent artifacts
  2. Gate logic tests pass for all 4 phase transitions (approve and reject paths)
  3. Orchestrator maintains "current best understanding" document across phases
**Plans**: 1 plan

Plans:
- [ ] 03-01: Research Orchestrator agent + gate logic + tests

### Phase 4: Worker Agents
**Goal**: Implement all 6 specialist agents. These are independent of each other and can be built in parallel.
**Depends on**: Phase 3 (Orchestrator defines gate interface that workers must satisfy)
**Requirements**: AGENT-02, AGENT-03, AGENT-04, AGENT-05, AGENT-06, AGENT-07, AGENT-08
**Success Criteria** (what must be TRUE):
  1. Each agent produces typed artifacts conforming to its contract schema
  2. PM agent sends and receives via comms adapter (mock for now)
  3. Pressure Testing agent produces specific named objections (not generic feedback) — verified by test
  4. Feedback Synthesis agent produces alignment/conflict report
**Plans**: 6 plans (parallelizable)

Plans:
- [ ] 04-01: UX Research agent
- [ ] 04-02: PM agent + Slack/comms integration
- [ ] 04-03: DS agent
- [ ] 04-04: Evaluation agent
- [ ] 04-05: Pressure Testing agent
- [ ] 04-06: Feedback Synthesis agent

### Phase 5: Integration
**Goal**: Wire all agents into the full LangGraph graph with phase gates, HITL checkpoints, and the handoff package assembler.
**Depends on**: Phase 4 (all agents must exist)
**Requirements**: ORCH-02, ORCH-03, INTG-02
**Success Criteria** (what must be TRUE):
  1. Full graph runs end-to-end with all real agents (not stubs) on synthetic input
  2. HITL checkpoints pause at all 4 phase gates and resume correctly
  3. Checkpoint resume test passes (interrupt mid-run, restore, continue)
  4. Assembler produces schema-conformant handoff package from real agent outputs
**Plans**: 2 plans

Plans:
- [ ] 05-01: Wire full graph with phase gates + HITL checkpoints
- [ ] 05-02: Handoff package assembler + schema validation

### Phase 6: Eval & Validation
**Goal**: Build eval framework, run synthetic smoke test, execute first real run on bounded product problem, write debrief.
**Depends on**: Phase 5 (full integrated system required)
**Requirements**: EVAL-01, VALID-01
**Success Criteria** (what must be TRUE):
  1. Eval framework produces quality scores for each artifact type
  2. Synthetic smoke test passes end-to-end
  3. First real run produces complete handoff package
  4. Engineering consumer confirms handoff package is actionable
  5. Debrief document captures what worked, broke, and needs iteration
**Plans**: 3 plans

Plans:
- [ ] 06-01: Eval framework + rubric definitions
- [ ] 06-02: E2E smoke test on synthetic input
- [ ] 06-03: First real run on bounded product problem + debrief

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Schema & Contracts | 2/2 | Complete | 2026-04-01 |
| 2. Infrastructure | 0/2 | Not started | - |
| 3. Orchestrator | 0/1 | Not started | - |
| 4. Worker Agents | 0/6 | Not started | - |
| 5. Integration | 0/2 | Not started | - |
| 6. Eval & Validation | 0/3 | Not started | - |
