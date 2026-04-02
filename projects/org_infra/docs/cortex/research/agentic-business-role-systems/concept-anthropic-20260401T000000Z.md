# Research Dossier — Anthropic Multi-Agent Research System

**Slug:** agentic-business-role-systems  
**Phase:** concept (focused topic)  
**Topic:** Anthropic's multi-agent research system — architecture and applicability as reference model  
**Timestamp:** 20260401T000000Z  
**Depth:** standard  
**Sources:** Jina Reader (anthropic.com/engineering/multi-agent-research-system) · Tavily (2 queries) · Gemini 2.5 Flash · Simon Willison analysis · ByteByteGo · ZenML LLMOps database

---

## Summary

Anthropic's multi-agent research system (which powers the Claude Research feature) is the most directly relevant production reference for the Meta Intelligence Orchestration system. It's the only publicly documented system where:
- Intelligence-gathering (not code delivery) is the primary output
- An orchestrator agent coordinates specialized subagents running in parallel
- The architecture is documented at engineering depth, not marketing depth

The system is also the closest existing implementation to what the Meta system needs to become — with one critical difference: Anthropic's system retrieves and synthesizes *factual information*, while the Meta system needs to synthesize *product intelligence* (user problems, design options, feasibility) and produce a *validated brief*, not an answer. That shift changes the orchestrator's job substantially, and it changes what "correct" means for evaluation.

The architecture is a strong reference. The orientation needs to rotate.

---

## The Architecture

### Orchestrator-Worker Pattern

```
User query
    ↓
Lead Agent (Claude Opus 4) — orchestrator
    ├── Decomposes query into parallel subtasks
    ├── Writes detailed task descriptions for each subagent
    │   (objective, output format, tools to use, task boundaries)
    ├── Spawns N subagents simultaneously
    └── Synthesizes results into final output

Subagent 1 (Claude Sonnet 4) — worker
Subagent 2 (Claude Sonnet 4) — worker
Subagent N (Claude Sonnet 4) — worker
    Each: runs independently, has own context window, tools, prompts
    Each: writes outputs to external artifact store
    Each: passes lightweight reference back to lead agent (not full content)
```

### Key Engineering Decisions (and why they matter)

**1. Artifact store, not message passing**
Subagents write full outputs to an external filesystem. Lead agent receives a reference, not the content. This prevents the "game of telephone" — where large outputs get summarized repeatedly through conversation history and lose fidelity. For a product intelligence system, this is critical: a 40-page user research synthesis can't be passed as a string through the orchestrator.

**2. Detailed task descriptions, not vague delegation**
Early versions allowed the lead agent to give short instructions like "research the semiconductor shortage." This caused subagents to duplicate work or diverge. The fix: each task description must include objective, output format, tool guidance, and explicit task boundaries. Without this, multi-agent systems do the same work multiple times or leave gaps.

**3. Broad-first, narrow-second search strategy**
Agents prompted to start with broad queries (survey the landscape) then narrow based on what they find. Mimics expert human researcher behavior. Specific queries run first returned poor results; broad orientation first, then specificity.

**4. Agents as their own prompt engineers**
Claude 4 models, given failing scenarios, can analyze why something went wrong and suggest prompt improvements. Anthropic built a tool-testing agent that tried a flawed tool repeatedly, then rewrote its own description to avoid the failure. Result: 40% reduction in task completion time for subsequent agents hitting the same tool.

**5. Resilient error handling**
Agents informed when tools fail; they adapt rather than crash. Combined with retry logic and durable checkpoints — agents resume from point of failure, not from scratch. Non-negotiable for long-running research sessions.

**6. Model tiering**
Opus 4 (expensive, high reasoning) as orchestrator. Sonnet 4 (cheaper, fast) as workers. Token efficiency via specialization. The orchestrator reasoning about *what to do* is worth the cost; subagent execution is not.

---

## Performance Numbers

| Metric | Value |
|--------|-------|
| Performance improvement vs. single-agent | **90.2%** on internal research eval |
| Token usage vs. standard chat | **~15x** more |
| Token usage vs. single-agent Claude | **~4x** more |
| % of performance variance explained by token usage | **80%** |
| Other explanatory factors | Tool call frequency (10%), model choice (10%) |

**Implication:** The performance gain is real and large. The cost is also real and large. This architecture is only viable for tasks where the value of the output justifies 15x token cost. For a pre-production product intelligence system generating validated briefs that determine engineering investment — the value is there. For casual queries — it isn't.

---

## What's Architecturally Novel (vs. standard orchestrator-worker)

Standard orchestrator-worker is decades old. What Anthropic adds:

1. **LLM as intelligent planner** — the orchestrator isn't a rules engine, it dynamically decides how to decompose and what to delegate based on reasoning
2. **Self-improving prompts** — agents rewrite their own instructions based on failure analysis; the system learns without retraining
3. **LLM-driven error recovery** — agent is told "this tool is failing" and reasons about how to continue; not just retry, but adaptive replanning
4. **Artifact store pattern for LLM output chains** — novel application of an old idea (write outputs to storage, pass references) specifically to solve the LLM context/fidelity problem

The orchestrator-worker shape is standard. The intelligence *inside* each role is the novel part.

---

## Applying This to the Meta Intelligence System

### What maps directly

| Anthropic component | Meta Intelligence equivalent |
|---------------------|------------------------------|
| Lead Agent (Opus 4) | Research Orchestrator agent |
| Subagent (Sonnet 4) | UX Research / PM / Design / DS / Eng agents |
| Artifact store | Shared intelligence workspace (per-phase artifact store) |
| Detailed task descriptions | Phase gate artifacts (each phase produces a structured brief that defines the next phase's task) |
| Broad-first → narrow | Discovery phase → Definition phase → Design phase |
| Model tiering (Opus/Sonnet) | Llama large (orchestrator) / Llama smaller (workers) |
| Self-improving prompts | Orchestrator refinement loop after each full run |

### What needs to change

**The orchestrator's job is different.**

Anthropic's lead agent aggregates correct answers. The Meta Orchestrator synthesizes *product intelligence* — it needs to:
- Resolve conflicts between agents (UX Research says users want X, DS says usage data contradicts it)
- Gate phase transitions (is the problem statement validated well enough to proceed to design?)
- Produce a structured brief as output, not a factual answer
- Hold the "current best understanding" that all agents read and update

This makes the orchestrator more like a **principal investigator** than a search aggregator. It reasons about coherence, not just completeness.

**Subagents have creative/synthesis roles, not just retrieval roles.**

Anthropic's subagents retrieve and extract. For the Meta system:
- UX Research agent synthesizes qual data, generates personas — it's not retrieving facts, it's interpreting signal
- Design agent generates wireframe concepts — it's producing artifacts, not summarizing sources
- PM agent reasons about prioritization and trade-offs — it's making judgment calls

These agents need richer prompting, more output format specification, and different evaluation criteria than "did you find the right fact?"

**"Correct" is harder to define.**

Anthropic can evaluate factual accuracy on research evals (BrowseComp). For product intelligence:
- Is this persona accurate? (Compared to what?)
- Is this problem statement well-formed?
- Does this wireframe address the identified user need?

The eval framework needs to be designed from scratch for this use case.

---

## Failure Modes Specific to Product-Team Context

| Failure Mode | Description | Mitigation |
|---|---|---|
| **Hallucination laundering** | Subagent hallucinates a user insight; orchestrator synthesizes it into a "validated" brief | Require source citations in all subagent outputs; human review at phase gates |
| **Bias amplification** | Subagents trained on biased data produce biased personas/recommendations | Diverse source inputs; bias audit at UX Research agent output |
| **Cost overrun at scale** | 15x token cost × cross-product scope × parallel runs = fast budget burn | Token budgets per run; model tiering; route simple queries to single-agent path |
| **Interpretability collapse** | Hard to explain *why* the orchestrator reached a conclusion across N parallel agents | Structured trace logging; orchestrator must cite which subagent output informed each conclusion |
| **Latency for interactive use** | Parallel LLM chains still take minutes; not suitable for real-time interaction | Design for async use — results delivered after a run completes, not streamed |
| **Vague delegation recurrence** | Without detailed task descriptions, agents duplicate work | Enforce structured task spec format at orchestrator level; reject vague delegations |

---

## Recommendations for the Meta System

1. **Adopt the artifact store pattern immediately.** Don't pass subagent outputs through the orchestrator as text. Each agent writes a structured artifact (JSON + prose); orchestrator reads references. This is non-negotiable at scale.

2. **Treat the orchestrator's gate function as the core design problem.** The hardest engineering question isn't "can agents do research?" — it's "how does the orchestrator decide when a phase output is good enough to proceed?" Design the gate logic before designing the agents.

3. **Use model tiering from day one.** Llama large (or equivalent) for the Research Orchestrator; lighter models for subagents. The orchestrator's reasoning budget matters; worker efficiency matters more.

4. **Build the eval framework in parallel with the system.** Anthropic's 90.2% improvement was measured against a defined eval. Without an eval framework, you can't know if the system is working. The eval for product intelligence is harder to design than for factual research — start now.

5. **First run on a single, bounded problem.** Take one real product question (e.g., "what problem should [Feature X] solve for [User Segment Y]?"), run a full cycle with all agent roles, and use the output quality as calibration data. Everything else is theory until you have one real run.

---

## Sources

| Source | Type | Key Content |
|--------|------|-------------|
| anthropic.com/engineering/multi-agent-research-system | Primary (Jina) | Full architecture, artifact store, task description design, error handling |
| simonwillison.net/2025/Jun/14/multi-agent-research-system/ | Analysis | Token cost data, BrowseComp eval, breadth-first pattern |
| blog.bytebytego.com | Synthesis | Self-prompt engineering, 40% task time reduction |
| zenml.io/llmops-database | Case study | 90.2% improvement figure, production engineering details |
| linkedin.com (Omar Sar) | Summary | Orchestrator-worker design, parallel breadth-first, 15x token cost |
| anthropic.com/engineering/building-effective-agents | Primary | Workflow vs. agent taxonomy, 5 core patterns |
| Gemini 2.5 Flash | Cross-reference | Novel vs. standard architecture, product-team adaptations, failure modes |
