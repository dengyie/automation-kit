"""Deterministic provider health book: closed / open / half-open transitions."""

import pytest

from automation_core.capabilities import HealthPolicy, ProviderHealthBook


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_book(**policy) -> tuple:
    clock = FakeClock()
    book = ProviderHealthBook(HealthPolicy(**policy), clock=clock)
    return book, clock


def test_healthy_provider_stays_closed_on_success():
    book, _ = make_book()

    assert book.probe("p") is True
    book.record_success("p")

    assert book.snapshot("p").state == "closed"
    assert book.snapshot("p").consecutive_failures == 0
    assert book.probe("p") is True


def test_failures_below_threshold_keep_breaker_closed():
    book, _ = make_book(failure_threshold=3)

    book.record_failure("p")
    book.record_failure("p")

    assert book.snapshot("p").state == "closed"
    assert book.snapshot("p").consecutive_failures == 2
    assert book.probe("p") is True


def test_threshold_failures_open_breaker_and_refuse_probes():
    book, _ = make_book(failure_threshold=2, cooldown_seconds=30.0)

    book.record_failure("p")
    book.record_failure("p")

    assert book.snapshot("p").state == "open"
    assert book.probe("p") is False


def test_cooldown_elapsed_grants_single_half_open_probe():
    book, clock = make_book(failure_threshold=1, cooldown_seconds=30.0)

    book.record_failure("p")
    assert book.probe("p") is False

    clock.advance(30.0)
    assert book.probe("p") is True
    # Only one in-flight probe while half-open.
    assert book.probe("p") is False


def test_half_open_failure_reopens_with_fresh_cooldown():
    book, clock = make_book(failure_threshold=1, cooldown_seconds=30.0)

    book.record_failure("p")
    clock.advance(30.0)
    assert book.probe("p") is True

    book.record_failure("p")
    assert book.snapshot("p").state == "open"
    # A fresh cooldown window starts at the failure time.
    clock.advance(29.0)
    assert book.probe("p") is False
    clock.advance(1.0)
    assert book.probe("p") is True


def test_half_open_success_closes_breaker():
    book, clock = make_book(failure_threshold=1, cooldown_seconds=30.0)

    book.record_failure("p")
    clock.advance(30.0)
    assert book.probe("p") is True

    book.record_success("p")

    assert book.snapshot("p").state == "closed"
    assert book.snapshot("p").consecutive_failures == 0
    assert book.probe("p") is True


def test_providers_are_tracked_independently():
    book, _ = make_book(failure_threshold=1)

    book.record_failure("primary")

    assert book.snapshot("primary").state == "open"
    assert book.snapshot("secondary").state == "closed"
    assert book.probe("secondary") is True


def test_policy_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="failure_threshold"):
        HealthPolicy(failure_threshold=0)
    with pytest.raises(ValueError, match="cooldown_seconds"):
        HealthPolicy(cooldown_seconds=-1.0)
