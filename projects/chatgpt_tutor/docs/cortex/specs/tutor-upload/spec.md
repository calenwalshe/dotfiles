# Spec: tutor-upload

**Status:** draft
**Created:** 20260403T223500Z

## 1. Problem

The Math Voice Tutor workflow requires the parent to prepare cropped worksheet images on one device (phone camera or laptop) and then get those crops into a ChatGPT voice session running on iOS. Currently there's no bridge between the prep device and the session device — crops sit in the camera roll or file system with no easy way to transfer them into a ChatGPT chat on the laptop. The parent needs a simple upload-and-share tool that eliminates this device-transfer friction so cropped images can be dragged directly into ChatGPT from a browser tab.

## 2. Scope

**In scope:**
- Web app at `tutorupload.calenwalshe.com`
- Upload page: drag-drop zone + file picker + mobile camera capture
- Session pack creation: group uploaded images under a single shareable URL
- Pack page: display all images as large draggable elements with copy-to-clipboard buttons
- Docker container service following agent-stack patterns
- Caddy reverse proxy configuration
- Cloudflare DNS A record creation
- 24-hour auto-expiry of session packs
- Health check endpoint

**Out of scope:**
- User accounts, authentication, or rate limiting
- Image processing, OCR, or text extraction
- ChatGPT API integration
- Mobile native app
- Long-term storage or archival
- Multi-user collaboration features
- Analytics or usage tracking

## 3. Architecture Decision

**Chosen approach:** Node.js Express server with Multer for file uploads, local filesystem storage in a Docker volume, nanoid for session pack IDs, single-process 24-hour cleanup timer. Served via Caddy reverse proxy behind Cloudflare.

**Rationale:** Matches the existing agent-showcase service pattern in docker-compose. Local filesystem is simpler than Garage S3 (which isn't on the agent-stack network). Node 20 is available on the server. No database needed — a pack is just a directory with images and a manifest.json.

**Alternatives considered:**
- **Python + Flask:** Rejected — works equally well but Node matches the existing service pattern on this server.
- **Garage S3 for storage:** Rejected — not on agent-stack network, requires bucket creation and S3 client library for zero benefit on a single-user app.
- **Static site + presigned S3 uploads:** Rejected — overengineered for a single-user ephemeral upload tool.
- **Clipboard-only UX (no drag-and-drop):** Rejected — drag-and-drop is one action per image vs. two for clipboard copy+paste.

## 4. Interfaces

| Interface | Owner | Read/Write | Notes |
|-----------|-------|------------|-------|
| `POST /upload` | tutor-upload service | Write | Accepts multipart form with images, creates session pack, returns pack URL |
| `GET /pack/:id` | tutor-upload service | Read | Serves pack page with all images |
| `GET /pack/:id/images/:filename` | tutor-upload service | Read | Serves individual images with correct content-type and CORS headers |
| `GET /health` | tutor-upload service | Read | Health check endpoint for Docker |
| `agent-stack/docker-compose.yml` | agent-stack | Write (append service) | New `tutor-upload` service definition |
| `agent-stack/caddy/Caddyfile` | agent-stack | Write (append block) | New `tutorupload.calenwalshe.com` reverse proxy block |
| Cloudflare DNS API | Cloudflare | Write (one-time) | A record for `tutorupload.calenwalshe.com` |
| Local filesystem (`/app/uploads/`) | Docker volume | Read/Write | Session pack directories with images and manifest.json |

## 5. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Node.js | 20-alpine (Docker) | Runtime |
| Express | ^4.x | HTTP server, routing, static file serving |
| Multer | ^1.x | Multipart file upload handling |
| nanoid | ^5.x | URL-safe random pack ID generation (12 chars) |
| Docker | Existing | Container runtime |
| Caddy | 2 (existing container) | Reverse proxy, TLS termination |
| Cloudflare | Existing account | DNS, CDN proxy |
| agent-stack network | Existing | Docker network for inter-service DNS |

## 6. Risks

- **Pack URLs are guessable if IDs are too short** — Mitigation: 12-char nanoid provides ~2^71 entropy, effectively unguessable for a single-user app.
- **Disk fills up if cleanup fails** — Mitigation: 24-hour setInterval cleanup in-process. Monitor via health endpoint. Volume is dedicated, won't affect other services.
- **CORS blocks drag-and-drop to ChatGPT** — Mitigation: Serve images with `Access-Control-Allow-Origin: *` and correct `Content-Type` headers.
- **Caddy reload fails after Caddyfile edit** — Mitigation: Validate Caddyfile syntax before reload (`caddy validate`). Keep backup of working Caddyfile.
- **Cloudflare DNS propagation delay** — Mitigation: Proxied A records propagate through Cloudflare instantly. TTL=1 (auto).

## 7. Sequencing

1. **Scaffold Node.js service** — Create `agent-stack/tutor-upload/` with package.json, Dockerfile, server.js. Checkpoint: `docker build` succeeds.
2. **Implement upload endpoint** — `POST /upload` accepts images via Multer, creates pack directory with nanoid, writes manifest.json. Checkpoint: curl upload returns pack URL.
3. **Implement pack page** — `GET /pack/:id` serves HTML with all images as draggable elements + copy-to-clipboard buttons. Checkpoint: pack page renders in browser with uploaded images.
4. **Implement image serving** — `GET /pack/:id/images/:filename` with CORS headers. Checkpoint: images load on pack page, draggable to another tab.
5. **Implement cleanup** — setInterval deletes pack directories older than 24 hours. Checkpoint: old packs are removed automatically.
6. **Add to docker-compose** — Service definition in `agent-stack/docker-compose.yml`. Checkpoint: `docker compose up -d tutor-upload` runs.
7. **Configure Caddy** — Add `tutorupload.calenwalshe.com` block to Caddyfile, reload. Checkpoint: `curl -k https://tutorupload.calenwalshe.com/health` returns 200.
8. **Create Cloudflare DNS record** — A record for `tutorupload`. Checkpoint: `dig tutorupload.calenwalshe.com` resolves.
9. **End-to-end test** — Upload images from phone, open pack on laptop, drag into ChatGPT. Checkpoint: images appear in ChatGPT chat.

## 8. Tasks

- [ ] Create `agent-stack/tutor-upload/` directory
- [ ] Write `package.json` with express, multer, nanoid dependencies
- [ ] Write `Dockerfile` (node:20-alpine, WORKDIR /app, npm install, EXPOSE 9260)
- [ ] Write `server.js` — Express app with health, upload, pack page, image serving endpoints
- [ ] Write upload page HTML — drag-drop zone, file picker, camera capture input, upload form
- [ ] Write pack page HTML — numbered images, drag-and-drop optimized, copy-to-clipboard buttons
- [ ] Implement 24-hour cleanup timer for expired packs
- [ ] Add `tutor-upload` service to `agent-stack/docker-compose.yml`
- [ ] Add `tutorupload.calenwalshe.com` block to `agent-stack/caddy/Caddyfile`
- [ ] Create Cloudflare A record for `tutorupload` subdomain
- [ ] Build and start container: `docker compose up -d --build tutor-upload`
- [ ] Reload Caddy: `docker exec caddy caddy reload -c /etc/caddy/Caddyfile`
- [ ] End-to-end test: upload → pack page → drag to ChatGPT

## 9. Acceptance Criteria

- [ ] `tutorupload.calenwalshe.com` resolves and returns HTTPS responses
- [ ] `GET /health` returns 200 OK
- [ ] Upload page accepts multiple images via file picker and drag-drop
- [ ] Upload page supports camera capture on mobile (`<input accept="image/*" capture>`)
- [ ] `POST /upload` creates a session pack and redirects to pack page
- [ ] Pack page displays all uploaded images as numbered, draggable `<img>` elements
- [ ] Images can be dragged from the pack page directly into ChatGPT's message bar (Chrome, tested)
- [ ] "Copy to clipboard" button copies image as PNG blob to clipboard (Chrome, tested)
- [ ] Images are served with `Access-Control-Allow-Origin: *` header
- [ ] Session packs auto-expire after 24 hours (files deleted from disk)
- [ ] Pack IDs are 12-char nanoid (URL-safe, unguessable)
- [ ] Service runs as Docker container on agent-stack network behind Caddy
