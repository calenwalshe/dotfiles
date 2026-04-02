"""Codebase perceiver — scans git history, test coverage, lint, and TODOs.

Writes L0 Claims to the store. Runs standalone:
    python -m src.perceivers.codebase --repo /path/to/repo --db knowledge.db

No other component needed. No configuration beyond repo path and DB.
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.protocols.schemas import Claim, ClaimLevel, Domain, SourceType
from src.protocols.sqlite_store import SQLiteStore


def _run(cmd: list[str], cwd: str | Path | None = None) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd)
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def perceive_git_churn(repo: Path, days: int = 7) -> list[Claim]:
    """Find files with high churn in recent history."""
    output = _run(
        ["git", "log", f"--since={days} days ago", "--name-only", "--pretty=format:"],
        cwd=repo,
    )
    if not output:
        return []

    file_counts: dict[str, int] = {}
    for line in output.splitlines():
        line = line.strip()
        if line:
            file_counts[line] = file_counts.get(line, 0) + 1

    claims = []
    for filepath, count in sorted(file_counts.items(), key=lambda x: -x[1]):
        if "__pycache__" in filepath or filepath.endswith((".pyc", ".pyo")):
            continue
        if count >= 3:
            claims.append(Claim(
                text=f"File '{filepath}' changed {count} times in the last {days} days (high churn)",
                level=ClaimLevel.L0,
                confidence=0.7,
                domain=Domain.codebase,
                topic="churn",
                entity=filepath,
                source_type=SourceType.commit,
                source_ref=f"git log --since={days}d {filepath}",
                tags=["codebase-health", "churn"],
            ))
    return claims


def perceive_todos(repo: Path) -> list[Claim]:
    """Find TODO/FIXME/HACK comments in source code."""
    output = _run(
        ["grep", "-rn", r"TODO\|FIXME\|HACK", "--include=*.py",
         "--exclude=codebase.py", "."],
        cwd=repo,
    )
    if not output:
        return []

    lines = output.splitlines()
    claims = []
    if len(lines) > 0:
        claims.append(Claim(
            text=f"Codebase has {len(lines)} TODO/FIXME/HACK comments across Python files",
            level=ClaimLevel.L0,
            confidence=0.9,
            domain=Domain.codebase,
            topic="todos",
            source_type=SourceType.file,
            source_ref="grep -rn TODO/FIXME/HACK --include=*.py",
            tags=["codebase-health", "tech-debt"],
        ))

    # Individual high-priority items (FIXME/HACK are more urgent than TODO)
    for line in lines:
        if "FIXME" in line or "HACK" in line:
            parts = line.split(":", 2)
            if len(parts) >= 3:
                filepath = parts[0].lstrip("./")
                lineno = parts[1]
                content = parts[2].strip()
                claims.append(Claim(
                    text=f"FIXME/HACK in {filepath}:{lineno} — {content[:200]}",
                    level=ClaimLevel.L0,
                    confidence=0.9,
                    domain=Domain.codebase,
                    topic="todos",
                    entity=filepath,
                    source_type=SourceType.file,
                    source_ref=f"{filepath}:{lineno}",
                    tags=["codebase-health", "urgent"],
                ))
    return claims


def perceive_test_coverage(repo: Path) -> list[Claim]:
    """Check for source files without corresponding test files."""
    src_dir = repo / "src"
    test_dir = repo / "tests"
    if not src_dir.exists() or not test_dir.exists():
        return []

    src_files = {p.stem for p in src_dir.rglob("*.py") if p.stem != "__init__"}
    test_files = {p.stem.removeprefix("test_") for p in test_dir.rglob("test_*.py")}

    untested = src_files - test_files
    if not untested:
        return []

    claims = [Claim(
        text=f"{len(untested)} source modules have no corresponding test file: {', '.join(sorted(untested)[:10])}{'...' if len(untested) > 10 else ''}",
        level=ClaimLevel.L0,
        confidence=0.6,
        domain=Domain.codebase,
        topic="test-coverage",
        source_type=SourceType.file,
        source_ref=f"src/ vs tests/ comparison",
        tags=["codebase-health", "test-gaps"],
    )]
    return claims


def perceive_lint(repo: Path) -> list[Claim]:
    """Run ruff and report issue count."""
    output = _run(["ruff", "check", "src/", "--quiet", "--statistics"], cwd=repo)
    if not output:
        return []

    lines = [l for l in output.splitlines() if l.strip()]
    if not lines:
        return [Claim(
            text="Codebase passes ruff lint with no issues",
            level=ClaimLevel.L0,
            confidence=0.95,
            domain=Domain.codebase,
            topic="lint",
            source_type=SourceType.file,
            source_ref="ruff check src/",
            tags=["codebase-health", "positive"],
        )]

    return [Claim(
        text=f"Ruff lint found {len(lines)} issue categories in src/",
        level=ClaimLevel.L0,
        confidence=0.9,
        domain=Domain.codebase,
        topic="lint",
        source_type=SourceType.file,
        source_ref="ruff check src/ --statistics",
        tags=["codebase-health", "lint"],
    )]


def perceive_recent_commits(repo: Path, count: int = 10) -> list[Claim]:
    """Summarize recent commit activity."""
    output = _run(
        ["git", "log", f"-{count}", "--oneline"],
        cwd=repo,
    )
    if not output:
        return []

    lines = output.splitlines()
    return [Claim(
        text=f"Last {len(lines)} commits: {'; '.join(lines[:5])}{'...' if len(lines) > 5 else ''}",
        level=ClaimLevel.L0,
        confidence=0.95,
        domain=Domain.codebase,
        topic="activity",
        source_type=SourceType.commit,
        source_ref=f"git log -{count} --oneline",
        tags=["codebase-health", "activity"],
    )]


def run(repo: Path, store: SQLiteStore) -> list[Claim]:
    """Run all codebase perception and write claims to store."""
    all_claims: list[Claim] = []

    for perceiver_fn in [
        perceive_git_churn,
        perceive_todos,
        perceive_test_coverage,
        perceive_lint,
        perceive_recent_commits,
    ]:
        claims = perceiver_fn(repo)
        for claim in claims:
            store.write_claim(claim)
        all_claims.extend(claims)

    return all_claims


def main() -> None:
    parser = argparse.ArgumentParser(description="Codebase perceiver — writes L0 Claims from git/lint/tests")
    parser.add_argument("--repo", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--db", type=Path, default=Path("knowledge.db"), help="SQLite database path")
    args = parser.parse_args()

    store = SQLiteStore(db_path=args.db)
    claims = run(repo=args.repo, store=store)
    print(f"Wrote {len(claims)} claims to {args.db}")
    for c in claims:
        print(f"  [{c.level.value}] {c.topic}: {c.text[:100]}")
    store.close()


if __name__ == "__main__":
    main()
