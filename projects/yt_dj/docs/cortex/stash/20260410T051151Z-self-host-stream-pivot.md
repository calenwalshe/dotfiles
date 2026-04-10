---
id: self-host-stream-pivot
captured: 20260410T051151Z
status: stashed
related_slug: channel-visual-identity
---

# Pivot idea: self-host live MP3 + webcam stream

## Raw capture

User is considering pivoting away from YouTube after receiving a Community
Guidelines warning on the "Live Views From Around the World" channel. Pivot
concept: host a live stream on his own server that plays MP3s with some live
webcam footage mixed in.

Not yet clarified, not yet written into a clarify brief. Parked as a stash
while the user steps away.

## What triggered the pivot

Received two YouTube notices on 2026-04-09:

1. 12:38 PT — live stream interrupted due to Content ID copyright match on
   "Live Views From Around the World" (video ID ZIBSjWsZHMM).
2. 13:10 PT — content removed, first-offense Community Guidelines warning
   under the 3rd-party content policy for live streams. Warning only, not a
   strike. Can still upload, post, and livestream.

YouTube's stated reason: "3rd party content in your live stream that was not
corrected following repeated warnings of possible abuse." Policy language
emphasized that live streams must be "actively monitored by the channel
owner" — the current 24/7 unattended webcam relay format is structurally
incompatible with that rule.

## Recommendation given on YouTube side (before user pivoted)

- Take the optional policy training, do NOT appeal. First offense, training
  expires the warning after 90 days with no risk. Appeal denial would
  convert the warning to a full strike with a 1-week feature ban.
- For any future live relay of third-party feeds: strip audio, add
  transformative overlays, pre-clear feeds with rights holders, build a
  Studio alerting pipeline so "active monitoring" is defensible.

## Why the self-hosting pivot is not a clean escape

Explained to user but not yet acknowledged. Key points to revisit:

- Self-hosting escapes Content ID enforcement but not copyright law itself.
  Streaming unlicensed MP3s is infringement regardless of platform.
- Liability shifts from "platform takes a channel strike" to "individual
  faces DMCA + potential statutory damages $750–$150K per work."
- "Moved off YouTube to avoid Content ID" is evidence of willfulness, which
  pushes statutory damages toward the ceiling.
- Small/unknown streams rarely get noticed, but growth = risk.

## Legal paths that actually work

1. SoundExchange statutory webcaster license (US) — how internet radio
   stations legally stream commercial music. Per-performance royalties,
   reporting obligations, but fully legal.
2. Royalty-free / Creative Commons / public domain sources only (Free Music
   Archive, ccMixter, Epidemic Sound, Artlist, Musopen). Zero cost, zero
   risk, easiest path.
3. User's own music or music directly licensed from artists.
4. Use a platform that holds the licenses (Mixcloud Live is the cleanest).

## Bandwidth reality check (for self-hosting feasibility)

Per-viewer upload from origin server:

| Quality | Bitrate | 10 viewers | 100 viewers |
|---------|---------|------------|-------------|
| 480p    | ~1 Mbps | 10 Mbps    | 100 Mbps    |
| 720p    | ~3 Mbps | 30 Mbps    | 300 Mbps    |
| 1080p   | ~5 Mbps | 50 Mbps    | 500 Mbps    |

Monthly transfer at 720p 24/7: ~975 GB per concurrent viewer.

Residential upload caps (30–50 Mbps typical) limit to ~10 concurrent 720p
viewers regardless of server hardware. Residential ISP ToS typically
prohibit public servers. VPS at $5–20/mo covers single-digit concurrent
viewers. Above that, need CDN (Cloudflare Stream, Bunny, Mux) or P2P
architecture (PeerTube).

**Architectural note:** since the video source is other people's webcam
feeds, a viewer-side embed approach (client browsers fetch upstream feeds
directly) would eliminate origin bandwidth entirely. Worth exploring
before committing to a true self-hosted transcode pipeline.

## Open questions — must answer before clarify brief

1. Where do the MP3s come from? Personal collection, own music, licensed,
   random? Load-bearing for the whole legal question.
2. Target audience size — handful of friends, ~100 strangers, thousands?
   Determines architecture.
3. Which server specifically? `agent-stack` box on the Pi, a VPS,
   something else? Determines upload bandwidth ceiling.
4. Does this replace `channel-visual-identity`, pause it, or run alongside?
5. Is the goal audience growth or a personal art/hobby piece?

## State when stashed

- Active slug `channel-visual-identity` left untouched: mode=execute,
  status=approved, contract-001 signed. User said "moving on" before
  deciding fate of this slug.
- No clarify brief written for the pivot — idea too sparse, user stepped
  away mid-clarification.

## Next action when resuming

Answer the 5 open questions above, then either:
- Run `/cortex-clarify "self-host live music and webcam stream"` to frame
  the pivot properly, OR
- Decide the pivot is not worth it and return to `channel-visual-identity`
  with the legal reality in mind, OR
- Pick a legal path (SoundExchange license or royalty-free sources) and
  reframe the stream concept around it.
