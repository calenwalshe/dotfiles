# Research Consolidation — Autonomous R&D Platform

**Date:** 2026-04-02  
**Total research cost:** ~$0.21 (8 Perplexity queries + 2 Jina reads)  
**Status:** Consolidation of all research conducted this session. Consolidator design still requires deeper investigation (see §8).

---

## 1. Research Questions Investigated

| # | Question | Method | Key Finding |
|---|---|---|---|
| 1 | Can Cortex + Memory + Handoff pipeline form an autonomous R&D loop? | Perplexity deep research | Yes — every production autonomous system follows the same DISCOVER → HYPOTHESIZE → EXECUTE → EVALUATE → GRADUATE skeleton. Our system has ~60% of the pieces. |
| 2 | What are SOTA memory systems that graduate knowledge? | Perplexity deep research | Tiered memory (working/episodic/semantic/procedural) with active consolidation pipelines. Memory is now a computational layer, not storage. |
| 3 | How do large orgs ingest heterogeneous data autonomously? | Perplexity deep research | Perception agent clusters per function, coordinated by orchestration layer. Always-on ingestion from experiment platforms, surveys, competitive intel, internal comms. |
| 4 | Postgres+pgvector vs graph-first vs managed memory services? | Perplexity deep research | Postgres+pgvector is consensus production answer. Graph premature until >10% queries need multi-hop. |
| 5 | How do AI systems track WHY they believe things? | Perplexity deep research | Claim/evidence/decision models with provenance. Retrieval-as-proposal (validate before committing to working memory) is the critical gate. |
| 6 | Markdown vs DB-backed memory for human auditability? | Perplexity deep research | Projection pattern (DB canonical → Markdown views) is validated best practice. |
| 7 | How does Karpathy's autoresearch work and where does it fit? | Jina (repo + program.md) + Perplexity | Single-file ratchet loop: edit → run → eval → keep/revert. Embeds as one execution mode within a larger system. |
| 8 | How do composable multi-agent systems avoid becoming monoliths? | Perplexity deep research | Protocol-based communication, typed artifacts in shared store, hexagonal architecture. Components talk to store, not to each other. |

---

## 2. Key Systems Studied

### 2.1 Memory Systems

| System | Architecture | Key Innovation | Relevance |
|---|---|---|---|
| **Letta** (ex-MemGPT) | OS-like memory hierarchy — RAM (working) + disk (persistent). Agents control memory via function calls. | **Sleep-time compute**: background agents reorganize and improve memory during idle periods. Proactive refinement, not lazy incremental updates. | Sleep-time consolidation pattern is directly applicable to our Consolidator. |
| **Amazon Bedrock AgentCore Memory** | Extraction → consolidation pipeline. Custom domain prompts for what to extract. | **89-95% compression** with tunable correctness tradeoff. Extraction and consolidation within 20-40s; retrieval in ~200ms. | Compression rates and domain-tunable extraction are the benchmark to hit. |
| **Mem0** | Multi-scope (user/session/agent), version-controlled facts, knowledge graph linking. | **Three memory scopes**: user-level, session-level, agent-level. Graph structure captures relationships, not just facts. | Per-agent memory namespaces needed for our 7-agent system. |
| **Cognee** | Automatic fact extraction + contradiction resolution. Static (long-term) vs dynamic (recent) split. | **Built-in contradiction detection** with minimal configuration. | Contradiction detection approach worth studying for Consolidator. |
| **Zep** | Semantic + temporal dual search, progressive summarization. | **Temporal search**: find memories by time or meaning. | Temporal validity queries map to our Q2 pressure test. |

### 2.2 Autonomous R&D Systems

| System | Domain | Loop Architecture | Key Lesson |
|---|---|---|---|
| **Karpathy autoresearch** | ML training optimization | Single-file edit → 5min experiment → val_bpb metric → keep/revert. Git-as-memory. ~12 experiments/hour. | Radical simplicity works. Constrained action space + clear metric + never stop = the ratchet pattern. |
| **Anthropic Research Agents** | Factual research | Orchestrator-worker. Lead agent strategizes, parallel subagents gather info. 90.2% improvement vs single-agent. ~15x token cost. | Multi-agent parallel exploration with artifact store (not message passing). |
| **Insilico Medicine** | Drug discovery | "From Prompt to Drug" — advanced reasoning controller coordinates AI agents for target discovery, generative chemistry, automated synthesis, validation. | Closed-loop with human safeguards at high-stakes gates. |
| **Radical AI** | Materials science | First fully autonomous lab — AI-driven experimentation in continuous data feedback loop. 370x faster than traditional. | Tight loop between hypothesis and physical experiment. |
| **Ginkgo Bioworks** | Biology | 52-cart robotic systems + OpenAI orchestration for experiment design, execution, and feedback. | Robotics-AI convergence for physical R&D. |
| **Sakana AI Scientist** | General ML research | Autonomous paper-writing agents: idea generation → experiment → write-up → review. | Broad scope but lower quality than human researchers. |

### 2.3 Storage Architectures

| Approach | Strengths | Weaknesses | When to Use |
|---|---|---|---|
| **Postgres + pgvector** | Unified relational + vector. ACID. SQL joins for hybrid queries. 75% cheaper than Pinecone. 471 QPS at 99% recall on 50M vectors. | Vertical scaling default. Tuning needed for >100M vectors. | Production canonical truth + vector overlay. Our long-term target. |
| **SQLite + LanceDB** | Zero dependencies. Embedded. <10ms reads. | No concurrency. No native vector search (without LanceDB). | MVP. Our current implementation. |
| **Neo4j / Graphiti** | Multi-hop relational reasoning. Temporal graphs. Entity evolution. | Premature unless >10% queries need graph traversal. Adds complexity/cost. | Only after relational model is saturated. |
| **Markdown (flat files)** | Human-inspectable. Zero cost. Grep/ripgrep for search. | No query capability. Unmanageable >5MB. No transactions. | Projection layer (not canonical truth). |
| **Mem0 / Zep (managed)** | Quick to integrate. Built-in consolidation. | No relational truth underneath. Vendor lock-in. | Fast demo, not production canonical. |

---

## 3. Architectural Decisions Made

### Decision 1: Protocol-based composability

**Chose:** Six typed protocols (Claim, Evidence, Decision, Experiment, Problem, Artifact) as the interfaces. Components talk to the store, not to each other.

**Rejected:**
- Direct component-to-component calls → creates monolith coupling
- Message passing between agents → game-of-telephone fidelity loss (Anthropic finding)
- Event-driven pub/sub → over-engineered for current scale

**Evidence:** Anthropic's artifact store pattern. Hexagonal architecture research. Unix pipes metaphor.

### Decision 2: Claim/evidence/decision as canonical truth model

**Chose:** Structured rows with provenance, confidence, temporal bounds. Every fact tracked with WHY it's believed, not just WHAT.

**Rejected:**
- Flat key-value memory → no provenance, no confidence, no temporal queries
- Graph-first → premature without enough validated data
- Unstructured text blobs → not queryable

**Evidence:** Cognitive Compression Modules research (near-zero hallucination via schema-governed commitment). Amazon Bedrock's extraction pipeline.

### Decision 3: Retrieval-as-proposal gate

**Chose:** Every recalled fact goes through validation (source exists? fresh? no contradictions? confidence threshold?) before entering agent working memory.

**Rejected:**
- Trust all recalled facts → hallucination laundering risk
- Only validate at write-time → misses staleness and new contradictions discovered after storage

**Evidence:** ACC research on cognitive compression. No production system implements read-time validation as a first-class gate — this is novel.

### Decision 4: Dual-mode execution (full pipeline vs. autoresearch ratchet)

**Chose:** Classify problems as open-ended or bounded. Open-ended → 7-agent pipeline with HITL gates. Bounded → autoresearch ratchet (edit → run → eval → keep/revert, no stopping).

**Rejected:**
- Single execution mode for all problems → either too heavy (pipeline for hyperparameter tweak) or too dangerous (ratchet for open-ended research)
- Always-human-gated → kills overnight autonomous operation for bounded problems

**Evidence:** Karpathy autoresearch (bounded works autonomously). Insilico/Radical AI (bounded domains with clear metrics succeed). No general-purpose autonomous system works yet.

### Decision 5: SQLite MVP → Postgres migration path

**Chose:** SQLite adapter now. Same StoreProtocol interface. Swap adapter when scale demands it.

**Rejected:**
- Start with Postgres → external dependency, deployment complexity for MVP
- Stay with flat files → can't answer the five pressure-test queries

**Evidence:** Perplexity research on Postgres+pgvector. Our own independence matrix (store is the only non-optional component, so its adapter must be swappable).

### Decision 6: Markdown as projection, not canonical truth

**Chose:** DB is canonical. Markdown is generated from DB. Humans inspect/edit Markdown. Edits sync back.

**Rejected:**
- Markdown as canonical → no query capability, no schema enforcement
- DB only, no Markdown → humans can't inspect or correct easily

**Evidence:** OpenClaw's hybrid architecture (89% recall with vector+BM25). Perplexity research on projection pattern.

---

## 4. Novel Contributions (things not found in existing literature)

| Contribution | What's new | Where it lives |
|---|---|---|
| **Retrieval-as-proposal gate** | Read-time validation of recalled facts before committing to agent working memory. No production system does this. | `src/protocols/store.py` — `validate_recall()` method on StoreProtocol |
| **Dual-mode execution routing** | Classifier determines open-ended vs. bounded → routes to appropriate execution engine. No system cleanly separates these modes. | System design (not yet implemented) |
| **Cortex discipline layers wrapping autonomous loop** | Anti-sycophancy, TDD, and debugging protocols applied to an autonomous R&D system, not just interactive coding. | Cortex behavioral rules (existing) |
| **Six-protocol composability model** | Claim/Evidence/Decision/Experiment/Problem/Artifact as the ONLY interfaces between components. Everything else is a plugin. | `src/protocols/schemas.py` |

---

## 5. What We Built (implemented and tested)

```
src/protocols/
├── __init__.py          # exports all 6 protocol types
├── schemas.py           # Claim, Evidence, Decision, Experiment, Problem, Artifact
│                        #   + ClaimLevel (L0-L3), Domain, SourceType, enums
│                        #   + Contradiction (for consolidator)
├── store.py             # StoreProtocol (abstract) + ValidatedClaim/RejectedClaim
│                        #   + retrieval-as-proposal gate interface
└── sqlite_store.py      # SQLite adapter: full CRUD, query filtering, lexical search,
                         #   retrieval-as-proposal gate implementation

src/perceivers/
├── __init__.py
└── codebase.py          # Standalone: git churn, TODOs, test gaps, lint, activity → L0 Claims
                         #   Run: python -m src.perceivers.codebase --repo . --db knowledge.db

src/projectors/
├── __init__.py
└── markdown.py          # Standalone: store → MEMORY.md, decision-journal.md, experiment-log.md
                         #   Run: python -m src.projectors.markdown --db knowledge.db --output-dir projections/

tests/
└── test_protocols.py    # 40 tests: schema validation, store CRUD, query filtering,
                         #   lexical search, retrieval-as-proposal gate (5 checks),
                         #   all 5 pressure-test queries as acceptance tests
```

**Test results:** 40/40 passing.

**End-to-end verified:** Perceiver scans this repo → writes 11 L0 claims → Projector reads store → generates MEMORY.md with correct stats. Neither component knows the other exists.

---

## 6. What Exists But Isn't Wired Yet

These components were built before this session as part of the handoff system contract:

| Component | Path | Status |
|---|---|---|
| 7 agent schemas (Pydantic v2) | `src/schemas/agent_artifacts.py` | Implemented |
| Handoff package schema | `src/schemas/handoff_package.py` | Implemented |
| Filesystem artifact store | `src/store/artifact_store.py` | Implemented |
| LangGraph graph skeleton | `src/graph/graph.py` | Implemented |
| Graph state types | `src/graph/state.py` | Implemented |
| Circuit breaker | `src/graph/circuit_breaker.py` | Implemented |
| Token tracker | `src/graph/token_tracker.py` | Implemented |
| 7 agent implementations | `src/agents/*.py` | Implemented |
| Eval framework | `src/eval/eval_framework.py` | Implemented |
| Slack adapter | `src/integrations/slack_adapter.py` | Implemented |
| Comms interface | `src/integrations/comms.py` | Implemented |
| OpenClaw deploy config | `src/deploy/openclaw_config.py` | Implemented |

These components use the old `ArtifactStore` (filesystem-based, run_id/agent_id keyed). They can coexist with the new protocol-based store — the new system doesn't replace the old one, it adds a composable knowledge layer alongside it.

---

## 7. What Needs to Be Built Next

| Component | Depends On | Complexity | Status |
|---|---|---|---|
| **Consolidator** | Store (built) | **High** — requires research (see §8) | Research brief written, not yet investigated |
| **Discoverer** | Store (built) | Medium — query store for problems | Not started |
| **Classifier** | Store (built) | Low — four-question heuristic, pure function | Not started |
| **Executor-ratchet** | Store (built), Evaluator | Medium — autoresearch loop with write-root enforcement | Not started |
| **Evaluator** | Store (built) | Medium — extends existing eval framework | Not started |
| **Graduator** | Store (built) | Low — writes results back to store as claims | Not started |
| **More perceivers** | Store (built) | Low each — competitive intel, comms, experiments | Not started |
| **Postgres adapter** | StoreProtocol (built) | Medium — implement same API against psycopg+pgvector | Not started |

---

## 8. Open Research Questions (Consolidator)

These questions must be answered before building the Consolidator. A research brief has been drafted for a research engineer.

### Q1: Contradiction detection at scale
How do Letta, Bedrock, and Cognee detect contradictions between stored facts? What's the actual algorithm? How do they avoid O(n²) pairwise comparison?

**What we know:** Cognee has built-in contradiction resolution. Bedrock's consolidation pipeline resolves contradictions during consolidation. No technical details on the specific algorithms found in our research.

**What we need:** The actual detection mechanism (entailment classification? embedding distance + LLM judge? clustering?).

### Q2: Promotion criteria
What counts as "corroboration from independent sources"? Two claims from the same perceiver run aren't independent. How do production systems determine when to promote?

**What we know:** Bedrock uses custom domain prompts for extraction. Mem0 uses multi-scope memory. No specific promotion heuristics found.

**What we need:** Concrete rules or models for L0→L1 extraction, L1→L2 validation, L2→L3 promotion.

### Q3: LLM vs. rule-based consolidation
What's the minimum viable LLM involvement? Can extraction be rule-based with LLM only for ambiguous cases?

**What we know:** Letta uses LLM for sleep-time compute. Bedrock uses LLM for extraction. Both are LLM-heavy.

**What we need:** Cost analysis at 100/1000/10000 claims. Hybrid approach (cheap classifier + LLM fallback) feasibility.

**Budget target:** <$0.50 per consolidation cycle at 1000 claims.

### Q4: Staleness decay functions
How do production systems handle temporal validity? Time-based, source-based, usage-based, or combination?

**What we know:** Our retrieval-as-proposal gate checks source file existence and valid_until dates. No research found on specific decay functions.

**What we need:** Decay rates per domain. Source-linked re-check strategy.

### Q5: Lossy compression boundaries
Where does compression destroy value? What's the actual strategy — summarization, deduplication, abstraction?

**What we know:** Bedrock achieves 89-95% compression. "Slightly lower correctness on factual recall tasks" but effective for inference tasks.

**What we need:** Per-domain compression rules. What's safe to compress vs. what must keep full fidelity.

---

## 9. Five Pressure-Test Queries (Acceptance Criteria)

These queries are the system's acceptance test. All five are implemented as tests in `tests/test_protocols.py` and pass.

| # | Query | How It Resolves | Tested? |
|---|---|---|---|
| 1 | "What did we decide about X, and what evidence supported it?" | `query_decisions(topic=X)` JOIN `query_evidence(decision.evidence_ids)` | Yes |
| 2 | "What was true about X last month?" | `query_claims(topic=X, valid_at=date)` using `valid_from`/`valid_until` bounds | Yes |
| 3 | "What does the system think it knows about Calen, and how confident is it?" | `query_claims(entity='Calen')` ordered by confidence DESC | Yes |
| 4 | "Which memories are stale because the source changed?" | `validate_recall()` checks source file existence, temporal validity, contradictions | Yes |
| 5 | "Why did the agent recommend path A over path B?" | `query_decisions(topic=X)` → `chosen_option` + `alternatives_rejected` with reasons | Yes |

---

## 10. Cost Summary

### Research costs this session
| Provider | Queries | Cost |
|---|---|---|
| Perplexity | 8 deep research queries | $0.172 |
| Jina | 2 URL reads (autoresearch repo + program.md) | $0.0002 |
| **Total** | | **$0.172** |

### Projected operational costs
| Component | Per-cycle | Frequency | Monthly |
|---|---|---|---|
| Perception agents (3) | ~$0.05 each | 4×/day | ~$18 |
| Consolidation agent | ~$0.10 | 1×/day | ~$3 |
| Loop controller | ~$0.15 | 1-3×/day | ~$14 |
| Mode B ratchet (per experiment) | ~$0.02-0.05 | ~100/week | ~$15 |
| Mode A full pipeline (per run) | ~$2-5 | 1-2×/week | ~$30 |
| Deep research (Power Search) | ~$0.02-0.03 | ~20/week | ~$2 |
| SQLite/Postgres | flat | always-on | ~$0-15 |
| **Total** | | | **~$100/mo** |

---

## 11. Sources

### External (Perplexity + Jina)
- Autonomous R&D loop architectures (Insilico, Radical AI, Sakana, Ginkgo, Anthropic)
- AI memory graduation (Letta/MemGPT, Amazon Bedrock AgentCore, Mem0, Cognee, Zep)
- Organizational data ingestion (enterprise AI agent patterns)
- Postgres+pgvector vs alternatives (benchmarks, scaling limits)
- Claim/evidence/decision epistemology (Cognitive Compression Modules, evidence graphs)
- Human-auditable memory (Markdown projection pattern, OpenClaw hybrid recall)
- Karpathy autoresearch (https://github.com/karpathy/autoresearch — repo, program.md, architecture analysis)
- Composable multi-agent architectures (protocol-based communication, hexagonal architecture, plugin patterns)

### Internal artifacts
- `docs/cortex/contracts/research-to-engineering-handoff/contract-001.md`
- `docs/cortex/specs/research-to-engineering-handoff/spec.md`
- `docs/cortex/specs/research-to-engineering-handoff/gsd-handoff.md`
- `docs/cortex/specs/research-to-engineering-handoff/system-design.md`
- `docs/cortex/research/research-to-engineering-handoff/concept-synthesis-20260401T000000Z.md`
- `docs/cortex/research/research-to-engineering-handoff/autonomous-rnd-system-synthesis-20260402T000000Z.md`
- `docs/cortex/evals/research-to-engineering-handoff/eval-plan.md`
