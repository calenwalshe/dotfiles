"""Openclaw container deployment configuration.

Resolves filesystem paths and verifies claude CLI availability
for running inside the openclaw container.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OpenClawConfig:
    """Configuration for running inside openclaw container."""

    # Filesystem paths (openclaw container mounts)
    workspace_dir: Path = field(default_factory=lambda: Path("/var/lib/openclaw/workspace"))
    artifact_store_dir: Path = field(default_factory=lambda: Path("/var/lib/openclaw/workspace/artifacts"))
    runs_dir: Path = field(default_factory=lambda: Path("/var/lib/openclaw/workspace/runs"))

    # Claude CLI
    claude_cmd: str = "claude"

    def verify(self) -> dict[str, bool | str]:
        """Verify the deployment environment is ready."""
        checks: dict[str, bool | str] = {}

        # Check workspace directory
        checks["workspace_exists"] = self.workspace_dir.exists()

        # Check claude CLI
        claude_path = shutil.which(self.claude_cmd)
        checks["claude_available"] = claude_path is not None
        if claude_path:
            try:
                result = subprocess.run(
                    [self.claude_cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                checks["claude_version"] = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                checks["claude_version"] = "error"
        else:
            checks["claude_version"] = "not found"

        # Create directories if workspace exists
        if checks["workspace_exists"]:
            self.artifact_store_dir.mkdir(parents=True, exist_ok=True)
            self.runs_dir.mkdir(parents=True, exist_ok=True)
            checks["artifact_dir_ready"] = self.artifact_store_dir.exists()
            checks["runs_dir_ready"] = self.runs_dir.exists()
        else:
            checks["artifact_dir_ready"] = False
            checks["runs_dir_ready"] = False

        return checks

    @classmethod
    def for_local_dev(cls) -> OpenClawConfig:
        """Create config for local development (not inside container)."""
        return cls(
            workspace_dir=Path("."),
            artifact_store_dir=Path("./artifacts"),
            runs_dir=Path("./runs"),
        )
