"""Markdown projector — generates human-readable views from the knowledge store.

Reads claims, decisions, experiments, contradictions from the store.
Writes MEMORY.md, decision-journal.md, and knowledge-bank/ pages.

Run standalone:
    python -m src.projectors.markdown --db knowledge.db --output-dir projections/
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from src.protocols.schemas import (
    Claim,
    ClaimLevel,
    Contradiction,
    Decision,
    Experiment,
    Problem,
    ProblemStatus,
)
from src.protocols.sqlite_store import SQLiteStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dt_short(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d")


def project_memory_index(store: SQLiteStore) -> str:
    """Generate MEMORY.md — the index of actionable knowledge."""
    lines = ["# Knowledge Store — Index", "", f"_Generated: {_dt_short(_now())}_", ""]

    # L3 actionable claims
    l3_claims = store.query_claims(level=ClaimLevel.L3, limit=50)
    if l3_claims:
        lines.append("## Actionable Knowledge (L3)")
        lines.append("")
        for c in l3_claims:
            conf = f"{c.confidence:.0%}"
            topic_tag = f" [{c.topic}]" if c.topic else ""
            lines.append(f"- **{conf}**{topic_tag} {c.text}")
        lines.append("")

    # L2 validated claims
    l2_claims = store.query_claims(level=ClaimLevel.L2, limit=30)
    if l2_claims:
        lines.append("## Validated Knowledge (L2)")
        lines.append("")
        for c in l2_claims:
            conf = f"{c.confidence:.0%}"
            topic_tag = f" [{c.topic}]" if c.topic else ""
            lines.append(f"- **{conf}**{topic_tag} {c.text}")
        lines.append("")

    # Active problems
    problems = store.query_problems(status=ProblemStatus.discovered, limit=10)
    problems += store.query_problems(status=ProblemStatus.approved, limit=10)
    if problems:
        lines.append("## Open Problems")
        lines.append("")
        for p in sorted(problems, key=lambda x: -x.score):
            score = f"{p.score:.2f}"
            status = p.status.value
            lines.append(f"- [{status}] (score: {score}) {p.description}")
        lines.append("")

    # Unresolved contradictions
    contradictions = store.query_contradictions(unresolved_only=True, limit=10)
    if contradictions:
        lines.append("## Unresolved Contradictions")
        lines.append("")
        for ctr in contradictions:
            claim_a = store.get_claim(ctr.claim_a_id)
            claim_b = store.get_claim(ctr.claim_b_id)
            a_text = claim_a.text[:80] if claim_a else f"[{ctr.claim_a_id}]"
            b_text = claim_b.text[:80] if claim_b else f"[{ctr.claim_b_id}]"
            lines.append(f"- **Conflict** ({_dt_short(ctr.detected_at)})")
            lines.append(f"  - A: {a_text}")
            lines.append(f"  - B: {b_text}")
        lines.append("")

    # Stats
    all_claims = store.query_claims(limit=10000)
    level_counts = {}
    for c in all_claims:
        level_counts[c.level.value] = level_counts.get(c.level.value, 0) + 1

    lines.append("## Store Stats")
    lines.append("")
    for level in ["L0", "L1", "L2", "L3"]:
        count = level_counts.get(level, 0)
        lines.append(f"- {level}: {count} claims")
    lines.append(f"- Contradictions (unresolved): {len(contradictions) if contradictions else 0}")
    lines.append("")

    return "\n".join(lines)


def project_decision_journal(store: SQLiteStore) -> str:
    """Generate decision-journal.md — chronological decisions with evidence."""
    lines = ["# Decision Journal", "", f"_Generated: {_dt_short(_now())}_", ""]

    decisions = store.query_decisions(limit=50)
    if not decisions:
        lines.append("_No decisions recorded._")
        return "\n".join(lines)

    for d in decisions:
        lines.append(f"### {d.topic}")
        lines.append(f"**Chose:** {d.chosen_option}  ")
        lines.append(f"**Confidence:** {d.confidence:.0%}  ")
        lines.append(f"**Date:** {_dt_short(d.timestamp)}  ")
        lines.append("")
        lines.append(f"**Reasoning:** {d.reasoning}")
        lines.append("")
        if d.alternatives_rejected:
            lines.append("**Rejected:**")
            for alt in d.alternatives_rejected:
                lines.append(f"- ~~{alt.option}~~ — {alt.reason}")
            lines.append("")
        if d.evidence_ids:
            lines.append(f"**Evidence:** {len(d.evidence_ids)} item(s) linked")
            lines.append("")
        if d.outcome:
            lines.append(f"**Outcome:** {d.outcome}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def project_experiment_log(store: SQLiteStore) -> str:
    """Generate experiment-log.md — all experiments with results."""
    lines = ["# Experiment Log", "", f"_Generated: {_dt_short(_now())}_", ""]

    experiments = store.query_experiments(limit=100)
    if not experiments:
        lines.append("_No experiments recorded._")
        return "\n".join(lines)

    kept = [e for e in experiments if e.kept]
    discarded = [e for e in experiments if not e.kept]

    lines.append(f"**Total:** {len(experiments)} | **Kept:** {len(kept)} | **Discarded:** {len(discarded)}")
    lines.append("")

    if kept:
        lines.append("## Kept (improvements)")
        lines.append("")
        lines.append("| Hypothesis | Metric | Baseline | Result | Duration |")
        lines.append("|---|---|---|---|---|")
        for e in kept:
            metric = e.metric_name or "—"
            val = f"{e.metric_value:.4f}" if e.metric_value is not None else "—"
            base = f"{e.baseline_value:.4f}" if e.baseline_value is not None else "—"
            dur = f"{e.duration_seconds:.0f}s" if e.duration_seconds else "—"
            lines.append(f"| {e.hypothesis[:60]} | {metric} | {base} | {val} | {dur} |")
        lines.append("")

    if discarded:
        lines.append("## Discarded (no improvement)")
        lines.append("")
        lines.append("| Hypothesis | Metric | Baseline | Result |")
        lines.append("|---|---|---|---|")
        for e in discarded:
            metric = e.metric_name or "—"
            val = f"{e.metric_value:.4f}" if e.metric_value is not None else "—"
            base = f"{e.baseline_value:.4f}" if e.baseline_value is not None else "—"
            lines.append(f"| {e.hypothesis[:60]} | {metric} | {base} | {val} |")
        lines.append("")

    return "\n".join(lines)


def run(store: SQLiteStore, output_dir: Path) -> list[Path]:
    """Generate all projections and write to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    projections = [
        ("MEMORY.md", project_memory_index),
        ("decision-journal.md", project_decision_journal),
        ("experiment-log.md", project_experiment_log),
    ]

    for filename, project_fn in projections:
        content = project_fn(store)
        path = output_dir / filename
        path.write_text(content)
        written.append(path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown projector — store → human-readable views")
    parser.add_argument("--db", type=Path, default=Path("knowledge.db"), help="SQLite database path")
    parser.add_argument("--output-dir", type=Path, default=Path("projections"), help="Output directory")
    args = parser.parse_args()

    store = SQLiteStore(db_path=args.db)
    written = run(store=store, output_dir=args.output_dir)
    print(f"Wrote {len(written)} projections to {args.output_dir}/")
    for p in written:
        print(f"  {p}")
    store.close()


if __name__ == "__main__":
    main()
