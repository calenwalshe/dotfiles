#!/usr/bin/env python3
"""cortex-distribute.py — Cortex artifact distributor (email + NotebookLM surfaces).

Called by cortex-distribute.sh with:
  --file-path   canonical artifact path (for logging)
  --tmpfile     path to file containing artifact content
  --surfaces    comma-separated: email,notebooklm
  --title       human-readable title derived from filename
"""
import argparse
import datetime
import json
import os
import re
import smtplib
import subprocess
import sys
from email.mime.text import MIMEText
from pathlib import Path

LOG = Path.home() / ".claude/hooks/logs/cortex-distribute.log"
CREDS = Path.home() / ".gmail_creds.json"
NLM = "/home/agent/.local/bin/nlm"


def log(msg: str) -> None:
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")


def strip_markdown(text: str) -> str:
    """Convert markdown to readable plain text for email."""
    lines = []
    for line in text.splitlines():
        # Headers: # Foo → FOO
        m = re.match(r"^#{1,6}\s+(.*)", line)
        if m:
            lines.append(m.group(1).upper())
            continue
        # Bold/italic: **foo** / *foo* → foo
        line = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", line)
        # Inline code: `foo` → foo
        line = re.sub(r"`([^`]+)`", r"\1", line)
        # HR: --- → blank
        if re.match(r"^-{3,}$", line.strip()):
            lines.append("")
            continue
        # Strip frontmatter-style key: value lines at top
        lines.append(line)
    # Collapse 3+ blank lines to 2
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    # Strip frontmatter block (--- ... ---) at start
    result = re.sub(r"^---\n.*?---\n", "", result, flags=re.DOTALL)
    return result.strip()


def send_email(title: str, content: str, file_path: str) -> None:
    try:
        creds = json.loads(CREDS.read_text())
        sender = creds["email"]
        password = creds["app_password"]
    except Exception as e:
        log(f"email:error: failed to load creds — {e} — file={file_path}")
        return

    subject = f"Recipe: {title}"
    body = strip_markdown(content)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = sender

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        log(f"email:success: subject='{subject}' to={sender} file={file_path}")
    except Exception as e:
        log(f"email:error: {e} — file={file_path}")


def create_notebook(title: str, content: str, file_path: str) -> None:
    notebook_title = f"Research — {title}"
    try:
        result = subprocess.run(
            [NLM, "notebook", "create", notebook_title],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PATH": f"/home/agent/.local/bin:{os.environ.get('PATH', '')}"},
        )
        if result.returncode != 0:
            log(f"notebooklm:error: notebook create failed (rc={result.returncode}) — {result.stderr.strip()[:200]} — file={file_path}")
            return

        # Parse notebook ID from output (nlm prints ID or JSON)
        output = result.stdout.strip()
        notebook_id = None
        try:
            data = json.loads(output)
            notebook_id = data.get("id") or data.get("notebook_id")
        except json.JSONDecodeError:
            # Try last word on last line as ID
            last_line = output.splitlines()[-1] if output else ""
            if last_line:
                notebook_id = last_line.split()[-1]

        if not notebook_id:
            log(f"notebooklm:error: could not parse notebook ID from output: {output[:200]} — file={file_path}")
            return

        log(f"notebooklm:notebook-created: id={notebook_id} title='{notebook_title}' — file={file_path}")

        # Add content as text source via tmpfile (nlm source add --text-file)
        source_result = subprocess.run(
            [NLM, "source", "add", notebook_id, "--text", content],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PATH": f"/home/agent/.local/bin:{os.environ.get('PATH', '')}"},
        )
        if source_result.returncode == 0:
            log(f"notebooklm:success: source added to notebook={notebook_id} — file={file_path}")
        else:
            log(f"notebooklm:error: source add failed (rc={source_result.returncode}) — {source_result.stderr.strip()[:200]} — file={file_path}")

    except subprocess.TimeoutExpired:
        log(f"notebooklm:error: timeout — file={file_path}")
    except Exception as e:
        log(f"notebooklm:error: {e} — file={file_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-path", required=True)
    parser.add_argument("--tmpfile", required=True)
    parser.add_argument("--surfaces", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()

    tmpfile = Path(args.tmpfile)
    try:
        content = tmpfile.read_text()
    except Exception as e:
        log(f"error: could not read tmpfile {args.tmpfile} — {e}")
        sys.exit(0)
    finally:
        try:
            tmpfile.unlink(missing_ok=True)
        except Exception:
            pass

    surfaces = [s.strip() for s in args.surfaces.split(",") if s.strip()]
    log(f"distribute:start: file={args.file_path} surfaces={args.surfaces} title='{args.title}'")

    for surface in surfaces:
        if surface == "email":
            send_email(args.title, content, args.file_path)
        elif surface == "notebooklm":
            create_notebook(args.title, content, args.file_path)
        else:
            log(f"distribute:warn: unknown surface '{surface}' — skipping")

    log(f"distribute:done: file={args.file_path}")


if __name__ == "__main__":
    main()
