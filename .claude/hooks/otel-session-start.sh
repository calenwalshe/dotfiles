#!/usr/bin/env bash
# W3C traceparent init for Claude Code sessions
set -euo pipefail

export PATH="$HOME/bin:/usr/local/bin:/usr/bin:/bin"

# Read session_id from stdin
SESSION_ID=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id','unknown'))" 2>/dev/null || echo "unknown")

# Generate W3C traceparent: 00-{32hex}-{16hex}-01
TRACE_ID=$(openssl rand -hex 16)
SPAN_ID=$(openssl rand -hex 8)
TRACEPARENT="00-${TRACE_ID}-${SPAN_ID}-01"

# Write traceparent file
TRACE_FILE="/tmp/claude-trace-${SESSION_ID}.json"
python3 -c "
import json, sys
data = {
    'traceparent': '${TRACEPARENT}',
    'trace_id': '${TRACE_ID}',
    'session_id': '${SESSION_ID}',
    'created_at': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
}
print(json.dumps(data))
" > "${TRACE_FILE}"

# Emit root span to Phoenix
"$HOME/bin/otel-cli" span \
    --endpoint "http://localhost:6006/v1/traces" \
    --name "claude-session-start" \
    --traceparent "${TRACEPARENT}" \
    --attrs "session.id=${SESSION_ID},span.type=session-root" \
    2>/dev/null || true

exit 0
