from dataclasses import dataclass
import time
from typing import Any, Callable, Optional, Tuple, Type


Predicate = Callable[[Any], bool]
Operation = Callable[[], Any]
Sleep = Callable[[float], None]
Clock = Callable[[], float]
AttemptObserver = Callable[["RetryAttemptSnapshot"], None]


@dataclass(frozen=True)
class RetryPolicy:
    """Boundaries for retrying an automation operation."""

    max_attempts: Optional[int] = None
    max_duration: Optional[float] = None
    interval: float = 0.0
    retry_on: Tuple[Type[Exception], ...] = (Exception,)

    def __post_init__(self):
        if self.max_attempts is None and self.max_duration is None:
            raise ValueError("max_attempts or max_duration is required")
        if self.max_attempts is not None and self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.max_duration is not None and self.max_duration < 0:
            raise ValueError("max_duration must be >= 0")
        if self.interval < 0:
            raise ValueError("interval must be >= 0")

    def can_retry(self, attempts: int, elapsed: float) -> bool:
        if self.max_attempts is not None and attempts >= self.max_attempts:
            return False
        if self.max_duration is not None and elapsed >= self.max_duration:
            return False
        return True

    def should_retry_exception(self, exc: Exception) -> bool:
        return isinstance(exc, self.retry_on)


@dataclass(frozen=True)
class RetryResult:
    """Result returned when retrying finishes without raising."""

    success: bool
    value: Any
    attempts: int
    elapsed: float
    last_exception: Optional[Exception] = None


@dataclass(frozen=True)
class RetryAttemptSnapshot:
    """Observed state after a handled retry attempt."""

    attempt: int
    elapsed: float
    value: Any
    exception: Optional[Exception]
    will_retry: bool


def retry_until(
    operation: Operation,
    *,
    predicate: Predicate = bool,
    policy: RetryPolicy,
    sleep: Sleep = time.sleep,
    monotonic: Clock = time.monotonic,
    on_attempt: Optional[AttemptObserver] = None,
) -> RetryResult:
    """Run ``operation`` until ``predicate`` accepts its value or policy ends."""

    attempts = 0
    start = monotonic()
    last_value = None
    last_exception = None

    while True:
        attempts += 1
        last_exception = None

        try:
            last_value = operation()
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception as exc:
            if not policy.should_retry_exception(exc):
                raise
            last_exception = exc
            last_value = None
        else:
            if predicate(last_value):
                elapsed = monotonic() - start
                _observe_attempt(
                    on_attempt,
                    attempt=attempts,
                    elapsed=elapsed,
                    value=last_value,
                    exception=None,
                    will_retry=False,
                )
                return RetryResult(
                    success=True,
                    value=last_value,
                    attempts=attempts,
                    elapsed=elapsed,
                )

        elapsed = monotonic() - start
        will_retry = policy.can_retry(attempts, elapsed)
        _observe_attempt(
            on_attempt,
            attempt=attempts,
            elapsed=elapsed,
            value=last_value,
            exception=last_exception,
            will_retry=will_retry,
        )
        if not will_retry:
            return RetryResult(
                success=False,
                value=last_value,
                attempts=attempts,
                elapsed=elapsed,
                last_exception=last_exception,
            )

        sleep(policy.interval)


def _observe_attempt(
    observer: Optional[AttemptObserver],
    *,
    attempt: int,
    elapsed: float,
    value: Any,
    exception: Optional[Exception],
    will_retry: bool,
) -> None:
    if observer is None:
        return
    observer(
        RetryAttemptSnapshot(
            attempt=attempt,
            elapsed=elapsed,
            value=value,
            exception=exception,
            will_retry=will_retry,
        )
    )
