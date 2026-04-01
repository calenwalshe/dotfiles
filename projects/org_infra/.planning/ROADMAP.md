# Roadmap: Research-to-Engineering Handoff

## Milestones

- :white_check_mark: **v1.0 MVP** - Phases 1-6 (shipped 2026-04-01)
- :construction: **v1.1 LLM Agents + HITL** - Phases 7-12 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-6) - SHIPPED 2026-04-01</summary>

### Phase 1: Schema & Contracts
**Plans**: 2/2 complete

### Phase 2: Infrastructure
**Plans**: 2/2 complete

### Phase 3: Orchestrator
**Plans**: 1/1 complete

### Phase 4: Worker Agents
**Plans**: 1/1 complete

### Phase 5: Integration
**Plans**: 1/1 complete

### Phase 6: Eval & Validation
**Plans**: 1/1 complete

</details>

### v1.1 LLM Agents + HITL (In Progress)

**Milestone Goal:** Replace rule-based agents with Claude Sonnet-powered subprocesses, add run-level HITL autonomy dial, wire token tracking, deploy inside openclaw.

#### Phase 7: HITL Framework
**Goal**: Implement the run-level autonomy dial and circuit breaker. Graph supports autonomous (no stops), supervised (gate stops), and guided (every agent stop) modes.
**Depends on**: Phase 6 (existing graph infrastructure)
**Requirements**: HITL-01, HITL-02, HITL-03, HITL-04, HITL-05, HITL-06
**Success Criteria** (what must be TRUE):
  1. Run config accepts `autonomy_level` parameter
  2. `supervised` mode pauses at each of the 3 phase gates and resumes on human input
  3. `guided` mode pauses after every agent node
  4. `autonomous` mode runs to completion without human stops
  5. Circuit breaker halts autonomous run when token/time budget exhausted
  6. Circuit breaker halts autonomous run when eval scores plateau across gate retries
**Plans**: TBD

Plans:
- [ ] 07-01: Run config + autonomy parameter + LangGraph interrupt wiring
- [ ] 07-02: Circuit breaker (budget + eval plateau detection)

#### Phase 8: Agent Runner
**Goal**: Build the `claude -p` subprocess wrapper that all LLM agents use. Handles prompt injection, output capture, artifact store write, timeout, and failure recovery.
**Depends on**: Phase 7 (HITL framework — runner needs to respect autonomy config)
**Requirements**: LLM-01, LLM-02
**Success Criteria** (what must be TRUE):
  1. Agent runner executes `claude -p` with system prompt + artifact context
  2. Runner captures stdout, parses output, writes typed artifact to store
  3. Runner handles timeout (configurable per-agent ceiling)
  4. Runner handles failure (non-zero exit, malformed output) gracefully — returns error artifact, does not crash graph
**Plans**: TBD

Plans:
- [ ] 08-01: Agent runner implementation + tests

#### Phase 9: LLM Worker Agents
**Goal**: Convert all 6 worker agents from rule-based to Claude Sonnet-powered via agent runner. Each agent gets a system prompt, receives artifacts as context, produces LLM-quality output.
**Depends on**: Phase 8 (agent runner must exist)
**Requirements**: LLM-03
**Success Criteria** (what must be TRUE):
  1. Each agent produces substantively different output than the rule-based version (not template-fill)
  2. All agent outputs still pass schema validation and Orchestrator quality checks
  3. Full pipeline runs e2e with LLM agents on synthetic input
  4. Eval framework scores are >= v1.0 scores (no quality regression)
**Plans**: TBD

Plans:
- [ ] 09-01: LLM system prompts for all 6 agents
- [ ] 09-02: Wire agents through runner, e2e validation

#### Phase 10: Orchestrator Upgrade
**Goal**: Upgrade Orchestrator gate decisions to use LLM reasoning alongside rule-based checks. Gate decisions should cite specific artifacts with natural language rationale.
**Depends on**: Phase 9 (LLM agents produce richer artifacts for Orchestrator to evaluate)
**Requirements**: LLM-04
**Success Criteria** (what must be TRUE):
  1. Orchestrator gate decisions include LLM-generated rationale (not just rule-based pass/fail)
  2. Gate decisions still enforce minimum quality rules (rule-based as floor, LLM as ceiling)
  3. Reject decisions include specific, actionable feedback for which agent to improve
**Plans**: TBD

Plans:
- [ ] 10-01: LLM-powered gate evaluation + hybrid rule/LLM logic

#### Phase 11: Token Tracking
**Goal**: Instrument per-agent and per-run token usage. Expose cost data in run artifacts. Wire token budget into circuit breaker.
**Depends on**: Phase 9 (LLM agents must be running to produce real token data)
**Requirements**: TOKEN-01, TOKEN-02, TOKEN-03
**Success Criteria** (what must be TRUE):
  1. Each agent run records input/output token counts
  2. Per-run total cost stored in `runs/{run_id}/cost.json`
  3. Token budget ceiling stops autonomous runs when exceeded
**Plans**: TBD

Plans:
- [ ] 11-01: Token capture from `claude -p` output + cost aggregation + budget enforcement

#### Phase 12: Openclaw Integration
**Goal**: Deploy the system inside the openclaw container. Wire real comms adapter for PM agent stakeholder cycles.
**Depends on**: Phase 11 (full system must be functional before deployment)
**Requirements**: CLAW-01, CLAW-02
**Success Criteria** (what must be TRUE):
  1. System runs inside openclaw container with correct mounted filesystem paths
  2. `claude` CLI available and functional inside container
  3. PM agent sends/receives via real Slack or email adapter
  4. First LLM-powered run completes successfully inside container
**Plans**: TBD

Plans:
- [ ] 12-01: Container config + filesystem paths + claude CLI verification
- [ ] 12-02: Real comms adapter (Slack/email) + first containerized run

## Progress

**Execution Order:** 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Schema & Contracts | 2/2 | Complete | 2026-04-01 |
| 2. Infrastructure | 2/2 | Complete | 2026-04-01 |
| 3. Orchestrator | 1/1 | Complete | 2026-04-01 |
| 4. Worker Agents | 1/1 | Complete | 2026-04-01 |
| 5. Integration | 1/1 | Complete | 2026-04-01 |
| 6. Eval & Validation | 1/1 | Complete | 2026-04-01 |
| 7. HITL Framework | 0/2 | Not started | - |
| 8. Agent Runner | 0/1 | Not started | - |
| 9. LLM Worker Agents | 0/2 | Not started | - |
| 10. Orchestrator Upgrade | 0/1 | Not started | - |
| 11. Token Tracking | 0/1 | Not started | - |
| 12. Openclaw Integration | 0/2 | Not started | - |
