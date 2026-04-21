#!/usr/bin/env bash
# Emit OTLP span per tool call with W3C traceparent propagation
set -euo pipefail

export PATH="$HOME/bin:/usr/local/bin:/usr/bin:/bin"

# Read payload fields from stdin
PAYLOAD=$(cat)
SESSION_ID=$(echo "$PAYLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id','unknown'))" 2>/dev/null || echo "unknown")
TOOL_NAME=$(echo "$PAYLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name','unknown'))" 2>/dev/null || echo "unknown")

TRACE_FILE="/tmp/claude-trace-${SESSION_ID}.json"

# Lazy-init guard: generate traceparent if file absent (handles /clear edge case)
if [[ ! -f "$TRACE_FILE" ]]; then
    TRACE_ID=$(openssl rand -hex 16)
    SPAN_ID=$(openssl rand -hex 8)
    TRACEPARENT="00-${TRACE_ID}-${SPAN_ID}-01"
    python3 -c "
import json
data = {
    'traceparent': '${TRACEPARENT}',
    'trace_id': '${TRACE_ID}',
    'session_id': '${SESSION_ID}',
    'created_at': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
}
print(json.dumps(data))
" > "${TRACE_FILE}"
fi

# Read traceparent from file
TRACEPARENT=$(python3 -c "import json; d=json.load(open('${TRACE_FILE}')); print(d['traceparent'])" 2>/dev/null || echo "")

if [[ -z "$TRACEPARENT" ]]; then
    exit 0
fi

# Emit child span to Phoenix
"$HOME/bin/otel-cli" span \
    --endpoint "http://localhost:6006/v1/traces" \
    --name "claude-tool-${TOOL_NAME}" \
    --traceparent "${TRACEPARENT}" \
    --attrs "session.id=${SESSION_ID},tool.name=${TOOL_NAME}" \
    2>/dev/null || true

exit 0
