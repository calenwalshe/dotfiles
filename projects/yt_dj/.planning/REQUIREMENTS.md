# Requirements: Self-Hosted Radio Station

**Defined:** 2026-04-10
**Core Value:** Full aesthetic and technical control over a 24/7 music stream — no platform
dependency, no Content ID, no active-monitoring requirement — reachable at
`https://radio.calenwalshe.com` for a small private audience.

## Infrastructure Requirements

- [ ] **RADIO-01**: Icecast2 + Liquidsoap Docker Compose services running on agent-stack network
- [ ] **RADIO-02**: BPM/key-matched MP3 queue via `dj_mixer.py` → M3U playlist → Liquidsoap

## Frontend Requirements

- [ ] **RADIO-03**: Minimal dark web frontend at `https://radio.calenwalshe.com` with HTML5 audio player
- [ ] **RADIO-04**: Single rotating webcam embed (Windy API, server-proxied JPEG refresh)
- [ ] **RADIO-05**: Caddy reverse proxy block for `radio.calenwalshe.com` with automatic HTTPS

## Operational Requirements

- [ ] **RADIO-06**: Icecast `<public>0</public>` — not discoverable via public streaming directories
- [ ] **RADIO-07**: 1-hour unattended run without stream interruption

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| **RADIO-01** | Phase 1: Services | Pending |
| **RADIO-02** | Phase 1: Services | Pending |
| **RADIO-03** | Phase 2: Routing & Frontend | Pending |
| **RADIO-04** | Phase 2: Routing & Frontend | Pending |
| **RADIO-05** | Phase 2: Routing & Frontend | Pending |
| **RADIO-06** | Phase 3: Deploy & Verify | Pending |
| **RADIO-07** | Phase 3: Deploy & Verify | Pending |

**Coverage:**
- Infrastructure requirements: 2 total — all mapped
- Frontend requirements: 3 total — all mapped
- Operational requirements: 2 total — all mapped
- Unmapped: 0
