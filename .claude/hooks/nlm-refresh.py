#!/usr/bin/env python3
"""nlm-refresh.py — Refresh nlm auth by extracting cookies from running Chrome CDP session.

Connects to Chrome at CDP_PORT (default 9222), extracts all cookies, writes them to
~/.notebooklm-mcp-cli/profiles/default/cookies.json, and bumps metadata.json last_validated.

Usage:
  python3 nlm-refresh.py              # refresh and exit 0
  python3 nlm-refresh.py --check      # check if refresh is needed (exit 0=ok, 1=needed)
  python3 nlm-refresh.py --log <path> # write result to log file instead of stdout
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
import websockets

CDP_URL = "http://127.0.0.1:9222"
COOKIES_FILE = Path.home() / ".notebooklm-mcp-cli/profiles/default/cookies.json"
METADATA_FILE = Path.home() / ".notebooklm-mcp-cli/profiles/default/metadata.json"
REQUIRED_COOKIES = {"SID", "HSID", "SSID", "APISID", "SAPISID"}


def log_out(msg: str, log_path: Path | None) -> None:
    if log_path:
        with open(log_path, "a") as f:
            f.write(f"[{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}] nlm-refresh: {msg}\n")
    else:
        print(msg)


def auth_is_fresh() -> bool:
    """Return True if existing cookies contain all required Google auth cookies."""
    try:
        cookies = json.loads(COOKIES_FILE.read_text())
        names = {c["name"] for c in cookies} if isinstance(cookies, list) else set(cookies.keys())
        return REQUIRED_COOKIES.issubset(names)
    except Exception:
        return False


async def extract_cookies_from_cdp() -> list[dict]:
    """Connect to Chrome CDP and extract all cookies via Network.getAllCookies."""
    try:
        r = httpx.get(f"{CDP_URL}/json", timeout=5)
        targets = r.json()
    except Exception as e:
        raise RuntimeError(f"Cannot connect to Chrome CDP at {CDP_URL}: {e}") from e

    # Prefer NotebookLM tab, then any google page, then first available page
    target = (
        next((t for t in targets if "notebooklm" in t.get("url", "") and t.get("type") == "page"), None)
        or next((t for t in targets if "google" in t.get("url", "") and t.get("type") == "page"), None)
        or next((t for t in targets if t.get("type") == "page"), None)
    )

    if not target:
        raise RuntimeError("No usable Chrome page target found at CDP endpoint")

    ws_url = target["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url, ping_timeout=10) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
        resp = json.loads(await ws.recv())

    cookies = resp.get("result", {}).get("cookies", [])
    if not cookies:
        raise RuntimeError("CDP returned empty cookie list")
    return cookies


def write_cookies(cookies: list[dict]) -> None:
    """Write cookies to nlm profile and update last_validated in metadata."""
    COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIES_FILE.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))
    COOKIES_FILE.chmod(0o600)

    metadata = {}
    if METADATA_FILE.exists():
        try:
            metadata = json.loads(METADATA_FILE.read_text())
        except Exception:
            pass

    metadata["last_validated"] = datetime.now().isoformat()
    METADATA_FILE.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    METADATA_FILE.chmod(0o600)


def refresh(log_path: Path | None = None) -> bool:
    """Extract cookies from Chrome and write to nlm profile. Returns True on success."""
    try:
        cookies = asyncio.run(extract_cookies_from_cdp())
        names = {c["name"] for c in cookies}
        missing = REQUIRED_COOKIES - names
        if missing:
            log_out(f"error: Chrome cookies missing required: {missing}", log_path)
            return False

        write_cookies(cookies)
        log_out(f"ok: refreshed {len(cookies)} cookies from Chrome CDP", log_path)
        return True

    except Exception as e:
        log_out(f"error: {e}", log_path)
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Exit 0 if fresh, 1 if refresh needed")
    parser.add_argument("--log", type=Path, help="Append result to this log file")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if auth_is_fresh() else 1)

    ok = refresh(log_path=args.log)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
