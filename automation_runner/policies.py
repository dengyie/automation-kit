from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CapabilityPolicy:
    timeout: Optional[float] = None
    max_attempts: int = 1
    backoff: float = 0.0
    fallback: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff < 0:
            raise ValueError("backoff must be >= 0")
