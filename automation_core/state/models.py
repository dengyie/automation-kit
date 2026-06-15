from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Optional


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunState:
    run_id: str
    status: RunStatus = RunStatus.PENDING
    started_at: float = field(default_factory=time)
    finished_at: Optional[float] = None
    outcome: Optional[str] = None
