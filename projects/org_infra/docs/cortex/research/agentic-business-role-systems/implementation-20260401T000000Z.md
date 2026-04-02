# Research Dossier

**Slug:** agentic-business-role-systems  
**Phase:** implementation  
**Timestamp:** 20260401T000000Z  
**Depth:** standard  
**Sources:** Perplexity sonar-pro · Tavily (3 queries) · Gemini 2.5 Flash  
**Context:** Pre-production cross-functional AI product team — covering Research, PM, Design, DS, Engineering (POC), stopping at the production boundary. Research as orchestration layer.

---

## Summary

The closest existing systems to what you're describing are **MetaGPT** and **ChatDev** — multi-agent frameworks that simulate a software company with defined roles. They are the right shape but the wrong orientation: both are engineering-first, code-delivery-focused, and treat research/PM as input feeders to engineers rather than as the control plane. They have no UX research role, no design role, and no genuine discovery orientation. They ask "how do we build X?" not "what should we build, and does it solve a real problem?"

What you're describing is structurally the inverse: **Research/Intelligence as orchestrator**, with engineering as a downstream consumer of validated, prototype-level outputs. No existing system does this. You're building something new, with MetaGPT/ChatDev as structural reference points and a fundamentally different orientation.

The good news: the architectural patterns are proven. The gaps are in role definitions and orientation, not in orchestration infrastructure.

---

## Findings

### 1. The Existing "AI Software Company" Systems

#### MetaGPT
The most architecturally complete existing system.

**Role set:**
- Product Manager → generates PRD, user stories, competitive analysis
- Architect → translates PRD into system design, API specs, sequence diagrams
- Project Manager → breaks specs into tasks, assigns, tracks
- Engineer → implements code from specs
- QA Engineer → generates/executes tests, produces bug reports

**How roles and handoffs work:**
- Each agent inherits from a `Role` base class with: `name`, `profile`, `goal`, list of `actions`, and `watch` subscriptions to upstream outputs
- Handoff = structured artifact passing. PM writes a PRD → Architect `watch([WritePRD])` triggers → Architect writes design doc → Engineer picks it up
- All agents share a workspace (shared memory/file system); state persists there
- Outputs are typed (Pydantic/JSON schemas), not freeform text — reduces hallucination drift
- Pipeline is sequential by default; some parallelism in newer versions

**What it gets right:**
- Structured artifact handoff (vs. free-form conversation) is the right model for a pre-production pipeline
- Role-based subscriptions (`watch`) cleanly define who cares about whose outputs
- Shared workspace solves state persistence across agents
- SOPs as prompts encode organizational process in a legible way

**What it gets wrong for your use case:**
- Engineering is the end state. Everything else feeds engineering.
- No UX researcher role — user interviews, qual synthesis, usability testing are absent
- No designer role — wireframes, design systems, interaction patterns don't exist
- "PM" generates requirements but doesn't do discovery (market research, user problem validation)
- "Data analyst" exists in some extensions but is shallow; no DS role for experiments, statistical modeling
- Stops at executable code, not at a validated prototype + handoff artifact package

#### ChatDev
Similar premise, different execution model.

- Agents simulate a software company (CEO, CTO, programmer, tester)
- Roles communicate via **dialogue** rather than structured artifacts — agents converse to produce outputs
- More flexible but less reliable than MetaGPT's SOP approach
- Same engineering-first bias; even more limited on research/design/DS

**When to reference ChatDev:** Its dialogue-based handoff model is worth studying for the Discovery phase, where structure is lower and agents need to reason through ambiguity together before producing artifacts.

#### Devin / SWE-agent / OpenDevin class
Advanced autonomous code execution agents.

- Take high-level engineering tasks and autonomously navigate codebases, run tests, debug, commit
- These are **executors**, not orchestrators — they fit inside the Engineering role slot, not at the top of the stack
- For your system: the Engineering agent would be this class of system, invoked by the orchestration layer with a well-specified task

#### Anthropic's multi-agent research system
Referenced in their own engineering blog — the most relevant non-engineering precedent.

- Designed for open-ended research tasks: synthesizing information, finding connections, building intelligence packages
- Multi-agent, parallelized, with a synthesis layer that consolidates findings
- This is the orientation you want: **intelligence-gathering as the primary output**, not code
- Key difference from MetaGPT: the "product" is a research artifact (insight, decision brief, validated assumption) not executable code

---

### 2. What's Missing — The Real Gap

Every existing system is built around a **delivery pipeline**: requirement → design → code → test. The question is always "how do we execute this?" The missing system has a **discovery pipeline**: signal → synthesis → hypothesis → validation → prototype → handoff spec.

| Role | Exists in MetaGPT/ChatDev | Gap |
|------|--------------------------|-----|
| PM (execution-focused) | Yes — generates PRDs | Missing: discovery PM who validates problems before writing requirements |
| Engineer | Yes — primary focus | Exists, but oriented toward production not POC |
| QA | Yes | Exists for code; missing for UX/product validation |
| UX Researcher | No | Entirely absent — qual synthesis, user signals, usability |
| Designer | No | Absent — wireframes, design systems, interaction patterns |
| Data Scientist | Minimal (data analyst) | Missing experiment design, statistical modeling, feasibility analysis |
| Orchestrator/Research | No | No system makes this the control plane |

The gap isn't tooling — it's **orientation and role set**. The infra (LangGraph, shared workspace, structured artifact handoff) exists. What doesn't exist is a system where:
1. Research/Intelligence is the orchestrating agent — it routes, synthesizes, and decides what to build
2. UX, Design, and DS are first-class roles
3. The pipeline terminates at a validated prototype + handoff package, not at shipped code

---

### 3. Architectural Reference — What Your System Should Look Like

Based on what works in existing systems + the gaps:

#### Phase structure (discovery → prototype → handoff)

```
DISCOVERY PHASE
├── Signal Intake Agent          — aggregates user research, market signals, business goals
├── UX Research Agent            — synthesizes qualitative data, generates personas, maps user problems
├── Market/Competitive Agent     — competitive landscape, analogues, positioning
└── Research Orchestrator        — synthesizes above → produces validated problem statement

DEFINITION PHASE
├── PM/Product Strategy Agent    — translates problem statement into product opportunity, KPIs, scope
├── DS/Feasibility Agent         — data availability, experiment design, technical feasibility sketch
└── Research Orchestrator        — validates problem-solution fit → gates progression

DESIGN PHASE
├── Design Agent                 — wireframes, user flows, interaction patterns (LLM + generative UI)
├── UX Validation Agent          — simulated usability scenarios, accessibility, edge case flagging
└── Research Orchestrator        — approves design artifacts before engineering begins

PROTOTYPE PHASE
├── Engineering Agent            — POC code (Devin/SWE-agent class), implements against spec
├── DS Agent                     — data models, basic analytics, experiment schema
└── Research Orchestrator        — validates prototype against problem statement → gates handoff

HANDOFF PACKAGE (output to production engineering)
├── PRD (validated)
├── Design specs + wireframes
├── Technical design document
├── Validated prototype
├── User research findings + personas
├── Data model + experiment design
└── Risk log + open assumptions
```

#### Key architectural decisions

**Artifact-based handoffs (not dialogue-based):**
Follow MetaGPT's model. Each phase produces a structured artifact. Agents subscribe to upstream artifacts via typed interfaces. Freeform conversation between agents is for discovery; outputs are always structured.

**Research Orchestrator as the gate agent:**
Every phase transition requires Orchestrator approval. Orchestrator doesn't just route — it validates that each phase's output actually answers the question from the previous phase. This is the mechanism that makes Research the structural control plane.

**Human-in-the-loop at phase gates:**
Discovery → Definition, Definition → Design, Design → Prototype, Prototype → Handoff. At minimum, a human reviews the Orchestrator's gate decision before phase transition. This is non-negotiable for a system operating at Meta scale with cross-product scope.

**Shared intelligence workspace:**
All agents read/write to a central workspace (vector DB + structured store). The Orchestrator maintains a "current understanding" document that all agents can read. This is how accumulated research context flows through phases without re-generating it.

**Modular role slots:**
Use LangGraph's node model — each role is a node with a typed input/output schema. New roles (e.g., "Legal/Policy Agent" for Meta-specific compliance) can be added as nodes without restructuring the graph.

---

### 4. Handoff Artifacts — What Production Engineering Receives

This is the production boundary. When your system hands off, engineering receives:

| Artifact | Contents | Owner Agent |
|----------|----------|-------------|
| PRD | Problem statement, user stories, scope, success metrics, anti-goals | PM Agent |
| Design Specs | Wireframes, user flows, component spec, accessibility notes | Design Agent |
| Technical Design Doc | Architecture sketch, technology choices, API contracts, data models | Engineering Agent |
| Validated Prototype | Working POC demonstrating core functionality | Engineering Agent |
| User Research Package | Personas, interview synthesis, usability findings, key pain points | UX Research Agent |
| Data/Experiment Design | Required data, experiment schema, feasibility analysis | DS Agent |
| Risk + Assumptions Log | Technical risks, product risks, open questions for prod engineering | Research Orchestrator |

Production engineering's job: scale, harden, secure, integrate. Not rediscover, not revalidate.

---

### 5. Meta-Specific Considerations

**Build on existing infra, don't replace it:**
- Meta's internal workflow orchestration (Tupperware, internal task systems) is the deployment environment, not a competitor
- LangGraph or a similar typed-state-machine framework sits on top of Meta's infra as the agent orchestration layer
- Llama models are the natural LLM backbone — Meta controls the model, reduces external dependency
- Internal data systems (logging, analytics, user research repos) become the Signal Intake Agent's primary sources

**Political positioning via architectural fact:**
Research becomes the orchestration layer because the system is designed that way — not by assertion. The Orchestrator agent is the Research function. It holds the gate authority. Every other function (PM, Design, DS, Eng) is a node that the Orchestrator invokes. This isn't a claim; it's the topology.

**Cross-product by default:**
The system's value increases with breadth. One product team's user research enriches another product's Signal Intake. The shared workspace becomes a cross-product intelligence asset that no single product team could build alone. This is the structural argument for why this lives in Research, not in Product or Engineering.

**The "surprising things" will come from:**
- Discovering which roles actually need to be agents vs. which are better as human-in-the-loop checkpoints
- Finding where Meta's existing data systems are rich enough to make agents powerful, and where they're sparse
- The handoff format — what production engineering actually needs vs. what the system initially produces
- Which agent roles naturally want to merge (e.g., UX Research + PM might want to be tighter than expected)

---

## Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Pipeline model | Sequential (MetaGPT-style) | Graph-based parallel (LangGraph) | LangGraph — phases overlap in reality; Research and Design should run concurrently in Definition phase |
| Handoff format | Document artifacts (PRD, specs) | Structured data schemas | Both — documents for human consumption, structured schemas for agent consumption |
| Gate authority | Orchestrator decides autonomously | Human approves each gate | Human at phase gates, Orchestrator autonomously manages within phases |
| LLM backend | Llama (Meta-native) | External (GPT-4, Claude) | Llama for production, external for bootstrapping/comparison while you calibrate |
| Role granularity | Broad (5-6 roles) | Fine-grained (10+ roles) | Start with 5: Orchestrator, UX Research, PM, Design, Engineering. Add DS and others when you hit the ceiling |

---

## Open Questions (updated)

1. **Does Meta have an existing shared research repository** (user interview recordings, survey data, behavioral analytics aggregated) that the Signal Intake Agent could connect to? The quality of Discovery output depends entirely on the richness of this input.
2. **What's the entry point MVP?** One full discovery-to-prototype run on a real but low-stakes problem — what product, what team, what problem statement? The first run will reveal more about the system's gaps than any amount of planning.
3. **Who owns the handoff format?** The handoff package defines the production engineering API. Getting production engineering to commit to consuming that format is a separate political problem from building the system.

---

## Sources

| Source | Type | Content |
|--------|------|---------|
| Perplexity sonar-pro | Primary synthesis | MetaGPT/ChatDev architecture, role structures, gaps |
| IBM Think | Reference | MetaGPT role specialization, SOP model |
| SmythOS | Comparison | MetaGPT vs ChatDev feature analysis |
| arXiv (Qian et al.) | Academic | Self-organizing multi-agent systems for software development |
| MetaGPT docs | Primary | Framework architecture, role/action model |
| ThirdEye Data | Reference | MetaGPT as virtual software company |
| Medium (PM Stack 2026) | Practitioner | PM-with-prototype model, validation before engineering |
| Anthropic engineering blog | Reference | Multi-agent research system for open-ended tasks |
| AI Requirements Discovery | Reference | Discovery-phase AI, cross-functional alignment |
| arXiv (AI Roles Continuum) | Academic | Blurring research/engineering boundary, cross-functional topology |
| Gemini 2.5 Flash | Cross-reference | Discovery-to-prototype architecture, handoff design, gap analysis |
