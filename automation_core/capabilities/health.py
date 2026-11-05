"""Deterministic provider health tracking (circuit-breaker semantics).

Pure stdlib. The book is a composition-root-owned object: the resolver asks
``probe`` before handing a provider out and the executor reports the outcome
via ``record_success`` / ``record_failure``. State transitions are driven by
an injected monotonic clock so tests are fully deterministic.

States per provider registration name:

- ``closed``: healthy; every probe is allowed.
- ``open``: ``failure_threshold`` consecutive failures; probes refused until
  ``cooldown_seconds`` elapsed on the clock.
- ``half_open``: cooldown elapsed; exactly one probe is allowed through to
  re-qualify the provider. Success closes the breaker; a failure re-opens it
  with a fresh cooldown.
"""

import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class HealthPolicy:
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")


@dataclass(frozen=True)
class HealthSnapshot:
    state: str
    consecutive_failures: int


class _ProviderHealth:
    __slots__ = ("state", "consecutive_failures", "opened_at", "probe_granted")

    def __init__(self) -> None:
        self.state = "closed"
        self.consecutive_failures = 0
        self.opened_at: Optional[float] = None
        self.probe_granted = False


class ProviderHealthBook:
    """Health ledger keyed by provider registration name."""

    def __init__(
        self,
        policy: Optional[HealthPolicy] = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.policy = policy or HealthPolicy()
        self._clock = clock
        self._providers: Dict[str, _ProviderHealth] = {}

    def _entry(self, name: str) -> _ProviderHealth:
        entry = self._providers.get(name)
        if entry is None:
            entry = _ProviderHealth()
            self._providers[name] = entry
        return entry

    def probe(self, name: str) -> bool:
        """Whether ``name`` may execute right now.

        Grants at most one in-flight probe while ``half_open``; an open
        breaker only flips to half-open once the cooldown has elapsed.
        """
        entry = self._entry(name)
        now = self._clock()
        if entry.state == "open":
            if entry.opened_at is None or now - entry.opened_at < self.policy.cooldown_seconds:
                return False
            entry.state = "half_open"
            entry.probe_granted = True
            return True
        if entry.state == "half_open":
            if entry.probe_granted:
                return False
            entry.probe_granted = True
            return True
        return True

    def record_success(self, name: str) -> None:
        entry = self._entry(name)
        entry.state = "closed"
        entry.consecutive_failures = 0
        entry.opened_at = None
        entry.probe_granted = False

    def record_failure(self, name: str) -> None:
        entry = self._entry(name)
        entry.consecutive_failures += 1
        if entry.state == "half_open" or entry.consecutive_failures >= self.policy.failure_threshold:
            entry.state = "open"
            entry.opened_at = self._clock()
            entry.probe_granted = False

    def snapshot(self, name: str) -> HealthSnapshot:
        entry = self._entry(name)
        return HealthSnapshot(
            state=entry.state,
            consecutive_failures=entry.consecutive_failures,
        )
