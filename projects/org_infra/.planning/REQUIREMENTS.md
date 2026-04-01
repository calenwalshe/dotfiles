# Requirements: Research-to-Engineering Handoff

**Defined:** 2026-04-01
**Core Value:** Engineering can begin implementation from handoff package without additional discovery

## v1.0 Requirements (Validated)

- [x] **SCHEMA-01**: Handoff package JSON schema defined with typed fields for all package sections
- [x] **SCHEMA-02**: Schema reviewed and co-signed by at least one engineering consumer
- [x] **AGENT-01**: Research Orchestrator gates all 4 phase transitions with citable decisions
- [x] **AGENT-02**: UX Research agent produces typed artifacts
- [x] **AGENT-03**: PM agent generates product pitch, requirements, and prioritization
- [x] **AGENT-04**: PM agent completes async stakeholder review cycle end-to-end
- [x] **AGENT-05**: DS agent produces quantitative feasibility assessment
- [x] **AGENT-06**: Evaluation agent produces success criteria and test harness concept
- [x] **AGENT-07**: Pressure Testing produces specific named objections
- [x] **AGENT-08**: Feedback Synthesis surfaces alignments and conflicts
- [x] **ORCH-01**: LangGraph state machine routes correctly through all 4 phases
- [x] **INTG-01**: All 7 agents produce typed artifacts in artifact store
- [x] **INTG-02**: Handoff package assembler produces schema-conformant output
- [x] **EVAL-01**: Eval framework produces auditable quality scores

## v1.1 Requirements

### HITL Spectrum

- [ ] **HITL-01**: Run accepts an autonomy level parameter (`autonomous`, `supervised`, `guided`)
- [ ] **HITL-02**: In `supervised` mode, graph pauses at each phase gate for human review before advancing
- [ ] **HITL-03**: In `guided` mode, graph pauses after every agent node for human review
- [ ] **HITL-04**: In `autonomous` mode, graph runs without human stops until completion or circuit breaker
- [ ] **HITL-05**: Circuit breaker stops autonomous runs when token/time budget is exhausted
- [ ] **HITL-06**: Circuit breaker stops autonomous runs when eval scores plateau or degrade across retries

### LLM Agents

- [ ] **LLM-01**: Agent runner executes `claude -p` subprocesses with injected system prompt and artifact context
- [ ] **LLM-02**: Agent runner captures output, writes to artifact store, handles timeout/failure
- [ ] **LLM-03**: All 6 worker agents produce LLM-quality output via Claude Sonnet (not rule-based templates)
- [ ] **LLM-04**: Orchestrator gate decisions use LLM reasoning (not just rule-based checks)

### Token Tracking

- [ ] **TOKEN-01**: Per-agent token usage captured for each run (input tokens, output tokens)
- [ ] **TOKEN-02**: Per-run total token cost calculated and stored in run artifacts
- [ ] **TOKEN-03**: Token budget enforceable as a circuit breaker ceiling

### Openclaw Integration

- [ ] **CLAW-01**: System runs inside openclaw container with correct filesystem paths
- [ ] **CLAW-02**: Real comms adapter (Slack or email) replaces mock for PM agent stakeholder cycles

## v2 Requirements (Deferred)

- **HITL-PER-AGENT**: Per-agent HITL granularity (override run-level for specific agents)
- **MODEL-SELECT**: Per-agent model selection (different Claude models for different agents)
- **MULTI-RUN**: Multiple concurrent runs with isolated state

## Out of Scope

| Feature | Reason |
|---------|--------|
| Implementation code | Engineering's responsibility downstream |
| Downstream engineering system | Black box — handoff schema is the contract |
| Per-agent HITL granularity | v1.1 uses run-level only — simpler mental model |
| Multi-model per agent | All agents use Claude Sonnet via `claude -p` for v1.1 |
| Visual design | Beyond text-based specifications |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HITL-01 | Phase 7 | Pending |
| HITL-02 | Phase 7 | Pending |
| HITL-03 | Phase 7 | Pending |
| HITL-04 | Phase 7 | Pending |
| HITL-05 | Phase 7 | Pending |
| HITL-06 | Phase 7 | Pending |
| LLM-01 | Phase 8 | Pending |
| LLM-02 | Phase 8 | Pending |
| LLM-03 | Phase 9 | Pending |
| LLM-04 | Phase 10 | Pending |
| TOKEN-01 | Phase 11 | Pending |
| TOKEN-02 | Phase 11 | Pending |
| TOKEN-03 | Phase 11 | Pending |
| CLAW-01 | Phase 12 | Pending |
| CLAW-02 | Phase 12 | Pending |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after v1.1 milestone definition*
