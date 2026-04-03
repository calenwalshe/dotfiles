# GSD Handoff: tutor-upload

## Objective

Build and deploy a lightweight web app at `tutorupload.calenwalshe.com` where the parent uploads cropped worksheet images, gets a session pack link, and drags images from that pack page directly into ChatGPT. Node.js + Express + Multer in Docker, Caddy reverse proxy, Cloudflare DNS. Success = parent can upload crops on phone, open pack on laptop, drag images into ChatGPT in one motion.

## Deliverables

| Artifact | Path |
|----------|------|
| Node.js service | `agent-stack/tutor-upload/` (server.js, package.json, Dockerfile) |
| Docker Compose entry | `agent-stack/docker-compose.yml` (tutor-upload service appended) |
| Caddy config | `agent-stack/caddy/Caddyfile` (tutorupload block appended) |
| Cloudflare DNS | A record for `tutorupload.calenwalshe.com` |

## Requirements

None formalized.

## Tasks

- [ ] Create `agent-stack/tutor-upload/` with package.json, Dockerfile, server.js
- [ ] Implement `POST /upload` — Multer multipart, creates pack dir with nanoid, writes manifest.json, redirects to pack page
- [ ] Implement upload page HTML — drag-drop zone, file picker, mobile camera capture
- [ ] Implement `GET /pack/:id` — pack page with numbered draggable images + copy-to-clipboard buttons
- [ ] Implement `GET /pack/:id/images/:filename` — image serving with CORS headers
- [ ] Implement `GET /health` — health check
- [ ] Implement 24-hour cleanup timer (setInterval, deletes expired pack directories)
- [ ] Add service to `agent-stack/docker-compose.yml`
- [ ] Add `tutorupload.calenwalshe.com` block to `agent-stack/caddy/Caddyfile`
- [ ] Create Cloudflare A record via API
- [ ] Build and deploy: `docker compose up -d --build tutor-upload && docker exec caddy caddy reload -c /etc/caddy/Caddyfile`
- [ ] End-to-end test: upload images → open pack → drag into ChatGPT

## Acceptance Criteria

- [ ] `tutorupload.calenwalshe.com` resolves and returns HTTPS responses
- [ ] `GET /health` returns 200 OK
- [ ] Upload page accepts multiple images via file picker and drag-drop
- [ ] Upload page supports camera capture on mobile
- [ ] `POST /upload` creates a session pack and redirects to pack page
- [ ] Pack page displays all uploaded images as numbered, draggable elements
- [ ] Images can be dragged from pack page directly into ChatGPT's message bar
- [ ] "Copy to clipboard" button copies image as PNG blob to clipboard
- [ ] Images served with `Access-Control-Allow-Origin: *` header
- [ ] Session packs auto-expire after 24 hours
- [ ] Pack IDs are 12-char nanoid
- [ ] Service runs as Docker container on agent-stack network behind Caddy

## Contract Link

`docs/cortex/contracts/tutor-upload/contract-001.md`
