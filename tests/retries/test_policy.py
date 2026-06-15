import pytest

from automation_core.retries import RetryPolicy, retry_until


def test_policy_requires_a_boundary():
    with pytest.raises(ValueError, match="max_attempts or max_duration"):
        RetryPolicy()


def test_retry_until_requires_explicit_policy():
    with pytest.raises(TypeError):
        retry_until(lambda: True)


def test_retry_until_returns_on_first_success():
    calls = []

    def operation():
        calls.append("call")
        return "ready"

    result = retry_until(
        operation,
        predicate=lambda value: value == "ready",
        policy=RetryPolicy(max_attempts=3, interval=0),
        sleep=lambda _: None,
    )

    assert result.success is True
    assert result.value == "ready"
    assert result.attempts == 1
    assert calls == ["call"]


def test_retry_until_retries_until_predicate_matches():
    values = iter(["not-ready", "not-ready", "ready"])

    result = retry_until(
        lambda: next(values),
        predicate=lambda value: value == "ready",
        policy=RetryPolicy(max_attempts=5, interval=0),
        sleep=lambda _: None,
    )

    assert result.success is True
    assert result.value == "ready"
    assert result.attempts == 3


def test_retry_until_stops_at_max_attempts():
    attempts = []

    result = retry_until(
        lambda: attempts.append("call") or "not-ready",
        predicate=lambda value: value == "ready",
        policy=RetryPolicy(max_attempts=3, interval=0),
        sleep=lambda _: None,
    )

    assert result.success is False
    assert result.value == "not-ready"
    assert result.attempts == 3
    assert attempts == ["call", "call", "call"]


def test_retry_until_retries_configured_exceptions():
    calls = []

    def operation():
        calls.append("call")
        if len(calls) < 2:
            raise TimeoutError("not ready")
        return "ready"

    result = retry_until(
        operation,
        predicate=lambda value: value == "ready",
        policy=RetryPolicy(
            max_attempts=3,
            interval=0,
            retry_on=(TimeoutError,),
        ),
        sleep=lambda _: None,
    )

    assert result.success is True
    assert result.value == "ready"
    assert result.attempts == 2
    assert result.last_exception is None


def test_retry_until_returns_last_retryable_exception():
    result = retry_until(
        lambda: (_ for _ in ()).throw(TimeoutError("not ready")),
        predicate=bool,
        policy=RetryPolicy(
            max_attempts=2,
            interval=0,
            retry_on=(TimeoutError,),
        ),
        sleep=lambda _: None,
    )

    assert result.success is False
    assert result.value is None
    assert result.attempts == 2
    assert isinstance(result.last_exception, TimeoutError)


def test_retry_until_raises_non_retryable_exception():
    with pytest.raises(ValueError, match="bad input"):
        retry_until(
            lambda: (_ for _ in ()).throw(ValueError("bad input")),
            predicate=bool,
            policy=RetryPolicy(
                max_attempts=3,
                interval=0,
                retry_on=(TimeoutError,),
            ),
            sleep=lambda _: None,
        )


def test_retry_until_does_not_swallow_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        retry_until(
            lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            predicate=bool,
            policy=RetryPolicy(max_attempts=3, interval=0),
            sleep=lambda _: None,
        )


def test_retry_until_stops_at_max_duration():
    now = [0.0]

    def monotonic():
        return now[0]

    def sleep(seconds):
        now[0] += seconds

    result = retry_until(
        lambda: "not-ready",
        predicate=lambda value: value == "ready",
        policy=RetryPolicy(max_duration=1.0, interval=0.6),
        sleep=sleep,
        monotonic=monotonic,
    )

    assert result.success is False
    assert result.attempts == 3
    assert result.elapsed >= 1.0
