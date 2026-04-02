# Spec — research-to-engineering-handoff

**Slug:** research-to-engineering-handoff  
**Status:** approved  
**Timestamp:** 20260401T000000Z

---

## 1. Problem

Product development at scale suffers from a structural gap: the work of determining *what* to build, *why*, *for whom*, and *how success will be measured* is scattered across UX research, PM, DS, and design functions with no coordinated intelligence layer and no structured handoff to engineering. Engineering teams routinely begin implementation from assumptions rather than validated briefs, discovering misalignment late in the cycle when it is expensive to correct. No existing multi-agent system fills this gap. MetaGPT and ChatDev are engineering-first — they ask "how do we build X?" and produce code. Anthropic's research system retrieves factual information but does not synthesize product intelligence. The missing system is a Research-Orchestrated, discovery-first pipeline that takes a product problem as input, runs coordinated intelligence work across seven specialist roles, pressure-tests its own outputs, and terminates at a structured handoff package that a downstream engineering system can execute against without doing any additional discovery work.

---

## 2. Scope

### In Scope

- Seven-agent intelligence system: Research Orchestrator, UX Research, PM, Data Science, Evaluation, Pressure Testing, Feedback Synthesis
- Handoff package schema definition (JSON + prose)
- LangGraph-based orchestration layer (state machine, phase gates, HITL checkpoints)
- Shared artifact store (per-agent outputs, cross-phase persistence)
- PM agent stakeholder communication interface (Model B: direct async comms, no human intermediary)
- Eval framework for output quality measurement (rubric-based + LLM-as-judge)
- Four-phase pipeline: Discovery → Definition → Pitch & Evaluation → Handoff
- First end-to-end run on a real bounded product problem

### Out of Scope

- Implementation code (engineering's responsibility downstream)
- The downstream engineering system (treated as black box)
- Production deployment, DevOps, CI/CD infrastructure
- Visual design tooling beyond text-based design specifications
- Test suite implementation (system produces harness concept only, not executable tests)
- Post-handoff operation — system's job ends when package is delivered
- Hiring or managing human team members

---

## 3. Architecture Decision

**Chosen approach:** LangGraph-based orchestrator-worker system. Research Orchestrator is the root node (high-reasoning model). Six specialist agents are worker nodes (lighter model). Artifact store persists all agent outputs; agents pass references, not content. Four phases with explicit gate nodes requiring Orchestrator approval + human review before transition.

**Rationale:** LangGraph is the only framework with native HITL checkpoints, typed state, resumable execution from failure, and conditional edge routing — all required for a phase-gated product intelligence pipeline. The Anthropic orchestrator-worker pattern with artifact store is production-proven for intelligence-gathering tasks. Research Orchestrator as root node is the architectural mechanism that makes Research the structural control plane — not a political claim, a topological fact.

**Alternatives Considered:**

- **CrewAI** — Rejected: rigid sequential pipeline, no native HITL at phase gates, limited state persistence. Good for prototyping; not for a production gate-based system.
- **MetaGPT** — Rejected: engineering-first orientation is wrong. No UXR, Design, Evaluation, or Pressure Testing roles. PRD is generated as a feed to engineering, not as a validated output. Cannot be repurposed without rebuilding the orientation.
- **AutoGen** — Rejected: conversational/dialogue-based handoffs lose fidelity at scale. Non-deterministic routing. Appropriate for exploratory research, not for a structured phase-gated pipeline.
- **Single large agent** — Rejected: context window limits prevent the breadth of parallel research needed in Discovery phase. Token cost is higher per unit of output than tiered multi-agent. Cannot parallelize independent research tracks.
- **Human workflow with AI assist** — Rejected: does not achieve the autonomous coordination goal; reintroduces the coordination overhead the system is meant to eliminate.

---

## 4. Interfaces

### Input Interface
- **What:** Product problem statement in natural language
- **Who owns it:** Human (research lead or product team)
- **Format:** NL text → structured intake form (parsed by Orchestrator at session start)
- **This system:** reads

### Output Interface — Handoff Package
- **What:** Structured handoff package for downstream engineering
- **Who owns it:** This system (write), downstream engineering system (read)
- **Format:** JSON schema (machine-readable) + prose documents (human-readable)
- **Schema fields:** `problem_statement`, `user_research`, `product_pitch`, `requirements`, `eval_criteria`, `test_harness_concept`, `feedback_synthesis`, `risk_log`, `open_assumptions`
- **This system:** writes

### Stakeholder Communication Interface (PM Agent)
- **What:** Async comms channel for PM agent → stakeholders → Feedback Synthesis agent
- **Who owns it:** Meta Slack workspace / email / async review platform
- **This system:** writes (PM agent sends), reads (Feedback Synthesis agent collects responses)
- **Model:** Model B — PM agent communicates directly, no human intermediary for routine cycles

### Downstream Engineering Interface
- **What:** The handoff package schema is the API contract
- **Who owns it:** Negotiated with engineering consumers before system build
- **This system:** writes only — downstream engineering system is a black box

### Meta Internal Data Systems
- **What:** User research repositories, behavioral analytics, existing research artifacts
- **Who owns it:** Meta internal data org
- **This system:** reads (Signal Intake for Discovery phase); never writes

### LangGraph State
- **What:** Typed StateGraph with per-phase state schemas
- **Who owns it:** This system
- **This system:** reads and writes throughout pipeline execution

---

## 5. Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| LangGraph | ≥0.2 | Orchestration framework — state machine, HITL, conditional routing |
| Llama (Meta-internal) | Large (orchestrator) + medium (workers) | LLM backbone — orchestrator reasoning + agent execution |
| Pydantic | v2 | Typed schemas for all agent inputs/outputs and handoff package |
| Artifact store | TBD (filesystem or Qdrant) | Persistent storage for agent outputs across phases |
| Slack API / Meta comms platform | Current | PM agent stakeholder communication (Model B) |
| Meta internal research repos | Current | Signal Intake — user research, behavioral analytics |
| Python | ≥3.12 | Runtime |
| LangSmith or equivalent | Current | Trace logging, observability, eval |

---

## 6. Risks

- **Handoff format not adopted by engineering** — Mitigation: co-design schema with engineering consumers before building; get explicit sign-off on the format as a prerequisite to starting implementation
- **Orchestrator gate logic too permissive** — produces briefs that pass gates but aren't actually validated. Mitigation: explicit rubric per phase gate; human review required at each gate; calibrate rubrics on first real run
- **PM agent stakeholder comms low response rate** — engineering teams ignore async requests. Mitigation: start with willing early adopters; establish trust through quality of output before expanding; fallback to human PM for initial outreach
- **Token cost at production scale** — 15x baseline × parallel runs × cross-product scope = significant cost. Mitigation: model tiering (Llama large orchestrator only; smaller for workers); per-run token budget with hard ceiling; route narrow/simple problems to single-agent path
- **Llama capability gaps for synthesis tasks** — orchestrator synthesis quality may be insufficient for complex product intelligence. Mitigation: evaluate on first end-to-end run; design with model-swappable orchestrator node (can substitute Claude/GPT-4 if needed without restructuring)
- **Hallucination laundering** — subagent hallucinates a user insight; orchestrator synthesizes it into validated brief. Mitigation: require source citations in all subagent outputs; human review at phase gates; Pressure Testing agent adversarially challenges all key claims
- **Scope creep into implementation** — pressure to have the system produce code, not just briefs. Mitigation: production boundary is a hard architectural constraint, not a preference; enforce via contract

---

## 7. Sequencing

Each step produces a verifiable artifact or checkpoint before the next step begins.

1. **Define handoff package schema** — JSON schema + field definitions, reviewed and signed off by at least one engineering consumer. Output: `handoff-package-schema.json`
2. **Define agent role contracts** — input schema, output schema, tool access, and evaluation rubric for all 7 agents. Output: `agent-contracts.md`
3. **Implement LangGraph skeleton** — graph nodes (one per agent + Orchestrator), typed state objects, phase gate nodes, conditional edges. No LLM calls yet — stub nodes only. Output: runnable graph skeleton with unit tests on routing logic
4. **Implement artifact store** — filesystem-based initially; each agent writes to a named directory; Orchestrator reads via reference. Output: `artifact_store.py` with read/write/list API
5. **Implement Research Orchestrator** — gate logic, phase transition decisions, conflict resolution between agent outputs, "current best understanding" document maintenance. Output: Orchestrator node passing gate logic tests
6. **Implement UX Research agent** — qual synthesis, persona generation, problem validation. Accepts user research input; produces `uxr_artifact.json`. Output: agent + unit tests on artifact schema compliance
7. **Implement PM agent + comms interface** — product pitch generation, requirements prioritization, Slack/comms integration for async stakeholder review cycle. Output: PM agent + comms adapter + integration test on async cycle
8. **Implement DS agent** — quantitative feasibility, data availability assessment, experiment design schema. Output: DS agent + unit tests
9. **Implement Evaluation agent** — success criteria definition, test harness concept, eval schema. Output: Evaluation agent + unit tests
10. **Implement Pressure Testing agent** — adversarial review of all key claims in current brief, structured objection report. Output: Pressure Testing agent + tests verifying it produces objections (not rubber-stamps)
11. **Implement Feedback Synthesis agent** — collects stakeholder responses from comms interface, structures conflicts/alignments against internal findings. Output: Feedback Synthesis agent + unit tests
12. **Wire phase gates in LangGraph** — connect all agents into full graph with gate nodes; implement HITL checkpoints; end-to-end graph runnable on synthetic input. Output: full graph integration test
13. **Implement handoff package assembler** — Orchestrator final step: aggregates all agent artifacts into typed handoff package, validates against schema, writes to output. Output: assembler + schema validation tests
14. **Build eval framework** — rubric-based quality assessment for each artifact type; LLM-as-judge for open-ended fields; human spot-check protocol for phase gates. Output: `eval_framework.py` + rubric definitions
15. **First end-to-end run** — run full pipeline on one real, bounded Meta product problem. Capture all artifacts. Measure output quality against eval framework. Document what worked, what broke, what to iterate. Output: run artifact set + debrief document

---

## 8. Tasks

- [ ] Define and document handoff package JSON schema (`handoff-package-schema.json`)
- [ ] Define agent role contracts for all 7 agents (`agent-contracts.md`)
- [ ] Implement LangGraph graph skeleton (nodes, edges, state types) — stub nodes only
- [ ] Write routing logic unit tests for LangGraph skeleton
- [ ] Implement artifact store (`artifact_store.py` — read/write/list API)
- [ ] Implement Research Orchestrator agent + gate logic
- [ ] Write Orchestrator gate logic tests
- [ ] Implement UX Research agent
- [ ] Implement PM agent
- [ ] Implement PM agent Slack/comms integration
- [ ] Write PM agent async comms integration test
- [ ] Implement DS agent
- [ ] Implement Evaluation agent
- [ ] Implement Pressure Testing agent
- [ ] Write Pressure Testing agent test (verifies it produces objections, not rubber-stamps)
- [ ] Implement Feedback Synthesis agent
- [ ] Wire all agents into full LangGraph graph with phase gates
- [ ] Implement HITL checkpoints at all 4 phase gates
- [ ] Implement handoff package assembler
- [ ] Implement schema validation on handoff package output
- [ ] Build eval framework (`eval_framework.py` + rubric definitions)
- [ ] Run first end-to-end test on synthetic input (full graph smoke test)
- [ ] Run first end-to-end run on real bounded Meta product problem
- [ ] Write debrief document from first real run

---

## 9. Acceptance Criteria

- [ ] System accepts a natural language product problem statement and produces a complete handoff package
- [ ] Handoff package conforms to `handoff-package-schema.json` (schema validation passes)
- [ ] All 7 agents produce typed artifacts persisted in the artifact store
- [ ] Research Orchestrator gates all 4 phase transitions with a structured, citable decision referencing specific agent outputs
- [ ] Orchestrator gate decisions are auditable — each decision cites which agent artifact(s) it is based on
- [ ] PM agent completes at least one async stakeholder review cycle end-to-end (sends comms, receives responses, passes to Feedback Synthesis)
- [ ] Pressure Testing agent produces adversarial challenge report with specific named objections to pitch claims — not generic feedback
- [ ] Feedback Synthesis agent surfaces at least one alignment and one conflict between internal findings and stakeholder responses in each run
- [ ] First real run produces a handoff package that at least one engineering consumer confirms is actionable without additional discovery work
- [ ] System resumes from checkpoint correctly when interrupted mid-run (LangGraph resilience test)
- [ ] Eval framework produces a quality score for each artifact type; scores are auditable
