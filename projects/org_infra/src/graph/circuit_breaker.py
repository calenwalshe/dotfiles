"""Circuit breaker for autonomous runs — halts on budget or eval plateau."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.graph.run_config import RunConfig


@dataclass
class CircuitBreaker:
    config: RunConfig
    tokens_used: int = 0
    start_time: float = field(default_factory=time.time)
    gate_eval_history: list[float] = field(default_factory=list)

    def record_tokens(self, count: int) -> None:
        """Record tokens consumed by an agent call."""
        self.tokens_used += count

    def check_budget(self) -> tuple[bool, str]:
        """Check if token or time budget is exhausted. Returns (tripped, reason)."""
        if self.tokens_used >= self.config.token_budget:
            return True, f"Token budget exhausted: {self.tokens_used}/{self.config.token_budget}"

        elapsed = time.time() - self.start_time
        if elapsed >= self.config.time_budget_seconds:
            return True, f"Time budget exhausted: {elapsed:.0f}s/{self.config.time_budget_seconds}s"

        return False, ""

    def check_eval_plateau(self, current_score: float) -> tuple[bool, str]:
        """Check if eval scores have plateaued. Returns (tripped, reason)."""
        self.gate_eval_history.append(current_score)

        if len(self.gate_eval_history) < 2:
            return False, ""

        # Plateau = last 2+ scores show no improvement over the first in the window
        window = self.gate_eval_history[-3:] if len(self.gate_eval_history) >= 3 else self.gate_eval_history
        baseline = window[0]
        recent = window[1:]

        if all(score <= baseline for score in recent):
            return True, (
                f"Eval scores plateaued: {[round(s, 2) for s in window]}. "
                f"No improvement over baseline {baseline:.2f}"
            )

        return False, ""

    def should_halt(self) -> tuple[bool, str]:
        """Combined check — returns (should_halt, reason)."""
        tripped, reason = self.check_budget()
        if tripped:
            return True, reason
        return False, ""
