# Research Dossier — Synthesis

**Slug:** research-to-engineering-handoff  
**Phase:** concept (synthesis of prior slug research)  
**Timestamp:** 20260401T000000Z  
**Depth:** synthesis  
**Source dossiers:**
- docs/cortex/research/agentic-business-role-systems/concept-20260401T000000Z.md
- docs/cortex/research/agentic-business-role-systems/implementation-20260401T000000Z.md
- docs/cortex/research/agentic-business-role-systems/concept-anthropic-20260401T000000Z.md

---

## Context

The prior slug (`agentic-business-role-systems`) explored the full landscape of multi-agent business systems and was refined through conversation into a specific problem frame: a **pre-production intelligence system** that produces a structured handoff package for downstream engineering. This dossier consolidates the findings relevant to that refined framing.

---

## Key Findings (relevant to this slug)

### No existing system matches the target

MetaGPT and ChatDev are the closest structural references but are engineering-first — they ask "how do we build X?" not "what should we build?" No existing system has UXR, Designer, Evaluation, or Pressure Testing roles. No existing system positions Research/Intelligence as the orchestration layer.

### Anthropic's architecture is the closest reference

Orchestrator-worker pattern, artifact store (not message passing), detailed task descriptions per subagent, model tiering (large for orchestrator, smaller for workers), broad-first narrowing strategy. 90.2% improvement vs. single-agent. ~15x token cost. The orientation (fact retrieval vs. product intelligence synthesis) needs to change; the architecture is solid.

### Proven architectural patterns

- **Artifact store over message passing** — prevents game-of-telephone fidelity loss in multi-stage chains
- **Typed state handoffs** — Pydantic/JSON schemas between agents reduce hallucination drift
- **LangGraph for phase-gated pipelines** — typed state machine, conditional edges, HITL checkpoints, resumable from failure
- **Role subscriptions (watch pattern)** — agents subscribe to upstream artifacts rather than being explicitly called
- **Model tiering** — Llama large for orchestrator reasoning, smaller for worker execution

### The handoff package is the API contract

What engineering receives must be consumable without additional discovery. Minimum: validated problem statement, product pitch, prioritized requirements, eval criteria, test harness concept, feedback synthesis, risk log. Format: JSON schema (machine-readable) + prose documents (human-readable).

### Eval framework is the hardest unsolved problem

Anthropic evaluates factual accuracy (BrowseComp). Product intelligence output has no equivalent ground truth. "Is this persona accurate?" has no clean answer. Rubric-based LLM-as-judge + human spot-checks at phase gates is the current best approach, but needs calibration from real runs.

---

## Assumptions Backed by Research

| Assumption | Evidence |
|---|---|
| Orchestrator-worker is the right pattern | Anthropic production system, MetaGPT, industry consensus |
| Artifact store > message passing | Anthropic engineering blog (game-of-telephone finding) |
| LangGraph > CrewAI for phase-gated HITL | Framework comparison research (LangGraph only framework with native HITL) |
| Model tiering reduces cost without quality loss | Anthropic: Sonnet 4 workers + Opus 4 orchestrator outperforms single Opus 4 |
| No existing system has UXR/Design/Evaluation roles | Implementation dossier role gap table |
| Handoff package must be schema-typed | MetaGPT Pydantic output pattern; downstream engineering consumption requirement |
