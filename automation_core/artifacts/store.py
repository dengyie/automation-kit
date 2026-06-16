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

    def _sanitize_component(self, value: str, field_name: str) -> str:
        cleaned = value.replace("\\", "/").split("/")[-1].strip()
        if cleaned in {"", ".", ".."}:
            raise ValueError(f"invalid {field_name}")
        return cleaned.replace(" ", "_")

    def build_path(self, run_id: str, artifact_type: str, name: str) -> Path:
        safe_run_id = self._sanitize_component(run_id, "run_id")
        safe_artifact_type = self._sanitize_component(
            artifact_type,
            "artifact_type",
        )
        safe_name = self._sanitize_component(name, "artifact name")
        return self.root / safe_run_id / safe_artifact_type / safe_name

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
