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

    def start(self, started_at: Optional[float] = None) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = time() if started_at is None else started_at
        self.finished_at = None
        self.outcome = None

    def succeed(
        self,
        outcome: str = "succeeded",
        finished_at: Optional[float] = None,
    ) -> None:
        self.status = RunStatus.SUCCEEDED
        self.finished_at = time() if finished_at is None else finished_at
        self.outcome = outcome

    def fail(
        self,
        outcome: str = "failed",
        finished_at: Optional[float] = None,
    ) -> None:
        self.status = RunStatus.FAILED
        self.finished_at = time() if finished_at is None else finished_at
        self.outcome = outcome

    def cancel(
        self,
        outcome: str = "cancelled",
        finished_at: Optional[float] = None,
    ) -> None:
        self.status = RunStatus.CANCELLED
        self.finished_at = time() if finished_at is None else finished_at
        self.outcome = outcome
