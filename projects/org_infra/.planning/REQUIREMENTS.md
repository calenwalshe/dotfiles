# Requirements: Research-to-Engineering Handoff

**Defined:** 2026-04-01
**Core Value:** Engineering can begin implementation from handoff package without additional discovery

## v1 Requirements

### Schema

- [ ] **SCHEMA-01**: Handoff package JSON schema defined with typed fields for all package sections
- [ ] **SCHEMA-02**: Schema reviewed and co-signed by at least one engineering consumer

### Agents

- [ ] **AGENT-01**: Research Orchestrator gates all 4 phase transitions with citable, auditable decisions referencing specific agent artifacts
- [ ] **AGENT-02**: UX Research agent produces typed artifacts (personas, problem validation, user signal synthesis)
- [ ] **AGENT-03**: PM agent generates product pitch, requirements definition, and prioritization
- [ ] **AGENT-04**: PM agent completes at least one async stakeholder review cycle end-to-end via Slack/comms
- [ ] **AGENT-05**: DS agent produces quantitative feasibility assessment, data availability, experiment design
- [ ] **AGENT-06**: Evaluation agent produces success criteria, test harness concept, eval schema
- [ ] **AGENT-07**: Pressure Testing agent produces adversarial challenge report with specific named objections to pitch claims
- [ ] **AGENT-08**: Feedback Synthesis agent surfaces at least one alignment and one conflict between internal findings and stakeholder responses per run

### Orchestration

- [ ] **ORCH-01**: LangGraph state machine routes correctly through Discovery → Definition → Pitch & Evaluation → Handoff
- [ ] **ORCH-02**: HITL checkpoints pause execution at all 4 phase gates for human review
- [ ] **ORCH-03**: System resumes correctly from checkpoint when interrupted mid-run

### Integration

- [ ] **INTG-01**: All 7 agents produce typed artifacts persisted in shared artifact store
- [ ] **INTG-02**: Handoff package assembler aggregates all agent artifacts into schema-conformant package

### Evaluation

- [ ] **EVAL-01**: Eval framework produces auditable quality scores per artifact type with rubric-based + LLM-as-judge assessment

### Validation

- [ ] **VALID-01**: First real run handoff package confirmed actionable by at least one engineering consumer without additional discovery work

## v2 Requirements

### Scale

- **SCALE-01**: Per-run token budget with hard ceiling and cost reporting
- **SCALE-02**: Model tiering optimization (swap worker models for cost)
- **SCALE-03**: Cross-product routing (narrow problems → single-agent fast path)

### Observability

- **OBS-01**: LangSmith trace logging for all agent calls
- **OBS-02**: Per-phase quality dashboard

## Out of Scope

| Feature | Reason |
|---------|--------|
| Implementation code | Engineering's responsibility downstream — hard boundary |
| Downstream engineering system | Treated as black box; handoff schema is the API contract |
| Production deployment / DevOps | Not in contract scope |
| Visual design / wireframing | Beyond text-based specifications |
| Test suite implementation | Harness concept only — engineering implements tests |
| Post-handoff operation | System's job ends at package delivery |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCHEMA-01 | Phase 1 | Pending |
| SCHEMA-02 | Phase 1 | Pending |
| AGENT-01 | Phase 3 | Pending |
| AGENT-02 | Phase 4 | Pending |
| AGENT-03 | Phase 4 | Pending |
| AGENT-04 | Phase 4 | Pending |
| AGENT-05 | Phase 4 | Pending |
| AGENT-06 | Phase 4 | Pending |
| AGENT-07 | Phase 4 | Pending |
| AGENT-08 | Phase 4 | Pending |
| ORCH-01 | Phase 2 | Pending |
| ORCH-02 | Phase 5 | Pending |
| ORCH-03 | Phase 5 | Pending |
| INTG-01 | Phase 2 | Pending |
| INTG-02 | Phase 5 | Pending |
| EVAL-01 | Phase 6 | Pending |
| VALID-01 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after GSD import*
