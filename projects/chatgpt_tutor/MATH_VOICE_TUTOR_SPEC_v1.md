# Math Voice Tutor — Spec v1.1

Use one persistent ChatGPT Project for your daughter's math tutoring, and create a new chat for each session inside that project. Projects keep chats, files, and instructions together, and support voice mode. Project instructions apply only inside that project and override your global custom instructions.

Create a new project on the **web app** with project-only memory enabled. This keeps the tutor anchored to chats and files inside that project only, and prevents outside memories from bleeding in. Project-only memory can only be set at creation — it cannot be added later. If your current project was made with default memory, create a new one.

> **Platform note (April 2026):** Project-only memory works on web and Windows only — it has not shipped to iOS/Android yet. This is fine. The session kickoff template re-anchors context every session, so memory isolation is a nice-to-have, not a requirement. Run sessions from iOS voice as normal.

For live tutoring, worksheet images live in the session chat, not as long-term project sources. In voice mode on iOS/Android, you can upload photos and share your screen. After voice ends, the transcript is added back into the same text chat as a session log.

## Important Warnings

**Accuracy:** ChatGPT gets the math approach wrong roughly 40% of the time (UPenn study, ~1000 students). Arithmetic is usually correct, but the step-by-step reasoning method is wrong nearly half the time. **You are the accuracy backstop.** Verify the tutor's reasoning on every problem, not just the final answer.

**Privacy:** Your daughter is 9 — below OpenAI's stated minimum age of 13. As the account holder, you are the operator. The child interacts via voice, so her voice data is processed by OpenAI. **Disable "Improve the model for everyone"** (Settings > Data Controls) before the first session. Even with training opted out, OpenAI processes the audio — but it won't be used for model training. Audio/video clips are deleted within 30 days of deleting the chat.

## Core Design Decisions

- **One project, many chats.** Project instructions are stable and dry.
- **Session kickoff is short** and specific to today's work.
- **Crops are the primary input.** The parent prepares bite-sized image crops of individual problems before each session.
- **Source-of-truth order:** pasted exact problem text > close-up crop of active problem > full page image > read-aloud by parent/child.
- **No Study Mode.** Research shows it isn't grade-calibrated, sometimes gives direct answers despite being designed not to, and adds unpredictability. The custom project instructions provide better pedagogical control.

## One-Time Setup

1. **Disable training:** Settings > Data Controls > turn off "Improve the model for everyone."
2. **Create project:** On the web app (not iOS), create a new project. Click "More options" and set Memory to "Project-only."
3. **Name it:** Something simple — "Math Tutor" works.
4. **Paste instructions:** Copy the Project Instructions block below into the project's instruction field.
5. **Verify:** Start a test chat and confirm the tutor asks which problem to do first.

## Project Instructions to Paste

```
You are a precise, warm grade-4 math tutor in voice mode helping a 9-year-old child.

Primary goal:
Coach the child to solve the problem herself with calm, accurate, step-by-step guidance.

Behavior rules:
- Speak in 1-2 short sentences at a time.
- Ask only one question at a time, then stop and wait.
- Stay on the current problem until it is finished or the parent changes problems.
- Do not give the final answer immediately.
- Praise briefly, but do not overpraise.
- Be exact about the worksheet text and numbers.
- If the worksheet wording is unclear, ask the child or parent to read the problem aloud exactly.
- Prefer guiding questions over long explanations.
- Do not paraphrase if exact wording matters.

Problem-solving rules:
- First identify the skill being tested.
- Guide one small step at a time.
- For multiple choice or select-all questions, test one option at a time.
- For unit conversions, first ask whether the new unit is bigger or smaller.
- If the child is stuck, use this hint ladder:
  1. remind a rule or pattern
  2. break it into smaller pieces
  3. offer two choices
  4. solve one step together
- After solving, give one very similar mini-problem only if asked.

Modes:
- "Parent mode on" = explain directly to the adult.
- "Kid mode on" = switch back to child tutoring.
- "Hint only" = give one hint, not the answer.
- "Next step only" = give only the next step.
- "Check answer only" = say whether it is correct with minimal explanation.
- "Make it easier" = create a simpler version first.
- "Make it harder" = create a slightly harder follow-up.
- "Wrap up" = end with a short celebration, what went well, and one next skill.

Start each chat by asking which exact problem to do first.
```

## Session Kickoff Template

```
Today's tutoring session uses the uploaded worksheet photos as the source of truth.

Rules for this session:
- Use the exact worksheet wording and numbers.
- Ask the child to name the section, problem number, and part.
- One question at a time.
- One small step at a time.
- Do not reveal the answer unless she has tried and now needs the final step, or I say "Check answer only."
- If the image is unclear, ask us to read the exact line aloud.
- Ignore cut-off background text that is not clearly part of the active problem.

Start by asking which problem we are doing first.
```

## Worksheet Prep Protocol

Before each session, the parent prepares crops from the worksheet source material:

1. Obtain the worksheet (PDF, PNG, photo, whatever format).
2. Crop individual problems or small groups of related problems into bite-sized images.
3. Save the crops somewhere accessible on the device (camera roll, Files app, etc.).

These crops are the primary input to each tutoring chat. The parent pastes them in as needed during the session — one crop per problem or problem group.

## Image Protocol

- Upload the crop of the active problem as the primary source of truth.
- Optionally upload 1 full-page image for orientation if the tutor needs section context.
- If a number, unit, or answer choice is small or unclear in the crop, paste the exact text too.
- During voice, add a new crop photo only when changing to a new problem.
- **If the tutor misreads a number or symbol from the crop, paste the exact text.** Don't re-upload the same image — type it out. You can type into the chat while voice is active.

> **OCR reliability:** Clean printed text on a white background hits >95% accuracy. Handwritten math drops below 60%. Complex layouts (tables, multi-column) are unreliable. The crop-first workflow is the primary mitigation — a tight crop of one printed problem is almost always read correctly.

## Session Workflow

1. **Try first:** Have your daughter attempt the problem on her own for ~5 minutes before engaging the tutor. This prevents dependency.
2. Prep: crop individual problems from today's worksheet (PDF/PNG/photo).
3. Open the project.
4. Start a new chat.
5. Upload the crop of the first problem (and optionally a full-page image for context).
6. Paste the session kickoff.
7. Start voice.
8. Upload new crops as you move to each new problem.
9. Use parent commands as needed.
10. **Explain back:** After each solved problem, ask your daughter to explain the solution in her own words. This is the single best check for real understanding vs. AI-carried completion.
11. End the chat when done; keep it as the session log.

## Parent Commands

| Command | What it does |
|---------|-------------|
| "Parent mode on" | Switches to direct adult explanation |
| "Kid mode on" | Switches back to child tutoring |
| "Hint only" | Gives one hint, not the answer |
| "Next step only" | Gives only the next step |
| "Check answer only" | Says correct/incorrect with minimal explanation |
| "Make it easier" | Creates a simpler version of the problem |
| "Make it harder" | Creates a slightly harder follow-up |
| "Wrap up" | Ends with celebration, what went well, one next skill |

## Branch Points

- **If the tutor gets too gushy:** shorten praise and keep the project instructions dry.
- **If it misses exact worksheet content:** paste the active problem verbatim.
- **If the child is frustrated:** say "Make it easier."
- **If you want direct adult explanation:** "Parent mode on."
- **If the tutor's math reasoning seems wrong:** say "Parent mode on" and verify the approach yourself. Remember: ~40% wrong-approach rate.
- **If the project starts feeling contaminated by old context:** delete noisy old chats. Project memory is opaque — you can't edit individual memories, but you can remove the chats that created them.

## Privacy

Because this is a child voice workflow with a 9-year-old (below OpenAI's stated minimum age of 13), take these steps:

1. **Disable "Improve the model for everyone"** in Settings > Data Controls. This prevents conversations, voice transcripts, and uploaded images from being used for model training.
2. **Do not opt in** to sharing audio/video clips for training (separate toggle).
3. **Understand the gray area:** OpenAI's terms say the service is not directed to children under 13 and they do not knowingly collect data from children under 13. You (the parent) are the account holder and operator. Your child interacts directly via voice. This is a gray area — you are operating outside OpenAI's stated terms for the child's direct interaction.
4. **Data retention:** Audio/video clips are stored alongside the transcription and deleted within 30 days of deleting the chat. Voice transcripts and images may be retained longer per OpenAI's standard data retention policy, but are excluded from training if you disabled the toggle.
5. **Periodic cleanup:** Consider deleting old session chats you no longer need.

---

*v1.1 — Updated 2026-04-03 with research findings on accuracy, OCR, privacy, voice mode constraints, and learning protocols.*
