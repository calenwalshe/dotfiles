---
phase: "03"
plan: "01"
name: "Caddy Security Headers + Dashboard Auth + VNC Cleanup"
subsystem: "reverse-proxy"
tags: ["caddy", "security-headers", "basicauth", "hsts", "hardening"]
status: complete
completed: "2026-04-14"
duration: "~15 minutes"

dependency-graph:
  requires: ["02-01", "02-02"]
  provides: ["security-headers-all-vhosts", "dashboard-auth", "vnc-removed"]
  affects: ["04-pentest-ac"]

tech-stack:
  added: []
  patterns: ["caddy-snippets", "basicauth-inline", "security-headers-snippet"]

key-files:
  modified:
    - /home/agent/agent-stack/caddy/Caddyfile
---

# Phase 03 Plan 01: Caddy Security Headers + Dashboard Auth + VNC Cleanup Summary

**One-liner:** HSTS/CSP-class headers on all 13 vhosts via snippet, basicauth on /status+/costs, VNC block removed.

## What Was Done

### Task 1: Generate bcrypt password hash

Generated random password using `openssl rand -base64 12` and hashed via `caddy hash-password --plaintext`.

**Dashboard password:** `u6P4FRokt727+Bq+`
**Hash:** `$2a$14$kKQT0djPgpbqKA0XwIPa0uQYKaqkifbb5nb44mo4nSghT7a2UzGrK`

**ACTION REQUIRED:** Change this password after reviewing. Use:
```bash
NEWHASH=$(docker exec caddy caddy hash-password --plaintext "your-new-password")
# Then update the three basicauth blocks in /home/agent/agent-stack/caddy/Caddyfile
# Then: cd /home/agent/agent-stack && docker compose restart caddy
```

### Task 2: Caddyfile edits

**A. Security headers snippet** — added after global options block (lines 7-16):
```caddy
(security_headers) {
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "SAMEORIGIN"
    Referrer-Policy "strict-origin-when-cross-origin"
    Permissions-Policy "geolocation=(), microphone=(), camera=()"
    -Server
  }
}
```

**B. `import security_headers`** added to all 13 named vhosts:
tutorupload, files, showcase, melts, dejo, :443, kalshidash, musicgenome, musicstreams, radio, maps, mcp, docs. Skipped :80 (redirect only).

**C. basicauth** added to /status, /status/metrics, /costs in :443 block. Username: `admin`.

**D. VNC block removed** — `vnc-auth.calenwalshe.com` block (previously marked "Temporary VNC for YouTube OAuth") deleted.

### Task 3: Validate

```
Valid configuration
```

### Task 4: Restart

`docker compose restart caddy` — started cleanly, no errors in logs.

## Verification Results

### 1. Security headers on radio.calenwalshe.com

```
permissions-policy: geolocation=(), microphone=(), camera=()
referrer-policy: strict-origin-when-cross-origin
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-content-type-options: nosniff
x-frame-options: SAMEORIGIN
```
Note: `server: cloudflare` appears (Cloudflare adds its own Server header after Caddy strips it — expected).

### 2. Dashboard auth enforced

```
/status without auth   → HTTP 401
/status/metrics no auth → HTTP 401
/costs without auth    → HTTP 401
/status with valid creds → HTTP 200
```

### 3. VNC entry removed

```
grep -c "vnc-auth.calenwalshe.com" Caddyfile → 0
```

### 4. Stream still works

```
HTTP/2 200
content-type: audio/mpeg
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| basicauth in route block (caddy fmt canonical) | caddy fmt moves top-level handle directives before a route block into the route block; validated as correct by `caddy validate` |
| X-Frame-Options: SAMEORIGIN (not DENY) | Allows same-origin framing; safer default that doesn't break internal iframes |
| Permissions-Policy: geolocation/mic/camera all blocked | Conservative default; services that need these must override in their own vhost |
| Server header suppressed (-Server) | Reduces fingerprinting; Cloudflare adds its own so header is still present at CDN edge |

## Deviations from Plan

### caddy fmt restructuring

**Found during:** Task 2 (after first Write)

**Issue:** The `caddy fmt` hook runs after every file write/edit. It consistently moved standalone `handle` blocks before a `route` block into the `route` block, and collapsed preceding comments into the route. Two write cycles were needed to understand the formatter behaviour.

**Resolution:** Accepted the formatter-canonical structure. `caddy validate` confirmed correctness. The auth directives (`basicauth`) remain in place inside the `route` block — Caddy evaluates them in order, so /status and /costs are still gated before the catch-all `handle`.

**Files modified:** `/home/agent/agent-stack/caddy/Caddyfile`

**Classified as:** Rule 3 (Blocking) — formatter interference required investigation before proceeding.

## Next Phase Readiness

Phase 4 (PTES pentest AC) can now verify:
- Security headers present on all vhosts
- /status, /costs return 401 without credentials
- vnc-auth.calenwalshe.com no longer resolves/routes

No blockers for Phase 4.
