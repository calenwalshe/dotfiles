# Research Dossier — Implementation Phase

- **Slug:** math-voice-tutor
- **Phase:** implementation
- **Timestamp:** 20260403T221201Z
- **Depth:** standard
- **Search cost:** ~$0.14 (6 queries: 4 Perplexity, 2 Gemini Grounded)

## Summary

Implementation research resolves the remaining open questions from the concept phase and surfaces concrete operational constraints the parent needs to know before running sessions. The three most actionable findings: (1) Plus plan gets only ~15 minutes/day of Advanced Voice Mode — sessions must be tightly run, (2) project-only memory is still web-only as of April 2026 (not on iOS), and (3) voice transcripts appear in the chat after the session but the model may not reference them in future chats without explicit re-pasting.

## Findings

### 1. Voice Mode Daily Limits — Hard Constraint for Session Planning

| Plan | Cost | Advanced Voice Limit | Notes |
|------|------|---------------------|-------|
| Plus | $20/mo | ~15 min/day | 15-min warning before cutoff, then drops to Standard Voice |
| Pro | $200/mo | Unlimited | Highest priority, no caps |
| Free | $0 | 15-30 min/day | Standard Voice only (GPT-4o mini), no video/screenshare |

**Impact on spec:** A Plus subscriber gets one 15-minute tutoring session per day with Advanced Voice. That's tight for a multi-problem worksheet session. The spec should recommend:
- Keep sessions to 1-3 problems max on Plus.
- If more time is needed, the parent can continue via text chat after voice cuts off.
- Pro eliminates this constraint entirely but costs 10x.
- Standard Voice (after cutoff) still works but uses a weaker model and lacks image/screen features.

### 2. Project-Only Memory — Still Web-Only (April 2026)

Project-only memory has **not shipped to iOS or Android** as of April 2026. It remains web + Windows only, despite being announced for mobile in August 2025.

**Impact on spec:** If the parent runs sessions from iOS (which is the natural device for voice mode), project-only memory isolation does NOT apply. The project's conversations will still be grouped together, but the memory isolation guarantee (no outside memories bleeding in) may not function on mobile.

**Workarounds:**
1. Start each chat on the web (where project-only works), then switch to iOS voice. Unclear if the memory isolation persists cross-platform.
2. Accept that memory isolation is best-effort on iOS and rely on the session kickoff prompt to re-anchor the tutor each time.
3. Turn off global memory entirely if contamination is a concern (Settings > Personalization > Memory off — but this disables all memory, including project memory).

**Recommendation:** Option 2 is most practical. The session kickoff template already re-establishes full context, so memory isolation is a nice-to-have, not a requirement. Note this limitation in the spec.

### 3. Voice Transcripts — Visible But Not Auto-Referenced

After a voice session ends, the transcript is added to the same text chat. However, **ChatGPT may not be able to actively reference or recall details from that transcript in subsequent interactions** unless the user manually pastes it into a new text chat.

**Impact on spec:** This is fine for the one-chat-per-session model. The transcript serves as a session log for the parent. If the child needs to revisit a problem from a prior session, the parent would need to open the old chat or paste the relevant transcript excerpt.

### 4. Text Input During Voice Mode

ChatGPT supports multimodal input during active voice sessions. The parent can:
- Speak
- Upload/take photos
- Share screen
- Type text messages

This means the parent can paste exact problem text into the chat **while voice is active** — confirming the spec's source-of-truth protocol works as designed.

### 5. Image OCR Accuracy on Math Worksheets

| Content Type | Accuracy | Notes |
|-------------|----------|-------|
| Clean printed text on white background | >95% | Excellent for typed worksheets |
| Handwritten math | <50-60% | Inconsistent, often misread |
| Small numbers, fractions, units | Variable | Depends on image quality, resolution |
| Complex layouts (tables, multi-column) | ~57.5% | May reinterpret rather than transcribe |

**Impact on spec:** The crop-first workflow is the correct mitigation. A tight crop of a single printed problem on a clean background should hit >95% accuracy. The spec's fallback to pasted text remains important for:
- Handwritten work
- Small numbers or units
- Anything the tutor misreads

**Recommendation:** Add to the spec: "If the tutor misreads a number or symbol from the crop, paste the exact text — don't re-upload the same image."

### 6. AI Tutoring Best Practices (Research-Backed)

Key findings from education research on parent-guided AI math tutoring:

1. **5-minute rule:** Have the child attempt the problem alone for 5+ minutes before engaging the AI tutor. This prevents dependency.
2. **Parent co-pilot effect:** Students with active parent involvement alongside AI show 14 percentage point higher pass rates (Stanford study, ~1000 elementary students).
3. **Explain-back protocol:** After the AI helps solve a problem, ask the child to explain the solution back in their own words. This is the single best check for actual understanding vs. AI-carried completion.
4. **Verify, don't trust:** The parent should independently verify the tutor's mathematical reasoning — the 42% wrong-approach rate from concept research is confirmed.
5. **Session length:** Short focused sessions (15-20 min) outperform long ones for elementary-age children. The 15-min Plus voice limit actually aligns well with this.

**Impact on spec:** These practices are compatible with the existing spec structure. The "Wrap up" parent command already provides a session-end hook. Consider adding:
- A "Try first" protocol note: let the child attempt before starting voice.
- An "Explain back" step after each solved problem.
- A parent-facing reminder that they are the accuracy backstop.

## Trade-offs

| Decision | Upside | Downside |
|----------|--------|----------|
| Plus plan (~15 min voice/day) | Affordable ($20/mo), voice limit enforces short focused sessions | Can only tutor 1-3 problems per session; no flexibility for longer worksheets |
| Pro plan (unlimited voice) | No time constraints | $200/mo is steep for tutoring |
| Accept no project-only memory on iOS | Simplifies setup, works today | Minor risk of memory contamination from other chats |
| Crop-first workflow | >95% OCR on clean crops, parent controls exactly what the tutor sees | Adds 5-10 min prep time before each session |
| One chat per session | Clean logs, fresh context each time | Can't reference prior sessions without manual effort |

## Recommendations for Spec v1.1

1. **Add voice time budget note.** Plus users get ~15 min/day. Recommend 1-3 problems per voice session. Can continue via text after voice cuts off.

2. **Note project-only memory is web-only.** Don't rely on it for iOS voice sessions. The session kickoff template is the real context anchor.

3. **Add "Try first" protocol.** Child attempts the problem for 5 minutes before starting the AI tutor. Add as step 0 in session workflow.

4. **Add "Explain back" step.** After each solved problem, the child explains the solution in her own words before moving on.

5. **Add OCR troubleshooting note.** "If the tutor misreads from the crop, paste the exact text. Don't re-upload — type it out."

6. **Add parent accuracy reminder.** Somewhere visible: "ChatGPT gets the math approach wrong ~40% of the time. You verify the reasoning."

7. **Confirm text input works during voice.** The parent can type/paste into the chat while voice is active — this is a key operational detail for the pasted-text fallback.

## Open Questions (Resolved)

| Question | Resolution |
|----------|-----------|
| Does project-only memory work on iOS? | No — web/Windows only as of April 2026 |
| Daily voice limits for Plus vs Pro? | Plus: ~15 min/day, Pro: unlimited |
| Can you type during voice mode? | Yes — multimodal input supported |
| Does voice transcript appear in chat? | Yes — added after voice ends |
| OCR reliability on worksheet crops? | >95% for clean printed crops; unreliable for handwriting |

## Open Questions (Remaining)

- Has the parent already created a project with default memory that needs to be recreated? (User-specific, not researchable)
- What worksheet curriculum is being used? (User-specific)
- Would upgrading to Pro be worthwhile given session frequency? (Depends on how often sessions run)

## Sources

- Perplexity: ChatGPT project-only memory iOS support status
- Perplexity: ChatGPT Advanced Voice Mode daily limits Plus vs Pro
- Perplexity: AI math tutoring best practices elementary children
- Perplexity: ChatGPT Vision OCR accuracy on math worksheets
- Gemini Grounded: Voice transcript behavior after session ends
- Gemini Grounded: Text input during active voice mode sessions
