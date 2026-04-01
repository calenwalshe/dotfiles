# Research-to-Engineering Handoff System

A seven-agent pre-production intelligence system that takes a product problem statement and produces a validated, schema-typed handoff package for downstream engineering.

## What It Does

The system owns everything **before** implementation. It runs 7 specialist agents through a 4-phase pipeline (Discovery → Definition → Pitch & Evaluation → Handoff) and produces a structured package that engineering can execute against without additional discovery.

**Agents:** Research Orchestrator, UX Research, PM, Data Science, Evaluation, Pressure Testing, Feedback Synthesis

**Output:** Schema-validated handoff package with problem statement, user research, product pitch, requirements, eval criteria, test harness concept, feedback synthesis, risk log, and open assumptions.

## Quick Start

```bash
pip install pydantic langgraph

# Run the full pipeline (autonomous mode)
python -c "
from src.graph.graph import build_graph
from src.graph.run_config import RunConfig, AutonomyLevel

graph = build_graph(RunConfig(autonomy_level=AutonomyLevel.autonomous))
result = graph.invoke({'problem_statement': 'Your problem here'})
print(result['handoff_package'])
"
```

## Run Tests

```bash
python -m pytest tests/ -v
```

## Architecture

- **LangGraph** state machine with typed state, conditional edges, HITL checkpoints
- **Pydantic v2** for all schemas (handoff package, agent artifacts)
- **Artifact store** — filesystem-based, typed read/write/list
- **Agent runner** — `claude -p` subprocess wrapper for LLM-powered agents
- **HITL spectrum** — run-level autonomy: `autonomous` / `supervised` / `guided`
- **Circuit breaker** — token/time budget + eval score plateau detection
- **Eval framework** — rubric-based quality scoring across 10 dimensions

## Project Structure

```
src/
├── agents/          # 7 agents + runner + LLM node factory
├── assembler/       # Handoff package assembler
├── deploy/          # Openclaw container config
├── eval/            # Eval framework + rubrics
├── graph/           # LangGraph state machine, HITL, circuit breaker
├── integrations/    # Comms adapters (mock + Slack)
├── schemas/         # Pydantic models (handoff package + agent artifacts)
└── store/           # Artifact store
tests/               # 123 tests
runs/                # Run artifacts
docs/                # Agent contracts, Cortex specs
```
