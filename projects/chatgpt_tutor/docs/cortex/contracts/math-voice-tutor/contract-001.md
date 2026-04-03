# Contract: math-voice-tutor-001

**ID:** math-voice-tutor-001
**Slug:** math-voice-tutor
**Phase:** execute
**Status:** pending

## Objective

Produce the finalized v1.1 Math Voice Tutor spec and parent quick-reference card so the parent can set up a ChatGPT Project and run validated voice-mode tutoring sessions for a 9-year-old on grade-4 math worksheets.

## Deliverables

- `MATH_VOICE_TUTOR_SPEC_v1.md` — Updated to v1.1 with all research findings baked in
- `PARENT_QUICK_REFERENCE.md` — 8 parent commands, workflow checklist, troubleshooting, accuracy reminder

## Scope

**In scope:**
- Finalizing the spec document with research-backed additions (accuracy warning, "Try first", "Explain back", OCR notes, privacy acknowledgment, project-only memory limitation)
- Removing Study Mode from the spec entirely
- Writing the parent quick-reference card
- Documenting the one-time setup steps and per-session workflow

**Out of scope:**
- Actually creating the ChatGPT Project (parent does this manually)
- Running tutoring sessions (parent does this)
- Building any software or code
- Curriculum or worksheet selection

## Write Roots

- `MATH_VOICE_TUTOR_SPEC_v1.md`
- `PARENT_QUICK_REFERENCE.md`

## Done Criteria

- [ ] `MATH_VOICE_TUTOR_SPEC_v1.md` updated to v1.1 with: Study Mode removed, accuracy warning added (~40% wrong-approach rate), "Try first" protocol (5 min independent attempt), "Explain back" step, OCR troubleshooting note, privacy under-13 acknowledgment, project-only memory web-only note
- [ ] `PARENT_QUICK_REFERENCE.md` created with: all 8 parent commands with descriptions, session workflow checklist (9 steps), troubleshooting tips (OCR misread, tutor too gushy, child frustrated), accuracy reminder
- [ ] Project instructions block is finalized and ready to paste
- [ ] Session kickoff template is finalized and ready to paste
- [ ] Privacy section explicitly acknowledges under-13 age policy gap and states "Improve the model for everyone" must be disabled

## Validators

- Manual review: all 9 spec sections from v1 are present and updated
- Manual review: Study Mode is not mentioned as an option anywhere in the spec
- Manual review: parent quick-reference card covers all 8 commands
- Manual review: privacy section includes under-13 acknowledgment
- Grep: `grep -i "study mode" MATH_VOICE_TUTOR_SPEC_v1.md` returns zero matches (or only in a "removed" context)

## Eval Plan

`docs/cortex/evals/math-voice-tutor/eval-plan.md` (pending)

## Approvals

- [ ] Contract approved for execution
- [ ] Evals approved

## Rollback Hints

- Revert `MATH_VOICE_TUTOR_SPEC_v1.md` to git HEAD (original v1)
- Delete `PARENT_QUICK_REFERENCE.md`
- No external state to restore — all deliverables are local files
