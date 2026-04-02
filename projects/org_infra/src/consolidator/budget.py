"""Budget tracker for LLM calls during consolidation cycles.

Tracks cumulative cost per cycle with model-specific pricing.
Stops making calls when budget cap is reached.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Pricing per million tokens (USD)
PRICING = {
    "haiku": {"input": 0.25, "output": 1.25},
    "sonnet": {"input": 3.0, "output": 15.0},
}


@dataclass
class CallRecord:
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


@dataclass
class BudgetTracker:
    """Track LLM costs per consolidation cycle."""

    budget_cap: float = 0.50
    calls: list[CallRecord] = field(default_factory=list)
    _cumulative_cost: float = 0.0
    queued_count: int = 0  # how many calls were skipped due to budget

    @property
    def cumulative_cost(self) -> float:
        return self._cumulative_cost

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.budget_cap - self._cumulative_cost)

    @property
    def budget_exceeded(self) -> bool:
        return self._cumulative_cost >= self.budget_cap

    def record_call(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record a completed LLM call. Returns cost of this call."""
        pricing = PRICING.get(model, PRICING["haiku"])
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        record = CallRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
        self.calls.append(record)
        self._cumulative_cost += cost
        return cost

    def can_afford(self, model: str, estimated_tokens: int = 1000) -> bool:
        """Check if we can afford another call of this model type."""
        pricing = PRICING.get(model, PRICING["haiku"])
        estimated_cost = (estimated_tokens * pricing["input"] + estimated_tokens * pricing["output"]) / 1_000_000
        return (self._cumulative_cost + estimated_cost) <= self.budget_cap

    def record_queued(self, count: int = 1) -> None:
        """Record that calls were queued (not made) due to budget."""
        self.queued_count += count

    def summary(self) -> dict:
        return {
            "total_calls": len(self.calls),
            "cumulative_cost_usd": round(self._cumulative_cost, 6),
            "budget_cap_usd": self.budget_cap,
            "budget_remaining_usd": round(self.budget_remaining, 6),
            "queued_due_to_budget": self.queued_count,
            "calls_by_model": self._calls_by_model(),
        }

    def _calls_by_model(self) -> dict:
        by_model: dict[str, dict] = {}
        for call in self.calls:
            if call.model not in by_model:
                by_model[call.model] = {"count": 0, "cost": 0.0, "input_tokens": 0, "output_tokens": 0}
            by_model[call.model]["count"] += 1
            by_model[call.model]["cost"] += call.cost
            by_model[call.model]["input_tokens"] += call.input_tokens
            by_model[call.model]["output_tokens"] += call.output_tokens
        return by_model
