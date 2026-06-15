import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import time
from typing import Dict, Optional


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_type: str
    name: str
    path: Path
    task_id: Optional[str] = None
    created_at: float = field(default_factory=time)
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["path"] = str(self.path)
        return data

    def metadata_json(self) -> str:
        return json.dumps(self.metadata, sort_keys=True)


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root

    def _sanitize_name(self, name: str) -> str:
        cleaned = name.replace("\\", "/").split("/")[-1].strip()
        if cleaned in {"", ".", ".."}:
            raise ValueError("invalid artifact name")
        return cleaned.replace(" ", "_")

    def build_path(self, run_id: str, artifact_type: str, name: str) -> Path:
        safe_name = self._sanitize_name(name)
        return self.root / run_id / artifact_type / safe_name

    def record(
        self,
        run_id: str,
        artifact_type: str,
        name: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ArtifactRecord:
        path = self.build_path(run_id, artifact_type, name)
        return ArtifactRecord(
            artifact_type=artifact_type,
            name=name,
            path=path,
            task_id=task_id,
            metadata=metadata or {},
        )
