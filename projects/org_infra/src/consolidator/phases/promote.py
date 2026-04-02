"""Phases 4a/4b/4c: Promotion gates.

4a: L0 -> L1 (rule-based: provenance, timestamp, atomicity)
4b: L1 -> L2 (corroboration + Claude Haiku validation)
4c: L2 -> L3 (Claude Sonnet review — human approval gate, not auto-promoted)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.consolidator.audit import AuditLog
from src.consolidator.budget import BudgetTracker
from src.consolidator.config import ConsolidatorConfig
from src.consolidator.phases.contradict import AmbiguousPair
from src.consolidator.phases.corroborate import CorroborationResult
from src.consolidator.store_adapter import ConsolidatorStore
from src.protocols.schemas import ClaimLevel, Evidence, EvidenceStrength, SourceType

# Optional anthropic import
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@dataclass
class L3Candidate:
    """A claim proposed for L3 promotion, pending human approval."""
    claim_id: UUID
    claim_text: str
    reasoning: str


@dataclass
class PromotionResults:
    """Aggregated results from all promotion phases."""
    l0_to_l1_actions: list[str] = field(default_factory=list)
    l1_to_l2_actions: list[str] = field(default_factory=list)
    l2_to_l3_candidates: list[L3Candidate] = field(default_factory=list)
    ambiguous_reviews: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4a: L0 -> L1 (rule-based)
# ---------------------------------------------------------------------------


def run_promote(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
) -> list[str]:
    """Promote L0 claims to L1 if they pass all gates.

    Gates (from config.l0_l1_rules):
    - provenance: source_type and source_ref must be set
    - timestamp: valid_from must be set
    - atomicity: text length must be <= max_text_length
    """
    actions: list[str] = []
    rules = config.l0_l1_rules
    now = datetime.now(timezone.utc)

    l0_claims = store.query_claims(level=ClaimLevel.L0, limit=10000)

    for claim in l0_claims:
        failures: list[str] = []

        # Check provenance
        if rules.provenance_required:
            if not claim.source_type or not claim.source_ref:
                failures.append("missing_provenance")

        # Check timestamp
        if rules.timestamp_required:
            if claim.valid_from is None:
                failures.append("missing_timestamp")

        # Check atomicity (text length)
        if len(claim.text) > rules.max_text_length:
            failures.append(f"text_too_long:{len(claim.text)}>{rules.max_text_length}")

        if failures:
            action = f"skipped:{claim.id}:{','.join(failures)}"
            actions.append(action)
            audit.record(
                phase="promote",
                action="skip",
                claim_id=str(claim.id),
                reason=f"Failed gates: {', '.join(failures)}",
                details={"failures": failures},
            )
        else:
            store.update_claim(claim.id, level=ClaimLevel.L1, promoted_at=now)
            action = f"promoted:{claim.id}"
            actions.append(action)
            audit.record(
                phase="promote",
                action="promote",
                claim_id=str(claim.id),
                reason="All L0->L1 gates passed",
                details={
                    "source_type": claim.source_type.value,
                    "source_ref": claim.source_ref,
                    "text_length": len(claim.text),
                },
            )

    return actions


# ---------------------------------------------------------------------------
# Phase 4b: L1 -> L2 (corroboration + Claude Haiku)
# ---------------------------------------------------------------------------


def _call_haiku(
    client: Any,
    claim_text: str,
    corroborating_texts: list[str],
    budget: BudgetTracker,
) -> dict | None:
    """Call Claude Haiku to validate a corroborated claim. Returns parsed JSON or None."""
    if budget.budget_exceeded or not budget.can_afford("haiku"):
        return None

    evidence_block = "\n".join(f"- {t}" for t in corroborating_texts)
    prompt = (
        f"You are validating a knowledge claim based on independent corroborating evidence.\n\n"
        f"Claim: {claim_text}\n\n"
        f"Independent corroborating sources:\n{evidence_block}\n\n"
        f"Given these independent sources, is this claim validated? "
        f"Respond with JSON only: {{\"validated\": true/false, \"reasoning\": \"...\"}}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-20250414",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        budget.record_call(
            "haiku",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return None


def run_promote_l1_to_l2(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
    corroboration_results: list[CorroborationResult],
    budget: BudgetTracker,
    *,
    llm_client: Any | None = None,
) -> list[str]:
    """Promote corroborated L1 claims to L2 via Claude Haiku validation.

    Args:
        corroboration_results: Output from run_corroborate
        budget: Budget tracker for cost control
        llm_client: Anthropic client (or mock). If None and SDK available, creates one.
    """
    actions: list[str] = []
    now = datetime.now(timezone.utc)

    if llm_client is None:
        if not HAS_ANTHROPIC:
            audit.record(
                phase="promote_l1_l2",
                action="skip",
                claim_id="*",
                reason="anthropic SDK not available",
            )
            return actions
        llm_client = anthropic.Anthropic()

    for result in corroboration_results:
        if budget.budget_exceeded:
            budget.record_queued(len(corroboration_results) - len(actions))
            audit.record(
                phase="promote_l1_l2",
                action="budget_exceeded",
                claim_id=str(result.claim_id),
                reason=f"Budget cap reached: ${budget.cumulative_cost:.4f} >= ${budget.budget_cap:.2f}",
            )
            break

        claim = store.get_claim(result.claim_id)
        if claim is None or claim.level != ClaimLevel.L1:
            continue

        # Get corroborating claim texts
        corr_texts = []
        for cid in result.corroborating_claim_ids:
            c = store.get_claim(cid)
            if c:
                corr_texts.append(c.text)

        response = _call_haiku(llm_client, claim.text, corr_texts, budget)

        if response is None:
            if budget.budget_exceeded:
                budget.record_queued(1)
                audit.record(
                    phase="promote_l1_l2",
                    action="budget_exceeded",
                    claim_id=str(claim.id),
                    reason="Budget cap reached",
                )
            continue

        if response.get("validated", False):
            store.update_claim(claim.id, level=ClaimLevel.L2, promoted_at=now)
            # Write evidence record
            evidence = Evidence(
                claim_id=claim.id,
                content=f"LLM validation: {response.get('reasoning', 'validated')}",
                strength=EvidenceStrength.supports,
                source_type=SourceType.api,
                source_ref="claude-haiku-validation",
            )
            store.write_evidence(evidence)
            action = f"promoted_l2:{claim.id}"
            actions.append(action)
            audit.record(
                phase="promote_l1_l2",
                action="promote",
                claim_id=str(claim.id),
                reason=f"Haiku validated: {response.get('reasoning', '')}",
                details={
                    "corroboration_count": result.corroboration_count,
                    "llm_reasoning": response.get("reasoning", ""),
                },
            )
        else:
            action = f"rejected_l2:{claim.id}"
            actions.append(action)
            audit.record(
                phase="promote_l1_l2",
                action="reject",
                claim_id=str(claim.id),
                reason=f"Haiku rejected: {response.get('reasoning', '')}",
                details={"llm_reasoning": response.get("reasoning", "")},
            )

    return actions


# ---------------------------------------------------------------------------
# Phase 4c: L2 -> L3 (Claude Sonnet — human approval gate)
# ---------------------------------------------------------------------------


def _call_sonnet(
    client: Any,
    claim_text: str,
    budget: BudgetTracker,
) -> dict | None:
    """Call Claude Sonnet to evaluate L3 promotion. Returns parsed JSON or None."""
    if budget.budget_exceeded or not budget.can_afford("sonnet"):
        return None

    prompt = (
        f"You are evaluating whether a validated knowledge claim should be promoted "
        f"to actionable knowledge (highest tier).\n\n"
        f"Claim: {claim_text}\n\n"
        f"Should this validated claim be promoted to actionable knowledge? "
        f"Consider: Is it specific enough to act on? Is it stable/durable? "
        f"Respond with JSON only: {{\"promote\": true/false, \"reasoning\": \"...\"}}"
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        budget.record_call(
            "sonnet",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return None


def run_promote_l2_to_l3(
    store: ConsolidatorStore,
    config: ConsolidatorConfig,
    audit: AuditLog,
    budget: BudgetTracker,
    *,
    llm_client: Any | None = None,
) -> list[L3Candidate]:
    """Propose L2 claims for L3 promotion via Claude Sonnet. Does NOT auto-promote.

    Returns list of L3Candidate for human review.
    """
    candidates: list[L3Candidate] = []

    if llm_client is None:
        if not HAS_ANTHROPIC:
            audit.record(
                phase="promote_l2_l3",
                action="skip",
                claim_id="*",
                reason="anthropic SDK not available",
            )
            return candidates
        llm_client = anthropic.Anthropic()

    l2_claims = store.query_claims(level=ClaimLevel.L2, min_confidence=0.8, limit=10000)

    for claim in l2_claims:
        if budget.budget_exceeded:
            budget.record_queued(1)
            audit.record(
                phase="promote_l2_l3",
                action="budget_exceeded",
                claim_id=str(claim.id),
                reason=f"Budget cap reached: ${budget.cumulative_cost:.4f}",
            )
            continue

        response = _call_sonnet(llm_client, claim.text, budget)

        if response is None:
            if budget.budget_exceeded:
                budget.record_queued(1)
            continue

        if response.get("promote", False):
            candidate = L3Candidate(
                claim_id=claim.id,
                claim_text=claim.text,
                reasoning=response.get("reasoning", ""),
            )
            candidates.append(candidate)
            audit.record(
                phase="promote_l2_l3",
                action="propose_l3",
                claim_id=str(claim.id),
                reason=f"Sonnet proposes L3: {response.get('reasoning', '')}",
                details={"llm_reasoning": response.get("reasoning", "")},
            )
        else:
            audit.record(
                phase="promote_l2_l3",
                action="reject_l3",
                claim_id=str(claim.id),
                reason=f"Sonnet rejects L3: {response.get('reasoning', '')}",
                details={"llm_reasoning": response.get("reasoning", "")},
            )

    return candidates


# ---------------------------------------------------------------------------
# Ambiguous contradiction review (via Claude Sonnet)
# ---------------------------------------------------------------------------


def run_review_ambiguous(
    store: ConsolidatorStore,
    audit: AuditLog,
    ambiguous_pairs: list[AmbiguousPair],
    budget: BudgetTracker,
    *,
    llm_client: Any | None = None,
) -> list[str]:
    """Review ambiguous contradiction pairs using Claude Sonnet.

    For each pair, ask Sonnet whether they truly contradict.
    If yes: write Contradiction. If no: skip.
    """
    actions: list[str] = []

    if not ambiguous_pairs:
        return actions

    if llm_client is None:
        if not HAS_ANTHROPIC:
            return actions
        llm_client = anthropic.Anthropic()

    for pair in ambiguous_pairs:
        if budget.budget_exceeded:
            budget.record_queued(1)
            break

        prompt = (
            f"Do these two claims contradict each other?\n\n"
            f"Claim A: {pair.claim_a_text}\n"
            f"Claim B: {pair.claim_b_text}\n\n"
            f"Respond with JSON only: {{\"contradicts\": true/false, \"reasoning\": \"...\"}}"
        )

        try:
            response = llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            budget.record_call(
                "sonnet",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            parsed = json.loads(text)
        except (json.JSONDecodeError, Exception):
            continue

        if parsed.get("contradicts", False):
            from src.protocols.schemas import Contradiction
            contradiction = Contradiction(
                claim_a_id=pair.claim_a_id,
                claim_b_id=pair.claim_b_id,
            )
            store.write_contradiction(contradiction)
            actions.append(f"contradiction_confirmed:{pair.claim_a_id}:{pair.claim_b_id}")
            audit.record(
                phase="review_ambiguous",
                action="confirm_contradiction",
                claim_id=str(pair.claim_a_id),
                reason=f"Sonnet confirmed contradiction with {pair.claim_b_id}",
                details={"reasoning": parsed.get("reasoning", "")},
            )
        else:
            actions.append(f"contradiction_dismissed:{pair.claim_a_id}:{pair.claim_b_id}")
            audit.record(
                phase="review_ambiguous",
                action="dismiss",
                claim_id=str(pair.claim_a_id),
                reason=f"Sonnet dismissed contradiction with {pair.claim_b_id}",
                details={"reasoning": parsed.get("reasoning", "")},
            )

    return actions
