# GSD Handoff: math-voice-tutor

## Objective

Produce a finalized v1.1 Math Voice Tutor spec document and parent quick-reference card that incorporates all research findings, then guide the parent through one-time ChatGPT Project setup and a dry-run validation session. Success = a working ChatGPT Project that produces correct tutor behavior on voice-mode worksheet sessions, with the parent confident in the accuracy-backstop workflow.

## Deliverables

| Artifact | Path |
|----------|------|
| Finalized spec v1.1 | `MATH_VOICE_TUTOR_SPEC_v1.md` (updated in place) |
| Parent quick-reference card | `PARENT_QUICK_REFERENCE.md` |

## Requirements

None formalized.

## Tasks

- [ ] Update `MATH_VOICE_TUTOR_SPEC_v1.md` to v1.1: remove Study Mode references, add accuracy warning, add "Try first" protocol, add "Explain back" step, add OCR troubleshooting note, add privacy under-13 acknowledgment, note project-only memory is web-only
- [ ] Write `PARENT_QUICK_REFERENCE.md`: 8 parent commands, session workflow checklist, troubleshooting tips, accuracy reminder
- [ ] Validate: project instructions produce correct behavior (1-2 sentences, one question, no answer reveal)
- [ ] Validate: crop workflow achieves accurate problem reading
- [ ] Validate: all 8 parent commands work in voice mode
- [ ] Validate: pasted-text fallback works during active voice
- [ ] Validate: "Improve the model for everyone" is disabled

## Acceptance Criteria

- [ ] ChatGPT Project exists with project-only memory enabled
- [ ] Project instructions produce correct tutor behavior: 1-2 sentence responses, one question at a time, no premature answer reveals
- [ ] Session kickoff template re-anchors context reliably
- [ ] Crop workflow produces >95% accurate problem reading on clean printed worksheets
- [ ] All 8 parent commands work in voice mode
- [ ] Pasted-text fallback works during active voice session
- [ ] "Improve the model for everyone" is confirmed disabled
- [ ] Parent can independently verify tutor's math reasoning within session flow
- [ ] Child engages naturally in voice mode
- [ ] Session chat serves as complete session log after voice ends
- [ ] v1.1 spec document is finalized with all research findings

## Contract Link

`docs/cortex/contracts/math-voice-tutor/contract-001.md`
