# Phase 3: Application Layer Hardening - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Auto-populated from Cortex artifacts via /cortex-bridge

<domain>
## Phase Boundary

Add a global Caddy security headers snippet to all vhosts (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Server header removal), protect the `/status` and `/costs` dashboard routes with authentication, and remove the stale `vnc-auth.calenwalshe.com` Caddyfile entry. Phase 2 must be complete first so Docker services are already bound correctly and Caddy is the sole public-facing listener.

</domain>

<decisions>
## Implementation Decisions

### Caddy global snippet approach
Add a `(security_headers)` named snippet at the top of the Caddyfile (before any site blocks), then `import security_headers` in each vhost block. This is the Caddy idiomatic way to apply headers globally without duplicating config per vhost.

### Caddyfile restart rule (inode change)
The Edit tool changes the file inode. After any Caddyfile edit:
1. First validate: `docker exec caddy caddy validate --config /etc/caddy/Caddyfile`
2. Then restart (not reload): `docker compose restart caddy`
Never use `caddy reload` — it won't pick up the new inode.

### Dashboard auth method
Options: `basicauth` directive or `@internal` IP matcher. Prefer `basicauth` for explicit credential control. If Cloudflare is the only inbound path, `@internal` IP restriction to Cloudflare IP ranges is also viable but adds maintenance burden. Decision: use `basicauth` with a hashed password unless the owner specifies IP restriction.

### Header values (research-confirmed):
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

### CSP is deferred
Content-Security-Policy requires per-vhost content inventory to configure correctly without breaking the radio stream player. Not in this phase.

### Claude's Discretion

- Exact basicauth credentials (generate a hashed password; document the plain-text in a comment for the owner)
- Whether to apply `import security_headers` to all vhosts or only public-facing ones
- Exact Caddyfile path (likely `/home/agent/agent-stack/Caddyfile` — verify at runtime)

</decisions>

<canonical_refs>
## Canonical References

- docs/cortex/specs/server-hardening/spec.md — Section 8 Sequencing step 9
- docs/cortex/specs/server-hardening/gsd-handoff.md — Tasks 16–17
- docs/cortex/contracts/server-hardening/contract-001.md — Done Criteria 10–12
- docs/cortex/research/server-hardening/concept-20260414T033547Z.md — §[q7] Caddy headers
- docs/cortex/clarify/server-hardening/20260414T032326Z-clarify-brief.md

</canonical_refs>

<specifics>
## Specific Ideas

**Security headers snippet:**
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

**Dashboard auth example:**
```caddy
handle /status* {
  basicauth {
    # Generate hash: caddy hash-password --plaintext "yourpassword"
    admin $2a$14$...hashedpassword...
  }
  reverse_proxy health-monitor:9099
}
```

**Validation workflow:**
```bash
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
docker compose restart caddy
curl -sI https://radio.calenwalshe.com | grep -iE "(strict-transport|x-content|x-frame|referrer|server:)"
curl -s -o /dev/null -w "%{http_code}" https://radio.calenwalshe.com/status
```

**Remove VNC entry:**
```bash
grep -n "vnc-auth" /home/agent/agent-stack/Caddyfile
# Then remove the entire block
grep -c "vnc-auth.calenwalshe.com" /home/agent/agent-stack/Caddyfile
# Expected: 0
```

</specifics>

<deferred>
## Deferred Ideas

- Content-Security-Policy headers (high configuration effort, separate task)
- Cloudflare IP-based access restriction for dashboard routes
- Per-vhost custom header values (SAMEORIGIN may need ALLOWALL for embeds — evaluate per vhost)

</deferred>

---

*Phase: 03-server-hardening-appLayer*
*Context gathered: 2026-04-14 via /cortex-bridge*
