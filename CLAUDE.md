# Home Directory — Development Hub

## Workflow

This directory is the **planning and context hub** for iterating on the openclaw-fresh bot system.

- **Plan here** (`/home/agent/`) — GSD `.planning/`, research, context artifacts
- **Code there** (`/home/agent/openclaw-fresh/`) — bot source, mounted into Docker container
- **Deploy** — `docker restart openclaw-fresh` (everything is local, no remote push)

## Directory Map

| Path | Purpose |
|------|---------|
| `/home/agent/openclaw-fresh/` | Bot source code (mounted into container) |
| `/home/agent/agent-stack/` | Docker-compose, scheduler, bridges, service configs |
| `/home/agent/machine_config/` | Machine-level config and logs |
| `/home/agent/.planning/` | GSD planning artifacts (when active) |
| `/home/agent/projects/dejan_research/` | **MagmaLab + Carmacks Group research** (see below) |

## Carmacks Group / MagmaLab Research Project

**Start here:** `projects/dejan_research/study/PROJECT_STATE.md` — full file map, conclusions, resume instructions.

| What | Where |
|------|-------|
| Project state & resume guide | `projects/dejan_research/study/PROJECT_STATE.md` |
| Knowledge base (3 papers, 49 claims) | `projects/dejan_research/study/knowledge_base/` |
| Current interpretation | `projects/dejan_research/study/carmacks/output/carmacks_tectonomagmatic_analysis.md` |
| All modeling scripts (reproducible) | `projects/dejan_research/study/carmacks/scripts/` |
| MagmaLab platform source | `projects/dejan_research/magmalab/` |
| Published reports | [melts.calenwalshe.com/carmacks.html](https://melts.calenwalshe.com/carmacks.html) |
| GSD planning (v1.0 + v2.0) | `projects/dejan_research/.planning/` |

**Key finding:** Carmacks Group best explained by hybrid plume–slab window model (12/14 evidence lines). K-enrichment is mantle-derived (AFC proves contamination dilutes K₂O). Most decisive missing data: Sr-Nd-Pb-Hf isotopes.

## Rules

- Never modify files inside the running container directly — edit the host-mounted paths
- After modifying openclaw-fresh files: `docker restart openclaw-fresh`
- After modifying agent-stack services: `cd ~/agent-stack && docker-compose restart <service>`
