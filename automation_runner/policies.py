from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CapabilityPolicy:
    timeout: Optional[float] = None
    max_attempts: int = 1
    backoff: float = 0.0
    # ``1.0`` keeps the historical fixed-delay backoff; >1 grows the delay as
    # ``backoff * multiplier ** (attempt - 1)`` across retries of one step.
    backoff_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff < 0:
            raise ValueError("backoff must be >= 0")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be >= 1")
