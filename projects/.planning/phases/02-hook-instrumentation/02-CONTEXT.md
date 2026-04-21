# Phase 2: Hook Instrumentation — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Write and register three Claude Code hook scripts, install OpenLLMetry, and verify that sessions produce correlated spans in Phoenix. Depends on Phase 1 (Phoenix running).

</domain>

<decisions>
## Implementation Decisions

- **traceparent file path:** `/tmp/claude-trace-{session_id}.json` — consistent with existing `ledger-last-{session_id}` pattern in `token-ledger.js`
- **traceparent schema:** `{ "traceparent": "00-{32hex}-{16hex}-01", "trace_id": "...", "session_id": "...", "created_at": "..." }`
- **SessionStart hook:** Generate random 32-hex traceId + 16-hex spanId; write JSON file
- **PostToolUse hook:** Read file; pass `--traceparent` to `otel-cli exec`; include lazy-init guard (generate file if absent — handles `/clear` edge case)
- **SessionEnd hook:** `rm -f /tmp/claude-trace-${session_id}.json`
- **OTLP endpoint:** `http://localhost:6006/v1/traces`
- **OpenLLMetry:** `pip install traceloop-sdk`; `TRACELOOP_TRACE_CONTENT=false` global default; `suppress_tracing()` for sensitive skills
- **Hook registration:** Additive writes to `~/.claude/settings.json` — existing hooks must not be removed
- **Lazy-init is REQUIRED (not optional):** PostToolUse must generate traceparent if file absent

### Claude's Discretion

- Exact bash implementation of hex generation (`openssl rand -hex 16` / `od -An -tx1 /dev/urandom | tr -d ' \n' | head -c 32`)
- Whether to source `~/.profile` for PATH in hooks or prepend directly
- otel-cli span name convention (e.g., tool name from `$CLAUDE_TOOL_NAME` or parsed from stdin)

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/experiment-control-plane/spec.md (§5 Interfaces, §8 Sequencing steps 3–7, §7 Risks)
- docs/cortex/specs/experiment-control-plane/gsd-handoff.md (Tasks 5–12)
- docs/cortex/contracts/experiment-control-plane/contract-001.md (Done Criteria 3–6)
- docs/cortex/research/experiment-control-plane/implementation-20260421T031706Z.md (Q3+Q5 hook payloads)
- /home/agent/.claude/settings.json (hook registration format)
- /home/agent/.claude/hooks/token-ledger.js (ledger-last pattern reference)
- /home/agent/.claude/hooks/postuse-event-logger.sh (PostToolUse payload fields reference)

</canonical_refs>

<specifics>
## Specific Ideas

**Hook event payload fields (from implementation research):**
- SessionStart stdin: `session_id`, `transcript_path`
- PostToolUse stdin: `session_id`, `tool_name`, `tool_input`, `tool_response.output`, `tool_response.exit_code`, `cwd`, `context_window.remaining_percentage`
- SessionEnd stdin: `session_id`, `transcript_path`, `matcher`
- All hooks have `$CLAUDE_PROJECT_DIR` env var available

**Critical footgun on choices:** Not relevant to this phase but note for Phase 3.

**Verification steps:**
1. Start new session → check `/tmp/claude-trace-*.json` exists
2. Run a tool → check span appears in Phoenix UI with correct `trace_id`
3. Run `/clear` then a tool → check span appears (lazy-init fired)
4. End session → check no stale `/tmp/claude-trace-*.json` files remain

</specifics>

<deferred>
## Deferred Ideas

- PreCompact hook instrumentation (v2)
- claude-haiku-4-5 eval judge (requires Anthropic evaluator wrapper)
- Content tracing opt-in per-skill pattern beyond suppress_tracing()

</deferred>

---

*Phase: 02-hook-instrumentation*
*Context gathered: 2026-04-21 via /cortex-bridge*
