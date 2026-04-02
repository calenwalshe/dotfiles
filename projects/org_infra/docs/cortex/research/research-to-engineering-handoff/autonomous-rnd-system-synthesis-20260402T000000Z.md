# Autonomous R&D System — Full Synthesis & Candidate Evaluation

**Slug:** research-to-engineering-handoff  
**Phase:** research (synthesis of multi-source investigation)  
**Timestamp:** 20260402T000000Z  
**Depth:** deep synthesis  
**Research cost:** $0.137 across 7 Perplexity queries + 2 Jina reads

---

## 1. What We Set Out to Answer

Can Cortex (3-layer cognitive framework), Claude Memory (persistent file-based knowledge), and the Research-to-Engineering Handoff system (7-agent LangGraph pipeline) be combined into a closed-loop autonomous R&D system — one that discovers problems, researches solutions, specs them, implements them, evaluates results, and accumulates knowledge across cycles?

---

## 2. Research Inputs

### 2.1 External Research (7 queries)

| Query | Key Finding |
|---|---|
| Autonomous R&D loop architectures | Every production system (Anthropic research agents, Insilico drug discovery, Radical AI materials, Karpathy autoresearch) follows the same skeleton: DISCOVER → HYPOTHESIZE → EXECUTE → EVALUATE → loop. The differentiator is how tightly the loop is closed and how much human gating exists. |
| AI memory graduation systems | SOTA is tiered memory (working/episodic/semantic/procedural) with active consolidation pipelines. Letta's sleep-time compute, Amazon Bedrock's 89-95% compression, Mem0's multi-scope memory, Cognee's contradiction resolution. Memory is now a computational layer, not storage. |
| Organizational data ingestion | Large orgs build perception agents — always-on ingestion from experimentation platforms, surveys, competitive intel, internal comms. Agent clusters per function (R&D, Product, Engineering) coordinated by an orchestration layer. |
| Postgres+pgvector vs alternatives | Postgres+pgvector is the consensus production answer for canonical truth + vector overlay. Handles up to 100M vectors, 75% cheaper than Pinecone, ACID guarantees. Graph databases (Neo4j/Graphiti) premature until >10% of queries require multi-hop relational reasoning. |
| Claim/evidence/decision epistemology | The critical pattern: retrieval is a proposal, not an update. Cognitive Compression Modules (CCM) achieve near-zero hallucination by requiring schema-governed compression before memory commitment. Every fact needs provenance, confidence, temporal bounds. |
| Human-auditable memory formats | Markdown excels for human-in-the-loop inspection/correction. The projection pattern (DB canonical → Markdown views) is validated as best practice. OpenClaw's hybrid vector+BM25 at 70:30 achieves 89% recall. |
| Karpathy autoresearch architecture | Radical simplicity: single file edits, fixed 5-min experiments, binary keep/discard ratchet, git-as-memory. ~12 experiments/hour. The key insight is constrained action space + clear metric + never stop. |

### 2.2 Internal Artifacts (existing system)

| Component | Status | Location |
|---|---|---|
| Cortex cognitive framework | Built | Layer 1 (GSD workflow), Layer 2 (TDD/debug/review), Layer 3 (reasoning quality) |
| Claude Memory | Built | `~/.claude/projects/*/memory/` — flat files with MEMORY.md index |
| Research-to-Engineering Handoff | Spec'd + contracted, not yet implemented | `docs/cortex/contracts/research-to-engineering-handoff/contract-001.md` |
| GSD executor | Built | Phase-based execution, atomic commits, state tracking |
| Eval framework | Spec'd | 6 dimensions: functional, integration, safety, resilience, style, UX/taste |
| Power Search | Built | Multi-provider web research (Perplexity, Gemini, Tavily, Jina, etc.) |
| Cortex spec pipeline | Built | clarify → research → spec → contract → execute |

---

## 3. The Candidate System

### 3.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    CORTEX (Layer 3 — Reasoning)                   │
│              Anti-hallucination, pushback, security               │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                 CORTEX (Layer 2 — Discipline)              │  │
│  │              TDD, debugging protocols, review               │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │              CORTEX (Layer 1 — Workflow)              │  │  │
│  │  │                                                      │  │  │
│  │  │   LOOP CONTROLLER                                    │  │  │
│  │  │   ┌────────────┐                                     │  │  │
│  │  │   │  DISCOVER  │◀──── Graduated Memory               │  │  │
│  │  │   │            │◀──── Perception Agents               │  │  │
│  │  │   │            │◀──── Codebase Analysis               │  │  │
│  │  │   └─────┬──────┘                                     │  │  │
│  │  │         │ ranked problem list                         │  │  │
│  │  │         ▼                                             │  │  │
│  │  │   ┌────────────┐  ┌──────────────────────────────┐   │  │  │
│  │  │   │  CLASSIFY  │──│ Open-ended? → FULL PIPELINE  │   │  │  │
│  │  │   │            │  │ Bounded?    → AUTORESEARCH   │   │  │  │
│  │  │   └─────┬──────┘  └──────────────────────────────┘   │  │  │
│  │  │         │                                             │  │  │
│  │  │    ┌────┴─────────────────────────────┐               │  │  │
│  │  │    │              │                   │               │  │  │
│  │  │    ▼              ▼                   ▼               │  │  │
│  │  │  FULL PIPELINE   AUTORESEARCH    HYBRID              │  │  │
│  │  │  (7-agent        (ratchet loop   (pipeline specs,    │  │  │
│  │  │   handoff →       on bounded     ratchet executes)   │  │  │
│  │  │   Cortex spec →   problems)                          │  │  │
│  │  │   GSD execute)                                       │  │  │
│  │  │    │              │                   │               │  │  │
│  │  │    └────┬─────────┴───────────────────┘               │  │  │
│  │  │         ▼                                             │  │  │
│  │  │   ┌────────────┐                                     │  │  │
│  │  │   │  EVALUATE  │──── Eval framework (6 dimensions)   │  │  │
│  │  │   │            │──── Ratchet gate (keep/revert)       │  │  │
│  │  │   └─────┬──────┘                                     │  │  │
│  │  │         ▼                                             │  │  │
│  │  │   ┌────────────┐                                     │  │  │
│  │  │   │  GRADUATE  │──── Promote findings to memory      │  │  │
│  │  │   │            │──── Update beliefs                   │  │  │
│  │  │   │            │──── Spawn new questions → DISCOVER   │  │  │
│  │  │   └────────────┘                                     │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              GRADUATED MEMORY STORE                         │  │
│  │                                                             │  │
│  │  Canonical Truth (Postgres + pgvector)                      │  │
│  │  ├── claims (with provenance, confidence, temporal bounds)  │  │
│  │  ├── evidence (source-linked, timestamped)                  │  │
│  │  ├── decisions (with reasoning chain)                       │  │
│  │  ├── experiments (inputs, outputs, metrics)                 │  │
│  │  ├── agent_memory (per-agent namespace)                     │  │
│  │  ├── contradictions (flagged pairs awaiting resolution)     │  │
│  │  └── embeddings (pgvector index)                            │  │
│  │                                                             │  │
│  │  Human-Facing Projections                                   │  │
│  │  ├── MEMORY.md (index, <200 lines)                          │  │
│  │  ├── decision-journal.md                                    │  │
│  │  ├── daily-logs/                                            │  │
│  │  └── curated-bank/ (promoted knowledge pages)               │  │
│  │                                                             │  │
│  │  Recall Layer                                               │  │
│  │  ├── pgvector similarity search                             │  │
│  │  ├── pg_trgm lexical search                                 │  │
│  │  └── retrieval-as-proposal gate (validate before commit)    │  │
│  │                                                             │  │
│  │  Consolidation (async, between sessions)                    │  │
│  │  ├── L0 (raw) → L1 (extracted) → L2 (validated)            │  │
│  │  │   → L3 (actionable) promotion                           │  │
│  │  ├── Contradiction resolution                               │  │
│  │  ├── Staleness decay (source-linked checks)                 │  │
│  │  ├── Domain-tunable compression (89-95%)                    │  │
│  │  └── Markdown projection regeneration                       │  │
│  │                                                             │  │
│  │  Runtime State                                              │  │
│  │  └── LangGraph checkpoints (same Postgres instance)         │  │
│  │                                                             │  │
│  │  Optional Graph Layer (when >10% queries need it)           │  │
│  │  └── Neo4j/Graphiti projection from relational model        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              PERCEPTION AGENTS (data connectors)            │  │
│  │                                                             │  │
│  │  ├── Codebase Agent (git churn, test gaps, lint, TODOs)     │  │
│  │  ├── Experiment Agent (A/B results, ML metrics)             │  │
│  │  ├── Survey/Feedback Agent (NPS, UXR, qualitative)          │  │
│  │  ├── Competitive Intel Agent (Power Search scheduled)       │  │
│  │  ├── Internal Comms Agent (Slack/Telegram via OpenClaw)     │  │
│  │  └── Each produces L0 raw facts → memory store              │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Three Execution Modes

The system classifies each discovered problem and routes to the appropriate execution mode:

**Mode A: Full Pipeline (open-ended research)**
- Unclear metric, multiple stakeholders, needs human judgment
- 7-agent handoff → Cortex spec → GSD execution → HITL gates at every phase
- Example: "What should we build next for the scheduling system?"

**Mode B: Autoresearch (bounded optimization)**
- Clear metric, single file/module, auto-evaluable, revertible
- Tight ratchet loop: edit → run → eval → keep/revert
- No human gates, no stopping, overnight operation
- Example: "Pressure Testing agent produces generic objections 40% of the time"

**Mode C: Hybrid (pipeline specs, ratchet executes)**
- Full pipeline produces the spec and contract
- Execution phase switches to autoresearch mode for bounded subtasks
- HITL gates on spec approval, autonomous on execution
- Example: "Build a new data connector" → pipeline defines what, ratchet optimizes how

### 3.3 Memory Graduation Pipeline

```
L0 — RAW                L1 — EXTRACTED           L2 — VALIDATED          L3 — ACTIONABLE
───────────────────     ───────────────────      ───────────────────     ───────────────────
Slack message           "Deploy of feature Y     Confirmed by 3          Entry in MEMORY.md:
A/B test log             caused 12% drop in       independent sources.   "Feature Y causes
Survey response          metric Z for segment     Survived Pressure       engagement regression
Experiment output        W on 2026-03-15"         Testing review.         in segment Z.
Git diff                                          No contradicting        Mitigation: rollback
                         Source: Slack #eng        evidence found.         + A/B test isolation."
                         + experiment-platform                            
                         Confidence: 0.6          Confidence: 0.9        Confidence: 0.95
                         Timestamp: 2026-03-15    Promoted: 2026-03-18   Promoted: 2026-03-20

PROMOTION CRITERIA:                              PROMOTION CRITERIA:     
• Fact extraction from raw                       • Corroborated by ≥2    
• Source provenance attached                       independent sources   
• Deduplication against existing L1              • Survived pressure test
• Timestamp + domain tag                         • No contradicting L1/L2
                                                 • Relevance score > 0.7 
```

**Consolidation runs between sessions** (sleep-time compute pattern from Letta):
- Scheduled via `/schedule` or cron
- Reviews L0→L1→L2→L3 promotion candidates
- Resolves flagged contradictions
- Decays stale facts (re-checks source pointers)
- Compresses low-fidelity domains (89-95% compression, tunable)
- Regenerates Markdown projections from canonical store

### 3.4 Retrieval-as-Proposal Gate

When any agent recalls memory during execution, the retrieved fact goes through a validation gate before entering working memory:

1. **Existence check** — does the source still exist? (file path, URL, commit SHA)
2. **Freshness check** — is the fact older than its domain's decay threshold?
3. **Contradiction check** — does it conflict with any L2/L3 fact?
4. **Confidence threshold** — is confidence above the required level for this decision type?

Only facts that pass all four checks are committed to the agent's working context. Others are flagged as "proposed but unverified" with the specific failure reason.

This is the epistemological equivalent of Cortex's anti-sycophancy rules — applied to memory rather than reasoning.

---

## 4. Evaluation of the Candidate System

### 4.1 The Five Pressure-Test Queries

These were proposed as the canonical evaluation harness. Here's how the candidate system handles each:

**Q1: "What did we decide about X, and what evidence supported it?"**

| Layer | How it answers |
|---|---|
| Canonical store | `SELECT * FROM decisions WHERE topic = 'X'` → returns decision row with reasoning chain |
| Evidence join | `SELECT * FROM evidence WHERE decision_id = ?` → returns all supporting evidence with provenance |
| Markdown projection | `decision-journal.md` has human-readable entry with linked evidence |
| **Verdict** | Clean. Relational model handles this natively. No graph needed. |

**Q2: "What was true about X last month?"**

| Layer | How it answers |
|---|---|
| Canonical store | `SELECT * FROM claims WHERE topic = 'X' AND valid_from <= '2026-03-02' AND (valid_until IS NULL OR valid_until >= '2026-03-02')` |
| Temporal bounds | Each claim has `valid_from` and `valid_until` timestamps |
| Contradiction log | Shows what changed and why: "Claim C1 invalidated on 2026-03-15 because evidence E7 contradicted it" |
| **Verdict** | Clean. Temporal queries are relational, not graph. Requires disciplined `valid_from`/`valid_until` maintenance. |

**Q3: "What does the system think it knows about Calen, and how confident is it?"**

| Layer | How it answers |
|---|---|
| Canonical store | `SELECT * FROM claims WHERE entity = 'Calen' ORDER BY confidence DESC` |
| Confidence scores | Each claim carries a numeric confidence (0-1) with source count |
| Agent memory | Per-agent namespace shows what individual agents have learned from interactions |
| **Verdict** | Works, but "about Calen" requires entity extraction to have been done correctly at L1. Entity resolution (is "Calen" = "the user" = "Ross"?) is the hard part. This is where a graph layer would help — but only if the entity space is large enough to warrant it. |

**Q4: "Which memories are stale because the source changed?"**

| Layer | How it answers |
|---|---|
| Source pointers | Each L1+ fact stores `source_type` (file, URL, commit, API) + `source_ref` (path, URL, SHA) |
| Staleness check | Consolidation agent re-fetches sources, diffs against stored content |
| Flagging | Stale facts get `stale_since` timestamp and are demoted one level |
| **Verdict** | This is the hardest query. No system solves it cleanly. Source-linked checking works for files and commits (deterministic). Fails for ephemeral sources (Slack messages deleted, URLs that 404). Mitigation: temporal decay as fallback for unverifiable sources. |

**Q5: "Why did the agent recommend building path A instead of path B?"**

| Layer | How it answers |
|---|---|
| Decision store | `SELECT * FROM decisions WHERE topic IN ('path A', 'path B')` → shows the decision and its reasoning |
| Evidence chain | All evidence that was active at decision time, with confidence scores |
| Alternatives considered | Decision row includes `alternatives_rejected` field with reasons |
| Experiment history | If autoresearch mode was used, git log shows the empirical basis |
| **Verdict** | Works if decisions are logged with alternatives. Requires discipline at write-time: every decision must capture what was rejected and why. The handoff system's Pressure Testing agent naturally produces this — it challenges the recommendation, creating a record of the counter-arguments considered. |

### 4.2 Strengths of the Candidate System

**S1: It's mostly built.** Cortex, Memory, GSD, Power Search, eval framework, and the Cortex spec pipeline all exist. The handoff system is spec'd and contracted. The new components (memory graduation, perception agents, loop controller, ratchet gate) are connective tissue, not new systems.

**S2: The dual-mode execution (full pipeline vs. autoresearch) solves the autonomy-safety tradeoff.** Full HITL gates for open-ended problems where human judgment matters. Zero gates for bounded optimization where the metric speaks for itself. No other system in the research cleanly separates these modes.

**S3: Retrieval-as-proposal is a genuine architectural innovation.** No production system we found implements this as a first-class gate. The closest is Amazon Bedrock's consolidation pipeline, but that operates at write-time, not read-time. Applying it at read-time means even correctly stored facts get re-validated before use — catching staleness and contradiction that write-time checks miss.

**S4: The claim/evidence/decision model as canonical truth is epistemologically sound.** Every system that works long-term (including traditional science) separates claims from evidence and tracks provenance. The relational model makes this queryable. The Markdown projections make it auditable. This is the right foundation to build everything else on.

**S5: Autoresearch-mode for bounded problems is high-leverage.** ~12 experiments/hour, ~100 overnight, no human attention required. For problems with clear metrics (test pass rates, eval scores, latency, specificity), this converts idle GPU/compute time into validated improvements.

### 4.3 Weaknesses and Risks

**W1: Complexity.** The full system has 5 major subsystems (Cortex layers, graduated memory, perception agents, dual-mode execution, eval framework), each with multiple components. Integration surface area is large. Risk of building infrastructure that never gets used because the integration work stalls.

*Mitigation:* Build incrementally. MVP is Markdown canonical + SQLite/LanceDB recall + one execution mode. Add Postgres, perception agents, and autoresearch mode only when the simpler version hits limits.

**W2: The memory graduation pipeline has no training data.** Promotion criteria (corroboration threshold, confidence scoring, relevance cutoff) are all hand-tuned heuristics. There's no ground truth for "this fact should be at L2 vs. L3." The system will need calibration runs where a human reviews promotion decisions and provides feedback.

*Mitigation:* Start with conservative promotion (high threshold, human review for L2→L3). Log all promotion decisions. Use the log to tune thresholds over time. This is the same approach the eval framework takes — calibrate from real runs.

**W3: Staleness detection for ephemeral sources is unsolved.** Source-linked checking works for files and git commits. It fails for Slack messages (deleted/edited), URLs (404/changed), and conversation context (not persistently stored). Temporal decay is a blunt fallback.

*Mitigation:* Accept this limitation. Mark ephemeral-source facts with lower maximum confidence. Don't promote them past L2 without corroboration from a durable source.

**W4: The loop controller is the highest-risk new component.** It must classify problems (open-ended vs. bounded), select execution mode, and decide when to loop vs. stop. Bad classification means the wrong execution mode runs — autoresearch on an open-ended problem (dangerous: no safety gates) or full pipeline on a bounded problem (wasteful: 7 agents for a hyperparameter tweak).

*Mitigation:* Start with human classification. The controller proposes a mode, human approves. Automate only after the classifier has been validated against enough examples.

**W5: No production system does general-purpose autonomous R&D yet.** The research is clear: every working system is domain-specific (drug discovery, materials science, ML training). General-purpose autonomous R&D across heterogeneous problem types (product research, infrastructure optimization, feature development) is 5-10 years out by industry consensus.

*Mitigation:* Don't claim general-purpose autonomy. Build for specific, bounded domains first (codebase optimization, agent prompt tuning, eval score improvement). Expand domains one at a time as each is validated.

**W6: Token cost scales with loop frequency.** Autoresearch at 12 experiments/hour is cheap (small context, single-file edits). Full pipeline at 7 agents × multi-model × phase gates is expensive. Running both modes continuously could exceed practical budgets.

*Mitigation:* Budget ceiling per cycle. Model tiering (heavy model for orchestrator/classification, light model for bounded optimization). Track cost per experiment via Power Search's existing cost tracking pattern.

### 4.4 What's Novel vs. What's Known

| Element | Novelty | Assessment |
|---|---|---|
| Tiered memory with graduation | Known (Letta, Bedrock, Mem0) | Implementation on claim/evidence/decision model is a novel application of known patterns |
| Retrieval-as-proposal gate | Novel in this context | Read-time validation of recalled facts is not standard in any production system we found |
| Dual-mode execution (pipeline vs. ratchet) | Novel | No system cleanly separates open-ended research from bounded optimization with mode-switching |
| Cortex behavioral layers wrapping the loop | Novel | Applying anti-sycophancy and TDD discipline to an autonomous R&D loop is unique |
| Sleep-time consolidation | Known (Letta) | Application to graduated memory with source-linked staleness is a novel combination |
| Perception agents for org data | Known (enterprise AI) | Standard pattern at large orgs, but combining with graduated memory + dual-mode execution is new |
| Autoresearch ratchet | Known (Karpathy) | Embedding it as one execution mode within a larger system is the novel contribution |
| Claim/evidence/decision canonical store | Known (epistemology, TMS) | Applying it as the foundation for AI agent memory is novel in implementation, not concept |

### 4.5 Build Sequence Recommendation

**Phase 0: Validate the loop on current infrastructure (1-2 weeks)**
- Pick one real bounded problem (e.g., "improve Pressure Testing agent specificity")
- Run it manually through the full cycle: Memory → Discover → Hypothesize → Execute → Evaluate → Graduate
- Use existing tools (flat-file memory, GSD executor, manual eval)
- Prove the cycle produces value before building infrastructure

**Phase 1: Memory graduation MVP (2-3 weeks)**
- Markdown canonical with YAML frontmatter for claims (confidence, source, temporal bounds)
- SQLite + LanceDB for recall (vector + lexical)
- Manual promotion (human reviews L1→L2→L3)
- Consolidation as a Claude Code scheduled task
- Run the five pressure-test queries against it

**Phase 2: Autoresearch mode (1-2 weeks)**
- Implement ratchet gate in GSD executor
- Write-root enforcement per experiment cycle
- Auto-eval + keep/revert logic
- Test on bounded optimization problem overnight

**Phase 3: Postgres migration + perception agents (3-4 weeks)**
- Migrate canonical store to Postgres + pgvector
- Build 2-3 perception agents (codebase analysis, competitive intel)
- LangGraph checkpoints in same Postgres instance
- Markdown projection generation from Postgres

**Phase 4: Loop controller + classification (2-3 weeks)**
- Problem classifier (open-ended vs. bounded)
- Mode routing (full pipeline vs. autoresearch vs. hybrid)
- Human approval gate on classification (initially)
- Budget tracking per cycle

**Phase 5: Full pipeline implementation (the existing contract)**
- Build the 7-agent handoff system per contract-001
- Wire handoff output → Cortex contract → GSD auto-import
- First end-to-end autonomous run with human gates

**Phase 6: Gate removal (ongoing)**
- Track classifier accuracy over time
- Remove human gates one at a time as trust builds
- Target: bounded optimization fully autonomous, open-ended research human-gated at spec approval only

---

## 5. Final Assessment

**Is this system buildable?** Yes. The hard architectural decisions (canonical truth model, dual-mode execution, memory graduation) are validated by research. The existing components (Cortex, GSD, Memory, Power Search) provide ~60% of the system. The remaining 40% is connective tissue and the memory store upgrade.

**Is it the right system?** The architecture is sound. The risk is over-building before validating the loop. Phase 0 (manual run on current infrastructure) is the critical gate. If the cycle doesn't produce value manually, no amount of infrastructure will fix that.

**What's the single most important thing to build first?** The memory graduation engine (Phase 1). Everything else — perception agents, loop controller, autoresearch mode — depends on the system having a knowledge store that can answer the five pressure-test queries. Without graduated memory, the loop has no substrate.

**What should we explicitly NOT build?** 
- Graph database (premature until relational model is saturated)
- General-purpose autonomy (domain-specific first, always)
- Real-time perception agents (batch/scheduled is sufficient for v1)
- Custom ML models for classification (LLM-as-judge is sufficient for v1)

**The honest assessment:** This is an ambitious system that, if built incrementally with disciplined phase gates, could produce genuine autonomous R&D capability within bounded domains. The architecture is more sophisticated than autoresearch (which it subsumes) and more practical than academic autonomous scientist proposals (which assume capabilities that don't exist yet). The risk is the classic infrastructure trap: building the machine that builds the machine, when you could just build the thing. Phase 0 exists to prevent that trap.

---

## 6. Sources

### External Research
- Perplexity: Autonomous R&D loop architectures (Insilico, Radical AI, Sakana AI Scientist, Ginkgo Bioworks)
- Perplexity: AI memory graduation (Letta/MemGPT, Amazon Bedrock AgentCore, Mem0, Cognee, Zep)
- Perplexity: Organizational data ingestion (Meta, Google, Amazon enterprise AI patterns)
- Perplexity: Postgres+pgvector vs alternatives (benchmarks, production patterns)
- Perplexity: Claim/evidence/decision epistemology (Cognitive Compression Modules, evidence graphs)
- Perplexity: Human-auditable memory (Markdown vs DB, projection pattern, OpenClaw hybrid recall)
- Perplexity: Karpathy autoresearch analysis (loop mechanics, extension patterns)

### Internal Artifacts
- `docs/cortex/contracts/research-to-engineering-handoff/contract-001.md`
- `docs/cortex/specs/research-to-engineering-handoff/spec.md`
- `docs/cortex/specs/research-to-engineering-handoff/gsd-handoff.md`
- `docs/cortex/research/research-to-engineering-handoff/concept-synthesis-20260401T000000Z.md`
- `docs/cortex/evals/research-to-engineering-handoff/eval-plan.md`

### Primary External References
- Karpathy autoresearch: https://github.com/karpathy/autoresearch
- Letta (ex-MemGPT): sleep-time compute, tiered memory architecture
- Amazon Bedrock AgentCore Memory: extraction/consolidation pipeline, 89-95% compression
- Anthropic research agents: orchestrator-worker, 90.2% improvement, 15x token cost
- Insilico Medicine: closed-loop drug discovery ("From Prompt to Drug")
- Radical AI: autonomous materials lab, 370x faster discovery
