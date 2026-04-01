# Milestones

## v1.0 — Rule-Based Intelligence Pipeline

**Shipped:** 2026-04-01

**Key accomplishments:**
- Seven-agent pre-production intelligence system (Research Orchestrator + 6 specialists)
- LangGraph state machine with 4-phase pipeline (Discovery → Definition → Pitch & Evaluation → Handoff)
- Typed handoff package schema (Pydantic v2, 9 sections, JSON Schema derived)
- Artifact store (filesystem-based, typed read/write)
- Orchestrator gate logic with artifact citation and gap reporting
- PM agent comms adapter (abstract + mock)
- Handoff package assembler with schema validation
- Eval framework (rubric-based, 10 dimensions, 6 agents)
- First synthetic run: 10/10 eval checks, schema valid, 4 specific objections

**Stats:**
- Files: ~30 created
- Tests: 69 passing
- Phases: 6 (Schema & Contracts → Infrastructure → Orchestrator → Worker Agents → Integration → Eval & Validation)
- Plans: 8 executed

**Git range:** `985cc4c..cab884e`

**What's next:** LLM-powered agents, HITL spectrum, token tracking, openclaw deployment
