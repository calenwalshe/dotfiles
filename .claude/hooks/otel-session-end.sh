#!/usr/bin/env bash
# Clean up traceparent file at session end
set -euo pipefail

export PATH="$HOME/bin:/usr/local/bin:/usr/bin:/bin"

SESSION_ID=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id','unknown'))" 2>/dev/null || echo "unknown")

TRACE_FILE="/tmp/claude-trace-${SESSION_ID}.json"
rm -f "${TRACE_FILE}"

exit 0
