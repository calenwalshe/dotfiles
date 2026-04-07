# Next Prompt — Paste after /clear

```
Resume Cortex work on slug: whole-house-audio-llm-control

Mode: execute (contract approved)
Contract: docs/cortex/contracts/whole-house-audio-llm-control/contract-001.md
Spec: docs/cortex/specs/whole-house-audio-llm-control/spec.md

## What this project is
Whole-house audio system: Pi-based Cast agent + Claude Code skill for NL control of Google Cast speakers. 5 audio sources: vinyl turntable (Fluance RT80), CD player (future), Spotify, YouTube/YT Music, local files. Pi (jams, 100.109.14.3) runs FastAPI agent with pychromecast. VPS controls via Tailscale tunnel.

## What's been done
- Clarify → Research (3 dossiers) → Spec → Contract approved
- Pi agent deployed on jams: FastAPI + pychromecast + Icecast + vinyl capture
- 6 Cast devices discovered (Kitchen speaker, Den Wifi, Play Room Wifi, Den TV 3, Upstairs TV, living space audio group)
- UCA202 ordered (Sweetwater L2154177101), awaiting delivery ~Apr 10-14

## What's next
- Build Claude Code skill (~/.claude/skills/cast-control/SKILL.md)
- Test end-to-end when UCA202 + Y-splitter arrive
- Spotify integration (needs Developer credentials)
- Eval plan (pending)

Run /cortex-status to verify current state.
```
