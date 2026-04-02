# Next Session Resume Prompt

Paste this after /clear to restore full context.

---

We are building `research-to-engineering-handoff`: a seven-agent pre-production intelligence system that takes a product problem statement as input and produces a validated, schema-typed handoff package consumable by a downstream engineering system — covering research, product pitch, evaluation criteria, test harness concept, and stakeholder feedback — so that engineering can begin implementation without any additional discovery work.

**Active slug:** research-to-engineering-handoff
**Mode:** spec (pending human approval)
**Active contract:** docs/cortex/contracts/research-to-engineering-handoff/contract-001.md

**Gates:**
- clarify_complete: true
- research_complete: true
- spec_complete: true
- contract_approved: false

**Artifacts on disk:**
- docs/cortex/clarify/research-to-engineering-handoff/20260401T000000Z-clarify-brief.md
- docs/cortex/clarify/agentic-business-role-systems/20260401T000000Z-clarify-brief.md
- docs/cortex/research/research-to-engineering-handoff/concept-synthesis-20260401T000000Z.md
- docs/cortex/research/agentic-business-role-systems/concept-20260401T000000Z.md
- docs/cortex/research/agentic-business-role-systems/implementation-20260401T000000Z.md
- docs/cortex/research/agentic-business-role-systems/concept-anthropic-20260401T000000Z.md
- docs/cortex/specs/research-to-engineering-handoff/spec.md
- docs/cortex/specs/research-to-engineering-handoff/gsd-handoff.md
- docs/cortex/contracts/research-to-engineering-handoff/contract-001.md

**Blocker:** eval_plan is pending — `docs/cortex/evals/research-to-engineering-handoff/eval-plan.md` does not exist. Run /cortex-research --phase evals to produce it (or approve contract and proceed without it).

**Next action:** Human must review and approve spec.md and contract-001.md
- In spec.md: change `Status: draft` → `Status: approved`
- In contract-001.md: check the approval box
Then run /cortex-status again to confirm gates, then proceed to execute phase.
