# Spec: math-voice-tutor

**Status:** draft
**Created:** 20260403T221647Z

## 1. Problem

A parent needs a reliable, repeatable way to run guided math tutoring sessions for a 9-year-old using ChatGPT's voice mode on iOS. The child is working through grade-4 math worksheets and needs step-by-step coaching — not answers. Current approaches (ad hoc ChatGPT chats, Study Mode) fail because: ChatGPT provides incorrect solution approaches ~42% of the time without guardrails, Study Mode isn't grade-calibrated and sometimes gives direct answers, and unstructured chats accumulate stale context that degrades tutor quality over time. The parent needs a structured configuration and SOP that constrains ChatGPT's behavior, keeps sessions clean, and makes the parent the accuracy backstop.

## 2. Scope

**In scope:**
- ChatGPT Project creation with project-only memory (one-time setup)
- Project instructions optimized for grade-4 voice tutoring
- Session kickoff template for per-session context anchoring
- Worksheet prep protocol (crop-first workflow)
- Image protocol for voice mode (crops + pasted-text fallback)
- Session workflow SOP (9 steps, prep through close)
- Parent command reference (8 voice commands + troubleshooting)
- Privacy configuration (data controls for under-13 child)
- Research-backed learning protocols ("Try first", "Explain back")
- Accuracy warning and parent-as-backstop guidance

**Out of scope:**
- Custom software, code, or application development
- Curriculum selection or worksheet creation
- Automated session management or chat creation
- Model training or fine-tuning
- Study Mode integration (explicitly removed — research shows it degrades this use case)
- Multi-child or multi-subject support
- Progress tracking, analytics, or session-over-session metrics
- Any modifications to OpenAI's platform or API usage

## 3. Architecture Decision

**Chosen approach:** A single ChatGPT Project with static project instructions + per-session kickoff template + parent-driven crop workflow. No Study Mode. No code.

**Rationale:** Research shows custom project instructions provide more reliable behavior control than Study Mode for elementary-age tutoring. The crop-first workflow achieves >95% OCR accuracy on printed worksheets, eliminating the primary failure mode (misread problems). The session kickoff template re-anchors context each session, making project-only memory a nice-to-have rather than a requirement — critical since project-only memory doesn't work on iOS yet.

**Alternatives considered:**
- **Study Mode:** Rejected. Not grade-calibrated, gives direct answers unpredictably, designed for advanced learners. Custom instructions are strictly better for this use case.
- **Full-page worksheet upload (no crops):** Rejected. OCR accuracy drops to ~57.5% on complex layouts. Crop-first workflow isolates the active problem and hits >95%.
- **Multiple projects (one per topic/unit):** Rejected. Adds setup overhead with no benefit — session kickoff template handles context isolation.
- **Text-only tutoring (no voice):** Rejected. Voice mode is natural for a 9-year-old and enables hands-free interaction during problem-solving.

## 4. Interfaces

| Interface | Owner | Read/Write | Notes |
|-----------|-------|------------|-------|
| ChatGPT Project (web UI) | OpenAI | Write (one-time setup) | Create project, paste instructions, configure memory |
| ChatGPT Project Instructions | Parent | Write (one-time, occasional updates) | Static text block pasted into project settings |
| ChatGPT Chat (per session) | Parent | Write (each session) | New chat, kickoff template, image crops |
| ChatGPT Voice Mode (iOS) | Parent/Child | Read/Write (each session) | Primary interaction surface |
| OpenAI Data Controls | Parent | Write (one-time) | Disable "Improve the model for everyone" |
| Worksheet source files | Parent | Read | PDF/PNG/photo input for crop prep |
| Cropped problem images | Parent | Write (pre-session) | Prepared on device, uploaded to chat |
| `MATH_VOICE_TUTOR_SPEC_v1.md` | This spec | Write | Final v1.1 spec document in this repo |

## 5. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| ChatGPT Pro subscription | Current | Unlimited Advanced Voice Mode, project features |
| ChatGPT Projects feature | Current | Persistent project instructions, memory isolation |
| ChatGPT Advanced Voice Mode | Current (iOS) | Voice interaction, image upload during voice |
| iOS device with ChatGPT app | Current | Primary session device |
| Image cropping tool | Any (Photos app, markup, etc.) | Pre-session worksheet crop preparation |

## 6. Risks

- **ChatGPT gives wrong math approach (~42% of the time)** — Mitigation: Parent verifies all mathematical reasoning. Explicit accuracy warning in spec. Parent commands ("Check answer only", "Parent mode on") enable quick verification.
- **Child is under 13 (below OpenAI's stated minimum age)** — Mitigation: Parent is account holder and session operator. Disable "Improve the model for everyone". Acknowledge this is a gray area in privacy section.
- **Project-only memory doesn't work on iOS** — Mitigation: Session kickoff template re-anchors context every session. Memory isolation is nice-to-have, not required.
- **Tutor misreads cropped worksheet image** — Mitigation: Paste exact problem text as fallback. Crop-first workflow achieves >95% on clean printed text.
- **Opaque project memory accumulates stale context** — Mitigation: One chat per session. Delete old session chats monthly or when tutor references outdated context.
- **Voice mode daily limits (Plus plan)** — Mitigation: User has Pro (unlimited). Noted for portability if plan changes.
- **AI-tutored overconfidence effect (UPenn)** — Mitigation: "Explain back" protocol after each solved problem catches shallow understanding. "Try first" rule prevents dependency.

## 7. Sequencing

1. **Privacy lockdown** — Disable "Improve the model for everyone" in OpenAI Data Controls. Verify setting is off. Checkpoint: screenshot or confirmation.
2. **Project creation** — Create new ChatGPT Project on web with project-only memory enabled. Name it (e.g., "Math Tutor"). Checkpoint: project exists with project-only memory badge.
3. **Instructions install** — Paste finalized project instructions into project settings. Checkpoint: instructions visible in project settings.
4. **Prep workflow test** — Take one worksheet, crop 2-3 problems, save to device. Checkpoint: crops accessible on iOS.
5. **Dry-run session** — Start a new chat, upload crops, paste session kickoff, start voice. Run through 1-2 problems. Checkpoint: tutor follows instructions, handles crops correctly, parent commands work.
6. **Accuracy validation** — During dry run, independently verify the tutor's math reasoning on each problem. Note any errors. Checkpoint: parent confirms accuracy backstop workflow is viable.
7. **Iterate instructions** — If tutor behavior needs adjustment (too gushy, too verbose, wrong approach), tweak project instructions. Checkpoint: updated instructions produce better behavior on re-test.
8. **Go live** — Run first real session with child. Checkpoint: child engages naturally, parent manages flow with commands, session log captured.

## 8. Tasks

- [ ] Disable "Improve the model for everyone" in OpenAI Settings > Data Controls
- [ ] Create new ChatGPT Project on web with project-only memory enabled
- [ ] Paste finalized project instructions into project settings
- [ ] Finalize `MATH_VOICE_TUTOR_SPEC_v1.md` as v1.1 with all research findings baked in
- [ ] Write parent quick-reference card (8 commands + troubleshooting)
- [ ] Crop 2-3 problems from a sample worksheet for dry-run testing
- [ ] Run dry-run session: upload crops, paste kickoff, test voice, verify parent commands
- [ ] Verify tutor's math accuracy on dry-run problems (parent backstop test)
- [ ] Iterate project instructions based on dry-run findings
- [ ] Run first live session with child
- [ ] Delete spec v1 Study Mode references (already removed from architecture, clean up branch points)

## 9. Acceptance Criteria

- [ ] ChatGPT Project exists with project-only memory enabled
- [ ] Project instructions are installed and produce correct tutor behavior: 1-2 sentence responses, one question at a time, no premature answer reveals
- [ ] Session kickoff template re-anchors context reliably (tutor follows session rules without referencing prior sessions)
- [ ] Crop workflow produces >95% accurate problem reading by the tutor on clean printed worksheets
- [ ] All 8 parent commands work in voice mode: Parent mode on, Kid mode on, Hint only, Next step only, Check answer only, Make it easier, Make it harder, Wrap up
- [ ] Pasted-text fallback works during active voice session (parent can type while voice is active)
- [ ] "Improve the model for everyone" is confirmed disabled
- [ ] Parent can independently verify tutor's math reasoning within the session flow
- [ ] Child engages naturally in voice mode (speaks, listens, responds to questions)
- [ ] Session chat serves as a complete session log after voice ends (transcript visible)
- [ ] v1.1 spec document is finalized with all research findings, warnings, and protocols
