"""Music stream manager web app — download YouTube audio, preview with scrubber, store.
Also serves the self-hosted radio frontend and Windy webcam proxy.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
import sqlite3
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import psutil
from fastapi import FastAPI, HTTPException, BackgroundTasks
from src import play_history
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).parent
PROJECT_DIR = APP_DIR.parent.parent
MUSIC_DIR = PROJECT_DIR / "music" / "library"
DB_PATH = PROJECT_DIR / "music" / "library.db"
CAMERAS_PATH = PROJECT_DIR / "config" / "cameras.json"
WEBCAMS_CONFIG_PATH = PROJECT_DIR / "config" / "webcams.json"
RESOURCES_LOG = PROJECT_DIR / "logs" / "resources.jsonl"

# Rate-limit counter for Windy API calls (in-memory, resets on restart)
_windy_call_count = 0
_WINDY_DAILY_WARN_THRESHOLD = 700

# Resource monitor config
_POLL_INTERVAL_S = 600          # 10 minutes
_MAX_ENTRIES = 3 * 24 * 6      # 3 days at 10-min intervals = 432 entries
_NET_IFACE = "enp1s0"          # main server interface
_RADIO_PROCS = ("liquidsoap", "icecast2")  # processes to track

MUSIC_DIR.mkdir(parents=True, exist_ok=True)
(PROJECT_DIR / "logs").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Music Stream Manager")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


# ---------------------------------------------------------------------------
# Resource monitor — background thread, polls every 10 min
# ---------------------------------------------------------------------------

_prev_net: dict | None = None
_prev_net_time: float = 0.0


def _sample_resources() -> dict:
    """Collect one resource sample. Returns a dict ready to log."""
    global _prev_net, _prev_net_time

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # System CPU / RAM
    cpu_pct = psutil.cpu_percent(interval=2)
    mem = psutil.virtual_memory()

    # Network bandwidth — delta bytes over elapsed interval
    net_now = psutil.net_io_counters(pernic=True).get(_NET_IFACE)
    now = time.monotonic()
    bw_up_kbps = bw_down_kbps = 0.0
    if net_now and _prev_net:
        elapsed = max(now - _prev_net_time, 1)
        bw_up_kbps   = (net_now.bytes_sent - _prev_net.bytes_sent) / elapsed / 1024
        bw_down_kbps = (net_now.bytes_recv - _prev_net.bytes_recv) / elapsed / 1024
    _prev_net = net_now
    _prev_net_time = now

    # Per-process CPU + RSS for the radio stack (match by process name only)
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            name = proc.info["name"] or ""
            if any(name == p for p in _RADIO_PROCS):
                procs.append({
                    "pid":    proc.pid,
                    "name":   name,
                    "cpu":    proc.info["cpu_percent"],
                    "rss_mb": round(proc.info["memory_info"].rss / 1024 / 1024, 1),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return {
        "ts":           ts,
        "cpu_pct":      round(cpu_pct, 1),
        "ram_pct":      round(mem.percent, 1),
        "ram_used_mb":  mem.used // (1024 * 1024),
        "bw_up_kbps":   round(bw_up_kbps, 1),
        "bw_down_kbps": round(bw_down_kbps, 1),
        "procs":        procs,
    }


def _append_sample(sample: dict) -> None:
    """Append sample to the rolling JSONL log, trimming to _MAX_ENTRIES."""
    log_path = RESOURCES_LOG
    lines: list[str] = []
    if log_path.exists():
        lines = log_path.read_text().splitlines()

    lines.append(json.dumps(sample))
    # Keep only the newest _MAX_ENTRIES lines
    if len(lines) > _MAX_ENTRIES:
        lines = lines[-_MAX_ENTRIES:]

    log_path.write_text("\n".join(lines) + "\n")


def _monitor_loop() -> None:
    """Background thread: warm up net counter, then poll every _POLL_INTERVAL_S."""
    # Prime the net baseline without recording (first delta would be lifetime totals)
    global _prev_net, _prev_net_time
    _prev_net = psutil.net_io_counters(pernic=True).get(_NET_IFACE)
    _prev_net_time = time.monotonic()
    time.sleep(5)  # brief warm-up so cpu_percent has a reference

    while True:
        try:
            sample = _sample_resources()
            _append_sample(sample)
        except Exception:
            logger.exception("Resource monitor sample failed")
        time.sleep(_POLL_INTERVAL_S)


def _start_monitor() -> None:
    t = threading.Thread(target=_monitor_loop, daemon=True, name="resource-monitor")
    t.start()
    logger.info("Resource monitor started (interval=%ds, max=%d entries)", _POLL_INTERVAL_S, _MAX_ENTRIES)


_start_monitor()


# --- Database ---

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            youtube_url TEXT NOT NULL,
            title TEXT NOT NULL,
            artist TEXT DEFAULT '',
            description TEXT DEFAULT '',
            yt_categories TEXT DEFAULT '',
            yt_tags TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            mood TEXT DEFAULT '',
            duration_s REAL DEFAULT 0,
            file_path TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            status TEXT DEFAULT 'downloading',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    # WAL mode — idempotent, no-op if already set
    conn.execute("PRAGMA journal_mode=WAL")

    # Library tracks index — one row per music file in clips/library dirs
    conn.execute("""
        CREATE TABLE IF NOT EXISTS library_tracks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path     TEXT    NOT NULL UNIQUE,
            filename      TEXT    NOT NULL,
            title         TEXT,
            artist        TEXT,
            bpm           REAL,
            camelot       TEXT,
            duration_s    REAL,
            first_seen_at TEXT    NOT NULL,
            removed_at    TEXT
        )
    """)

    # Append-only play log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plays (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            library_track_id INTEGER,
            file_path        TEXT    NOT NULL,
            filename         TEXT    NOT NULL,
            played_at        TEXT    NOT NULL,
            source           TEXT    DEFAULT 'liquidsoap'
        )
    """)

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_library_tracks_file_path ON library_tracks(file_path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_library_tracks_removed_at ON library_tracks(removed_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plays_library_track_id ON plays(library_track_id, played_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plays_played_at ON plays(played_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plays_file_path ON plays(file_path)")

    conn.commit()
    return conn


# --- Models ---

CLIPS_DIR = PROJECT_DIR / "music" / "clips"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)


class FetchRequest(BaseModel):
    url: str

class SaveClipRequest(BaseModel):
    track_id: str
    start_s: float
    end_s: float
    name: str = ""


# --- Background tasks ---

GENRE_TAG_MAP = {
    "house": ["house", "deep house", "tech house", "progressive house"],
    "techno": ["techno", "minimal techno", "industrial techno"],
    "ambient": ["ambient", "chill", "lo-fi", "lofi", "chillout", "downtempo", "new age"],
    "jazz": ["jazz", "smooth jazz", "acid jazz", "jazz fusion", "bossa nova"],
    "dnb": ["drum and bass", "dnb", "jungle", "liquid dnb"],
    "trance": ["trance", "psytrance", "progressive trance", "goa"],
    "hip_hop": ["hip hop", "hip-hop", "rap", "trap", "boom bap"],
    "rock": ["rock", "psychedelic rock", "classic rock", "indie rock", "alternative"],
    "electronic": ["electronic", "edm", "synth", "synthwave", "electro"],
    "classical": ["classical", "orchestra", "symphony", "piano"],
    "soul": ["soul", "r&b", "funk", "motown", "neo soul"],
    "world": ["world", "afrobeat", "latin", "reggae", "dub"],
}

MOOD_TAG_MAP = {
    "energetic": ["energetic", "upbeat", "party", "hype", "workout", "dance"],
    "chill": ["chill", "relax", "calm", "peaceful", "sleep", "study", "lofi"],
    "dark": ["dark", "industrial", "heavy", "intense", "aggressive"],
    "melancholic": ["sad", "melancholic", "emotional", "nostalgic", "moody"],
    "uplifting": ["uplifting", "happy", "positive", "euphoric", "feel good"],
    "hypnotic": ["hypnotic", "meditative", "trance", "atmospheric", "drone"],
}


def classify_from_tags(yt_tags: list[str], yt_categories: list[str], title: str, description: str) -> tuple[str, str]:
    """Auto-classify genre and mood from YouTube metadata."""
    all_text = " ".join(yt_tags + yt_categories + [title, description]).lower()

    genre = ""
    best_genre_score = 0
    for g, keywords in GENRE_TAG_MAP.items():
        score = sum(1 for k in keywords if k in all_text)
        if score > best_genre_score:
            best_genre_score = score
            genre = g

    mood = ""
    best_mood_score = 0
    for m, keywords in MOOD_TAG_MAP.items():
        score = sum(1 for k in keywords if k in all_text)
        if score > best_mood_score:
            best_mood_score = score
            mood = m

    return genre or "unclassified", mood or "neutral"


def parse_artist_title(yt_title: str, uploader: str) -> tuple[str, str]:
    """Extract artist and clean title from YouTube title string."""
    # Common patterns: "Artist - Title", "Artist — Title", "Artist | Title"
    for sep in [" - ", " — ", " – ", " | "]:
        if sep in yt_title:
            parts = yt_title.split(sep, 1)
            artist = parts[0].strip()
            title = parts[1].strip()
            # Remove common suffixes
            for suffix in ["(Official Audio)", "(Official Video)", "(Official Music Video)",
                          "(Audio)", "(Lyrics)", "(Lyric Video)", "[Official Audio]",
                          "[Official Video]", "(Official)", "(HD)", "(HQ)"]:
                title = title.replace(suffix, "").strip()
            return artist, title

    # No separator found — use uploader as artist
    title = yt_title
    for suffix in ["(Official Audio)", "(Official Video)", "(Official Music Video)",
                  "(Audio)", "(Lyrics)", "(Lyric Video)", "[Official Audio]",
                  "[Official Video]", "(Official)", "(HD)", "(HQ)"]:
        title = title.replace(suffix, "").strip()
    return uploader, title


def download_track(track_id: str, url: str):
    """Download audio from YouTube in background."""
    temp_dir = MUSIC_DIR / "tmp"
    temp_dir.mkdir(exist_ok=True)
    temp_template = str(temp_dir / f"{track_id}.%(ext)s")
    final_path = str(MUSIC_DIR / f"{track_id}.mp3")

    try:
        # Step 1: Get metadata first
        meta_result = subprocess.run([
            "yt-dlp",
            "--cookies-from-browser", "chrome",
            "--remote-components", "ejs:github",
            "--no-playlist", "--skip-download",
            "--print", "%(title)s\n%(uploader)s\n%(description).300s\n%(categories)s\n%(tags)s",
            url,
        ], capture_output=True, text=True, timeout=60)

        yt_title = yt_uploader = yt_description = ""
        yt_categories_raw = yt_tags_raw = ""
        if meta_result.returncode == 0:
            lines = meta_result.stdout.strip().split("\n")
            if len(lines) >= 5:
                yt_title = lines[0]
                yt_uploader = lines[1]
                yt_description = lines[2]
                yt_categories_raw = lines[3]
                yt_tags_raw = lines[4]

        artist, clean_title = parse_artist_title(yt_title, yt_uploader)
        display_title = f"{artist} — {clean_title}" if artist else clean_title

        # Parse tags from string repr
        def parse_list_str(s):
            try:
                import ast
                return ast.literal_eval(s) if s.startswith("[") else []
            except Exception:
                return []

        yt_tags = parse_list_str(yt_tags_raw)
        yt_categories = parse_list_str(yt_categories_raw)

        genre, mood = classify_from_tags(yt_tags, yt_categories, yt_title, yt_description)

        # Update DB with metadata immediately
        db = get_db()
        db.execute(
            "UPDATE tracks SET title=?, artist=?, description=?, yt_categories=?, yt_tags=?, genre=?, mood=? WHERE id=?",
            (display_title, artist, yt_description[:500], json.dumps(yt_categories), json.dumps(yt_tags), genre, mood, track_id),
        )
        db.commit()
        db.close()

        logger.info(f"Metadata: {display_title} | genre={genre} mood={mood} tags={len(yt_tags)}")

        # Step 2: Download audio
        result = subprocess.run([
            "yt-dlp",
            "--cookies-from-browser", "chrome",
            "--remote-components", "ejs:github",
            "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "--no-playlist",
            "--print", "after_move:filepath",
            "-o", temp_template,
            url,
        ], capture_output=True, text=True, timeout=600)

        logger.info(f"yt-dlp stdout: {result.stdout[-500:]}")
        if result.returncode != 0:
            logger.error(f"yt-dlp stderr: {result.stderr[-500:]}")

        # Step 3: Find the output file
        downloaded = None
        for line in result.stdout.strip().splitlines():
            candidate = line.strip()
            if candidate and os.path.isfile(candidate):
                downloaded = candidate
                break
        if not downloaded:
            for f in sorted(temp_dir.glob(f"{track_id}.*"), key=os.path.getmtime, reverse=True):
                if f.suffix in (".mp3", ".m4a", ".opus", ".webm", ".ogg"):
                    downloaded = str(f)
                    break
        if not downloaded or not os.path.isfile(downloaded):
            raise FileNotFoundError(f"No output file found for {track_id}. yt-dlp exit={result.returncode}")

        # Step 4: Ensure mp3 and move to final location
        if downloaded != final_path:
            if not downloaded.endswith(".mp3"):
                subprocess.run([
                    "ffmpeg", "-y", "-i", downloaded,
                    "-c:a", "libmp3lame", "-q:a", "0", final_path,
                ], capture_output=True, timeout=120)
                os.remove(downloaded)
            else:
                os.rename(downloaded, final_path)

        # Step 5: Get duration from file
        probe = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", final_path,
        ], capture_output=True, text=True, timeout=30)

        duration = 0
        if probe.returncode == 0:
            info = json.loads(probe.stdout)
            duration = float(info.get("format", {}).get("duration", 0))

        file_size = os.path.getsize(final_path)

        db = get_db()
        db.execute(
            "UPDATE tracks SET status=?, duration_s=?, file_path=?, file_size=? WHERE id=?",
            ("ready", duration, final_path, file_size, track_id),
        )
        db.commit()
        db.close()
        logger.info(f"Downloaded: {display_title} ({duration:.0f}s, {file_size/1024/1024:.1f}MB)")

    except Exception as e:
        logger.exception(f"Download failed for {track_id}")
        db = get_db()
        db.execute("UPDATE tracks SET status=? WHERE id=?", (f"error: {str(e)[:200]}", track_id))
        db.commit()
        db.close()


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(APP_DIR / "static" / "index.html"))


@app.post("/api/fetch")
async def fetch_track(req: FetchRequest, bg: BackgroundTasks):
    """Start downloading a YouTube track."""
    url = req.url.strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        raise HTTPException(400, "Must be a YouTube URL")

    # Clean URL — remove playlist params
    url = re.sub(r"[&?](list|start_radio|index)=[^&]*", "", url)

    track_id = uuid.uuid4().hex[:12]
    db = get_db()
    db.execute(
        "INSERT INTO tracks (id, youtube_url, title, file_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (track_id, url, "Downloading...", "", "downloading", datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    db.close()

    bg.add_task(download_track, track_id, url)
    return {"track_id": track_id, "status": "downloading"}


@app.get("/api/tracks")
async def list_tracks():
    """List all tracks."""
    db = get_db()
    rows = db.execute("SELECT * FROM tracks ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.get("/api/tracks/{track_id}")
async def get_track(track_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM tracks WHERE id=?", (track_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Track not found")
    return dict(row)


@app.get("/api/audio/{track_id}")
async def serve_audio(track_id: str):
    """Serve a track's audio file for playback."""
    db = get_db()
    row = db.execute("SELECT file_path, status FROM tracks WHERE id=?", (track_id,)).fetchone()
    db.close()
    if not row or row["status"] != "ready":
        raise HTTPException(404, "Track not ready")
    path = row["file_path"]
    if not path or not os.path.exists(path):
        raise HTTPException(404, f"File not found: {path}")
    return FileResponse(path, media_type="audio/mpeg", headers={
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
    })


@app.post("/api/save-clip")
async def save_clip(req: SaveClipRequest):
    """Extract a clip from a track and save to the canonical clips directory."""
    db = get_db()
    row = db.execute("SELECT file_path, title, status FROM tracks WHERE id=?", (req.track_id,)).fetchone()
    db.close()
    if not row or row["status"] != "ready":
        raise HTTPException(404, "Track not ready")
    if not os.path.exists(row["file_path"]):
        raise HTTPException(404, "Source file missing")
    if req.end_s <= req.start_s:
        raise HTTPException(400, "End must be after start")

    # Generate clip filename: Artist - Title or custom name
    clip_name = req.name.strip() if req.name.strip() else row["title"]
    # Sanitize filename
    safe_name = re.sub(r'[^\w\s\-\.\(\)]', '', clip_name).strip()[:100]
    if not safe_name:
        safe_name = f"clip_{req.track_id[:8]}"
    clip_path = str(CLIPS_DIR / f"{safe_name}.mp3")

    # Avoid overwriting
    counter = 1
    while os.path.exists(clip_path):
        clip_path = str(CLIPS_DIR / f"{safe_name}_{counter}.mp3")
        counter += 1

    try:
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", row["file_path"],
            "-ss", str(req.start_s),
            "-to", str(req.end_s),
            "-c:a", "libmp3lame", "-q:a", "0",
            clip_path,
        ], capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-200:]}")

        file_size = os.path.getsize(clip_path)
        duration = req.end_s - req.start_s
        clip_filename = os.path.basename(clip_path)

        return {
            "status": "saved",
            "path": clip_path,
            "filename": clip_filename,
            "duration_s": duration,
            "file_size": file_size,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to save clip: {str(e)}")


@app.get("/api/clips")
async def list_clips():
    """List all saved clips."""
    clips = []
    for f in sorted(CLIPS_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True):
        # Get duration via ffprobe
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(f)],
            capture_output=True, text=True, timeout=10,
        )
        duration = 0
        if probe.returncode == 0:
            info = json.loads(probe.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
        clips.append({
            "filename": f.name,
            "path": str(f),
            "file_size": f.stat().st_size,
            "duration_s": duration,
        })
    return clips


# ---------------------------------------------------------------------------
# Radio routes — self-hosted Icecast radio + webcam proxy
# ---------------------------------------------------------------------------

def _load_windy_key() -> str:
    with open(WEBCAMS_CONFIG_PATH) as f:
        return json.load(f)["windy_api_key"]


def _load_cameras() -> list[dict]:
    with open(CAMERAS_PATH) as f:
        return json.load(f)


@app.get("/radio", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def radio_page():
    """Serve the radio frontend."""
    radio_html = APP_DIR / "static" / "radio.html"
    if radio_html.exists():
        return FileResponse(str(radio_html))
    raise HTTPException(404, "radio.html not found")


@app.get("/cam-url")
async def cam_url():
    """Return Windy webcam data for a randomly chosen global location.

    Returns player embed URL (iframe-able) and preview JPEG. Calls Windy v3 API
    server-side so the API key never reaches the browser and CORS is bypassed.
    """
    global _windy_call_count
    _windy_call_count += 1
    if _windy_call_count >= _WINDY_DAILY_WARN_THRESHOLD:
        logger.warning(
            f"Windy API call #{_windy_call_count} — approaching free-tier limit (1000/day)"
        )

    cameras = _load_cameras()
    # Prefer pedestrian/square city cams; fall back to any city cam
    pedestrian_cams = [c for c in cameras if c.get("source") == "windy"
                       and c.get("category") == "city"
                       and any(t in c.get("tags", []) for t in ("pedestrian", "square", "crossing"))]
    city_cams = [c for c in cameras if c.get("source") == "windy" and c.get("category") == "city"]
    pool = pedestrian_cams if pedestrian_cams else city_cams
    if not pool:
        raise HTTPException(503, "No Windy cameras configured")

    cam = random.choice(pool)
    api_key = _load_windy_key()

    async def _search(params: dict):
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.windy.com/webcams/api/v3/webcams",
                params={"lang": "en", "limit": 10, "offset": 0,
                        "include": "images,player,categories", **params},
                headers={"x-windy-api-key": api_key},
            )
            resp.raise_for_status()
            return resp.json().get("webcams", [])

    def _extract(webcam: dict, cam_name: str, cam_country: str) -> dict | None:
        preview = webcam.get("images", {}).get("current", {}).get("preview")
        webcam_id = webcam.get("webcamId") or webcam.get("id")
        player_day = webcam.get("player", {}).get("day")
        player_embed = (
            player_day if isinstance(player_day, str) else
            (f"https://webcams.windy.com/webcams/public/embed/player/{webcam_id}/" if webcam_id else None)
        )
        if not (preview or player_embed):
            return None
        # Prefer cams with player embed (live video) over still-only
        cats = [c.get("name", "").lower() for c in webcam.get("categories", [])]
        return {
            "url": preview,
            "player_embed": player_embed,
            "webcam_id": str(webcam_id) if webcam_id else None,
            "location": cam_name,
            "country": cam_country,
            "windy_call_count": _windy_call_count,
            "has_video": bool(player_embed),
            "windy_cats": cats,
        }

    lat, lon = cam["lat"], cam["lon"]
    try:
        # Search with city category filter near chosen location
        webcams = await _search({
            "nearTo": f"{lat},{lon}", "radius": 50,
            "categories": "city", "sortBy": "popularity",
        })
    except httpx.HTTPError as e:
        logger.error(f"Windy API error for {cam['name']}: {e}")
        raise HTTPException(503, f"Windy API unavailable: {e}")

    # Widen radius if nothing nearby
    if not webcams:
        try:
            webcams = await _search({
                "nearTo": f"{lat},{lon}", "radius": 200,
                "categories": "city", "sortBy": "popularity",
            })
        except httpx.HTTPError:
            pass

    # Last resort: global popular city cams
    if not webcams:
        try:
            webcams = await _search({"categories": "city", "sortBy": "popularity"})
        except httpx.HTTPError:
            pass

    if not webcams:
        raise HTTPException(503, "No webcams available from Windy API")

    # Sort: player-embed cams first (live video), then still-image cams
    candidates = [r for w in webcams if (r := _extract(w, cam["name"], cam.get("country", "")))]
    candidates.sort(key=lambda x: 0 if x["has_video"] else 1)

    if candidates:
        return JSONResponse(candidates[0])

    raise HTTPException(503, "No webcam data available")


@app.get("/api/resources")
async def get_resources(hours: int = 72):
    """Return resource samples from the rolling log.

    Query param:
      hours — how many hours of history to return (default 72 = 3 days, max 72)
    """
    hours = min(max(hours, 1), 72)
    max_points = hours * 6  # 6 samples per hour at 10-min intervals

    if not RESOURCES_LOG.exists():
        return {"samples": [], "poll_interval_s": _POLL_INTERVAL_S}

    lines = RESOURCES_LOG.read_text().splitlines()
    recent = lines[-max_points:] if len(lines) > max_points else lines

    samples = []
    for line in recent:
        line = line.strip()
        if line:
            try:
                samples.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return {"samples": samples, "poll_interval_s": _POLL_INTERVAL_S}


@app.delete("/api/tracks/{track_id}")
async def delete_track(track_id: str):
    """Delete a track."""
    db = get_db()
    row = db.execute("SELECT file_path FROM tracks WHERE id=?", (track_id,)).fetchone()
    if row and row["file_path"] and os.path.exists(row["file_path"]):
        os.remove(row["file_path"])
    db.execute("DELETE FROM tracks WHERE id=?", (track_id,))
    db.commit()
    db.close()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Play history read API
# ---------------------------------------------------------------------------

@app.get("/api/play-history/recent")
def api_play_history_recent(limit: int = 100):
    return play_history.recent_plays(limit=limit)


@app.get("/api/play-history/never-played")
def api_play_history_never_played():
    return play_history.tracks_never_played()


@app.get("/api/play-history/freshness")
def api_play_history_freshness(max_days: int = 7):
    return play_history.tracks_by_days_since_play(max_days=max_days)


@app.get("/api/play-history/track")
def api_play_history_track(file_path: str):
    result = play_history.track_stats(file_path=file_path)
    if result is None:
        raise HTTPException(status_code=404, detail="Track not found in library")
    return result
