from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ArtifactStore:
    """Filesystem-based artifact persistence layer.

    Agents write typed artifacts; Orchestrator and Assembler read by reference.
    Path layout: {base_dir}/{run_id}/{agent_id}.json
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def write(self, run_id: str, agent_id: str, artifact: BaseModel) -> str:
        """Write artifact to store. Returns the artifact file path."""
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = run_dir / f"{agent_id}.json"
        artifact_path.write_text(artifact.model_dump_json(indent=2))
        return str(artifact_path)

    def read(self, run_id: str, agent_id: str, model_class: type[T]) -> T:
        """Read artifact from store and validate against model_class."""
        artifact_path = self.base_dir / run_id / f"{agent_id}.json"
        if not artifact_path.exists():
            raise FileNotFoundError(
                f"No artifact found for agent '{agent_id}' in run '{run_id}'"
            )
        data = json.loads(artifact_path.read_text())
        return model_class.model_validate(data)

    def list_artifacts(self, run_id: str) -> list[str]:
        """List all agent_ids that have artifacts for this run."""
        run_dir = self.base_dir / run_id
        if not run_dir.exists():
            return []
        return sorted(p.stem for p in run_dir.glob("*.json"))

    def exists(self, run_id: str, agent_id: str) -> bool:
        """Check if artifact exists without reading it."""
        return (self.base_dir / run_id / f"{agent_id}.json").exists()
