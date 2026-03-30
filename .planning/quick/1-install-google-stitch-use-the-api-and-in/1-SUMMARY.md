---
phase: quick
plan: 1
subsystem: google-skill
tags: [stitch, sdk, google, ui-generation]
key-files:
  created:
    - /home/agent/stitch-test.js
  modified: []
decisions:
  - ESM-only SDK requires absolute path import — require() and NODE_PATH do not work for ESM packages
  - SDK high-level Project.generate() has a bug when response outputComponents[0] is not a design component — bypassed with direct callTool() calls
  - htmlCode field in get_screen response is an object with downloadUrl, not a string — must fetch the URL to get HTML content
  - Correct API flow is three-step: create_project -> generate_screen_from_text -> get_screen + fetch downloadUrl
metrics:
  duration: 8min
  completed: 2026-03-30
---

# Quick Task 1: Install @google/stitch-sdk and Stitch Smoke Test Summary

One-liner: Stitch SDK installed globally (ESM-only), smoke test verifies end-to-end login form HTML generation via create_project + generate_screen_from_text + get_screen flow.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install @google/stitch-sdk globally | 08ce549 | (npm global install) |
| 2 | Write and run Stitch smoke test | 08ce549 | /home/agent/stitch-test.js |

## Outcome

- `@google/stitch-sdk@0.0.3` installed at `/home/agent/.nvm/versions/node/v20.20.0/lib/node_modules/@google/stitch-sdk/`
- `stitch-test.js` generates a login form and saves 9515-char HTML to `/home/agent/stitch-output.html`
- `STITCH_API_KEY` sourced from `/home/agent/agent-stack/.env`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SDK is ESM-only — require() fails**
- Found during: Task 1 verification
- Issue: `require('@google/stitch-sdk')` throws `ERR_PACKAGE_PATH_NOT_EXPORTED`. Package has `"type": "module"` and exports only ESM entry points.
- Fix: Rewrote stitch-test.js as ES module (`import` syntax) using absolute path to global install.
- Files modified: /home/agent/stitch-test.js
- Commit: 08ce549

**2. [Rule 1 - Bug] SDK high-level Project.generate() crashes on fresh project**
- Found during: Task 2 execution
- Issue: `Project.generate()` does `raw.outputComponents[0].design.screens[0]` but the first outputComponent may not have a `design` key, causing `Cannot read properties of undefined`.
- Fix: Bypassed the high-level wrapper; used `client.callTool()` directly with `Array.find()` to locate the design component.
- Files modified: /home/agent/stitch-test.js
- Commit: 08ce549

**3. [Rule 1 - Bug] get_screen htmlCode field is an object with downloadUrl, not a string**
- Found during: Task 2 execution
- Issue: `screenRaw.htmlCode` is `{ downloadUrl: "https://..." }`, not a string. Calling `.slice()` on it throws `TypeError: html.slice is not a function`.
- Fix: Added `fetch(htmlCodeField.downloadUrl)` step to download the actual HTML content.
- Files modified: /home/agent/stitch-test.js
- Commit: 08ce549

## SKILL.md Update Needed

The Google skill at `~/.claude/skills/google/SKILL.md` has incorrect Stitch code examples:
- Uses `require('@google/stitch-sdk')` — fails (ESM-only)
- Uses `client.callTool('create_project', { description })` — wrong parameter (should be `{ title }`)
- Uses `result.getHtml()` on callTool result — callTool returns raw JSON, not a Screen object

The correct pattern is documented in `/home/agent/stitch-test.js`.

## Self-Check: PASSED

- [x] /home/agent/stitch-test.js exists
- [x] /home/agent/stitch-output.html exists (112 `<` tags, non-empty HTML)
- [x] Commit 08ce549 exists in git log
- [x] SDK loads via ESM import from absolute path
