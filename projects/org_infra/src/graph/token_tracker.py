"""Token tracking — per-agent and per-run cost instrumentation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Approximate pricing per 1M tokens (Claude Sonnet)
INPUT_COST_PER_1M = 3.0
OUTPUT_COST_PER_1M = 15.0


@dataclass
class AgentTokenUsage:
    agent_id: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.input_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (self.output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
        return input_cost + output_cost


@dataclass
class TokenTracker:
    """Tracks per-agent and per-run token usage."""

    run_id: str = ""
    agent_usage: dict[str, AgentTokenUsage] = field(default_factory=dict)

    def record(self, agent_id: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record token usage for an agent."""
        if agent_id not in self.agent_usage:
            self.agent_usage[agent_id] = AgentTokenUsage(agent_id=agent_id)
        usage = self.agent_usage[agent_id]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens

    def record_total(self, agent_id: str, total_tokens: int) -> None:
        """Record total tokens (split 40/60 input/output estimate)."""
        input_est = int(total_tokens * 0.4)
        output_est = total_tokens - input_est
        self.record(agent_id, input_est, output_est)

    @property
    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self.agent_usage.values())

    @property
    def total_cost_usd(self) -> float:
        return sum(u.estimated_cost_usd for u in self.agent_usage.values())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON storage."""
        return {
            "run_id": self.run_id,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "agents": {
                agent_id: {
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "total_tokens": u.total_tokens,
                    "estimated_cost_usd": round(u.estimated_cost_usd, 4),
                }
                for agent_id, u in self.agent_usage.items()
            },
        }

    def save(self, runs_dir: str | Path) -> str:
        """Save cost data to runs/{run_id}/cost.json."""
        path = Path(runs_dir) / self.run_id / "cost.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return str(path)

    def exceeds_budget(self, token_budget: int) -> bool:
        """Check if total tokens exceed budget."""
        return self.total_tokens >= token_budget
