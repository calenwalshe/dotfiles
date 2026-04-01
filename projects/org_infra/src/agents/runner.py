"""Agent runner — executes agents via `claude -p` subprocess.

Each agent gets a system prompt + artifact context. Runner captures output,
parses it as JSON, writes to artifact store, handles timeout and failure.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentResult:
    agent_id: str
    success: bool
    artifact: dict[str, Any] | None = None
    raw_output: str = ""
    error: str = ""
    tokens_used: int = 0
    duration_seconds: float = 0.0


@dataclass
class AgentRunner:
    """Executes agents via `claude -p` subprocess."""

    timeout_seconds: int = 120
    claude_cmd: str = "claude"

    def run(
        self,
        agent_id: str,
        system_prompt: str,
        context: dict[str, Any],
        output_schema_hint: str = "",
    ) -> AgentResult:
        """Run an agent via claude -p subprocess.

        Args:
            agent_id: Identifier for this agent (e.g., "uxr", "pm")
            system_prompt: Agent-specific system prompt
            context: Dict of artifact context to inject into the prompt
            output_schema_hint: Description of expected JSON output format

        Returns:
            AgentResult with parsed artifact or error
        """
        prompt = self._build_prompt(system_prompt, context, output_schema_hint)
        start = time.time()

        try:
            result = subprocess.run(
                [self.claude_cmd, "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            duration = time.time() - start

            if result.returncode != 0:
                return AgentResult(
                    agent_id=agent_id,
                    success=False,
                    raw_output=result.stdout,
                    error=f"claude exited with code {result.returncode}: {result.stderr[:500]}",
                    duration_seconds=duration,
                )

            return self._parse_output(agent_id, result.stdout, duration)

        except subprocess.TimeoutExpired:
            return AgentResult(
                agent_id=agent_id,
                success=False,
                error=f"Timeout after {self.timeout_seconds}s",
                duration_seconds=self.timeout_seconds,
            )
        except FileNotFoundError:
            return AgentResult(
                agent_id=agent_id,
                success=False,
                error=f"claude CLI not found at '{self.claude_cmd}'",
                duration_seconds=time.time() - start,
            )

    def _build_prompt(
        self,
        system_prompt: str,
        context: dict[str, Any],
        output_schema_hint: str,
    ) -> str:
        """Build the full prompt with system prompt + context injection."""
        parts = [system_prompt, "\n\n## Context\n"]

        for key, value in context.items():
            if isinstance(value, dict):
                parts.append(f"\n### {key}\n```json\n{json.dumps(value, indent=2, default=str)}\n```")
            else:
                parts.append(f"\n### {key}\n{value}")

        if output_schema_hint:
            parts.append(f"\n\n## Output Format\n{output_schema_hint}")

        parts.append(
            "\n\n## Instructions\n"
            "Respond with ONLY a valid JSON object matching the output format above. "
            "No markdown, no explanation, just the JSON."
        )

        return "\n".join(parts)

    def _parse_output(
        self, agent_id: str, raw_output: str, duration: float
    ) -> AgentResult:
        """Parse claude output into an artifact dict."""
        # Try to parse the output JSON
        # claude --output-format json wraps in {"type":"result","result":"..."}
        try:
            wrapper = json.loads(raw_output)
            if isinstance(wrapper, dict) and "result" in wrapper:
                content = wrapper["result"]
            else:
                content = raw_output
        except json.JSONDecodeError:
            content = raw_output

        # Parse the actual artifact JSON from content
        try:
            if isinstance(content, str):
                # Try to find JSON in the content
                artifact = self._extract_json(content)
            else:
                artifact = content

            tokens = self._estimate_tokens(raw_output)

            return AgentResult(
                agent_id=agent_id,
                success=True,
                artifact=artifact,
                raw_output=raw_output,
                tokens_used=tokens,
                duration_seconds=duration,
            )
        except (json.JSONDecodeError, ValueError) as e:
            return AgentResult(
                agent_id=agent_id,
                success=False,
                raw_output=raw_output,
                error=f"Failed to parse output as JSON: {e}",
                duration_seconds=duration,
            )

    def _extract_json(self, text: str) -> dict:
        """Extract JSON object from text that may contain surrounding content."""
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON between { }
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in output")

        # Find matching closing brace
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : i + 1])

        raise ValueError("Unbalanced braces in output")

    def _estimate_tokens(self, raw_output: str) -> int:
        """Estimate token usage from output length. Rough heuristic."""
        # ~4 chars per token is a reasonable estimate
        return len(raw_output) // 4
