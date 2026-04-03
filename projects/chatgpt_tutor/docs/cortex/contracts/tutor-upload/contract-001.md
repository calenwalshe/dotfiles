# Contract: tutor-upload-001

**ID:** tutor-upload-001
**Slug:** tutor-upload
**Phase:** execute
**Status:** pending

## Objective

Build and deploy `tutorupload.calenwalshe.com` — a lightweight image upload and session pack server so the parent can upload cropped worksheet images and drag them directly into ChatGPT from a browser tab.

## Deliverables

- `agent-stack/tutor-upload/package.json` — Node.js dependencies
- `agent-stack/tutor-upload/Dockerfile` — Container build
- `agent-stack/tutor-upload/server.js` — Express app with all endpoints
- `agent-stack/docker-compose.yml` — tutor-upload service entry (appended)
- `agent-stack/caddy/Caddyfile` — tutorupload.calenwalshe.com block (appended)
- Cloudflare DNS A record for `tutorupload` subdomain

## Scope

**In scope:**
- Upload page with drag-drop, file picker, and mobile camera capture
- Session pack creation with nanoid IDs and manifest.json
- Pack page with numbered draggable images and copy-to-clipboard
- Image serving with CORS headers
- 24-hour auto-expiry cleanup
- Docker container, Caddy reverse proxy, Cloudflare DNS
- Health check endpoint

**Out of scope:**
- Auth, rate limiting, multi-user
- Image processing or OCR
- ChatGPT API integration
- Long-term storage
- Analytics

## Write Roots

- `agent-stack/tutor-upload/` (new directory — all service files)
- `agent-stack/docker-compose.yml` (append service definition)
- `agent-stack/caddy/Caddyfile` (append subdomain block)
- Cloudflare DNS API (one-time A record creation)

## Done Criteria

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

## Validators

```bash
# Health check
curl -sf https://tutorupload.calenwalshe.com/health

# DNS resolution
dig +short tutorupload.calenwalshe.com

# CORS header check
curl -sI https://tutorupload.calenwalshe.com/pack/test/images/test.png | grep -i access-control

# Container running
docker ps --filter name=tutor-upload --format '{{.Status}}'

# Upload test (local)
curl -X POST -F "images=@test.png" http://localhost:9260/upload -v
```

## Eval Plan

`docs/cortex/evals/tutor-upload/eval-plan.md` (pending)

## Approvals

- [ ] Contract approved for execution
- [ ] Evals approved

## Rollback Hints

- Remove `agent-stack/tutor-upload/` directory
- Remove tutor-upload service block from `agent-stack/docker-compose.yml`
- Remove `tutorupload.calenwalshe.com` block from `agent-stack/caddy/Caddyfile`
- `docker compose down tutor-upload && docker exec caddy caddy reload -c /etc/caddy/Caddyfile`
- Delete Cloudflare DNS A record via API
- Remove Docker volume: `docker volume rm agent-stack_tutor_upload_data`
