# Research-to-Engineering Handoff System

## What This Is

A seven-agent pre-production intelligence system that takes a product problem statement as input and produces a validated, schema-typed handoff package for a downstream engineering system. The system owns everything before implementation — research, product pitch, evaluation criteria, test harness concept, stakeholder feedback. Engineering owns everything after handoff.

## Core Value

A downstream engineering team can begin implementation from the handoff package without any additional discovery work.

## Current Milestone: v1.1 — LLM-Powered Agents + HITL Spectrum

**Goal:** Replace rule-based agents with Claude Sonnet-powered `claude -p` subprocesses, add a run-level HITL autonomy dial (autonomous/supervised/guided), wire token cost tracking, and deploy inside the openclaw container.

**Target features:**
- LLM-powered agents via `claude -p` subprocess pattern
- HITL spectrum: autonomous (no stops, eval-based circuit breaker), supervised (gate stops), guided (every agent)
- Circuit breaker: dual token/time budget + eval score plateau detection
- Per-agent and per-run token cost instrumentation
- Openclaw container deployment with real comms adapter

## Requirements

### Validated

- [x] SCHEMA-01: Handoff package JSON schema defined and versioned
- [x] SCHEMA-02: Schema validated by at least one engineering consumer
- [x] AGENT-01: Research Orchestrator gates all 4 phase transitions with citable, auditable decisions
- [x] AGENT-02: UX Research agent produces typed user research artifacts
- [x] AGENT-03: PM agent generates product pitch and prioritized requirements
- [x] AGENT-04: PM agent completes async stakeholder review cycle end-to-end
- [x] AGENT-05: DS agent produces quantitative feasibility assessment
- [x] AGENT-06: Evaluation agent defines success criteria and test harness concept
- [x] AGENT-07: Pressure Testing produces specific named objections (not rubber-stamps)
- [x] AGENT-08: Feedback Synthesis surfaces at least one alignment and one conflict per run
- [x] ORCH-01: LangGraph state machine routes correctly across all 4 phases
- [x] INTG-01: All 7 agents produce typed artifacts persisted in artifact store
- [x] INTG-02: Handoff package assembler produces schema-conformant output
- [x] EVAL-01: Eval framework produces auditable quality scores per artifact type

### Active

*(v1.1 requirements — see REQUIREMENTS.md for full list)*

### Out of Scope

- Implementation code for the product being researched — engineering's responsibility downstream
- The downstream engineering system — treated as black box
- Visual design tooling — beyond text-based design specifications
- Test suite implementation — system produces harness concept only, not executable tests
- Post-handoff operation — system's job ends when package is delivered
- Per-agent HITL granularity — v1.1 uses run-level only
- LLM model selection per agent — all agents use Claude Sonnet via `claude -p`

## Context

- **Architecture:** LangGraph orchestrator manages state and gates. Each agent is a `claude -p` subprocess that reads artifacts from disk, does LLM reasoning, and writes output to artifact store.
- **Pipeline:** Four phases — Discovery → Definition → Pitch & Evaluation → Handoff. Gate nodes use Orchestrator with rule-based + eval-based decisions.
- **HITL model:** Run-level autonomy dial. `autonomous` = no human stops, circuit breaker on budget + eval plateau. `supervised` = stops at gates. `guided` = stops after every agent.
- **Deployment:** Inside openclaw container. `claude` CLI available. Artifact store on mounted filesystem.
- **PM comms model:** Model B — PM agent communicates directly with stakeholders via Slack/async platform.

## Constraints

- **Framework:** LangGraph ≥0.2
- **LLM:** Claude Sonnet via `claude -p` subprocess (not API SDK)
- **Runtime:** Python ≥3.12
- **Deployment:** openclaw container (filesystem paths, mounted volumes)
- **Production boundary:** No implementation code

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph over CrewAI/AutoGen | Native HITL checkpoints, typed state, resumable execution | ✓ Good |
| Orchestrator-worker pattern | Structural control plane for phase gating | ✓ Good |
| PM agent Model B (direct comms) | Removes human intermediary bottleneck | ✓ Good |
| Artifact store (references not content) | Prevents context window bloat | ✓ Good |
| `claude -p` over API SDK | Each agent gets full Claude Code capabilities (file access, bash). Same pattern as GSD sub-agents. | — Pending |
| Run-level HITL (not per-agent) | Simpler mental model. Per-agent granularity deferred to v1.2 if needed. | — Pending |
| Dual circuit breaker (budget + eval plateau) | Budget prevents runaway cost. Eval plateau prevents useless retries. | — Pending |

---
*Last updated: 2026-04-01 after v1.1 milestone start*
