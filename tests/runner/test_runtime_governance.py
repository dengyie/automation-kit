"""Runtime governance wiring: platform propagation and exponential backoff."""

import asyncio

import pytest

from automation_core.capabilities import (
    CapabilityExecutionProfile,
    CapabilityExecutor,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
)
from automation_runner.policies import CapabilityPolicy
from automation_runner.runtime import WorkflowRuntime
from automation_runner.workflows import WorkflowStep
from tests.runner.test_runtime import FakeSession


class FakeProvider:
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        platforms=("web",),
        default_cancellation="cooperative",
    )

    def __init__(self, *, fail_times=0):
        self.calls = 0
        self.fail_times = fail_times

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        self.calls += 1
        if self.calls <= self.fail_times:
            return CapabilityResult(
                success=False,
                provider="fake",
                error_code="temporary",
                retryable=True,
            )
        return CapabilityResult(success=True, provider="fake", data={})


def make_runtime(provider, metadata=None):
    registry = CapabilityRegistry()
    registry.register(provider)
    executor = CapabilityExecutor(CapabilityResolver(registry))
    return WorkflowRuntime(
        session_factory=lambda: FakeSession(),
        capability_executor=executor,
        workflow_name="smoke",
        metadata=metadata,
    )


def capability_step(policy=None):
    return WorkflowStep.capability(
        "solve-captcha",
        request=CapabilityRequest(
            capability="visual.challenge",
            operation="solve",
            parameters={},
        ),
        policy=policy,
    )


def test_runtime_passes_workflow_platform_to_capability_resolution():
    runtime = make_runtime(FakeProvider(), metadata={"platform": "web"})

    result = asyncio.run(runtime.arun([capability_step()]))

    assert result.success is True


def test_runtime_platform_mismatch_fails_as_wiring_resolution_error():
    runtime = make_runtime(FakeProvider(), metadata={"platform": "android"})

    result = asyncio.run(runtime.arun([capability_step()]))

    assert result.success is False
    step = result.steps[0]
    # The platform mismatch surfaces at the advisory profile resolution, so
    # the step never attempts a provider call.
    assert step.attempts == 0
    assert step.error is not None
    assert step.error.category.value == "resolution"


def test_runtime_exponential_backoff_grows_across_attempts(monkeypatch):
    provider = FakeProvider(fail_times=2)
    runtime = make_runtime(provider)
    delays = []

    async def fake_sleep(delay, *args, **kwargs):
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = asyncio.run(
        runtime.arun(
            [
                capability_step(
                    CapabilityPolicy(
                        max_attempts=3, backoff=0.5, backoff_multiplier=2.0
                    )
                )
            ]
        )
    )

    assert result.success is True
    assert provider.calls == 3
    # attempt 1 -> base delay, attempt 2 -> doubled.
    assert delays == [0.5, 1.0]


def test_runtime_fixed_backoff_keeps_historical_behavior(monkeypatch):
    provider = FakeProvider(fail_times=2)
    runtime = make_runtime(provider)
    delays = []

    async def fake_sleep(delay, *args, **kwargs):
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = asyncio.run(
        runtime.arun(
            [capability_step(CapabilityPolicy(max_attempts=3, backoff=0.5))]
        )
    )

    assert result.success is True
    assert delays == [0.5, 0.5]


# --- review fixes 2026-11: unavailable mapping + yaml policy field -----------


def test_runtime_reports_all_breakers_open_as_provider_unavailable():
    from automation_core.capabilities import (
        CapabilityResult,
        HealthPolicy,
        ProviderHealthBook,
    )

    class AlwaysFailing(FakeProvider):
        async def execute(self, request, context):
            return CapabilityResult(
                success=False,
                provider="fake",
                error_code="temporary",
                retryable=False,
            )

    registry = CapabilityRegistry()
    registry.register(AlwaysFailing(), name="only")
    book = ProviderHealthBook(HealthPolicy(failure_threshold=1, cooldown_seconds=30.0))
    executor = CapabilityExecutor(CapabilityResolver(registry, health=book))
    book.record_failure("only")  # force the single breaker open
    runtime = WorkflowRuntime(
        session_factory=lambda: FakeSession(),
        capability_executor=executor,
        workflow_name="smoke",
    )

    result = asyncio.run(runtime.arun([capability_step()]))

    assert result.success is False
    step = result.steps[0]
    assert step.error is not None
    assert step.error.category.value == "resolution"
    assert step.error.code == "provider_unavailable"
    assert step.capability_result.error_code == "provider_unavailable"


def test_yaml_loader_parses_backoff_multiplier():
    from automation_runner.yaml_loader import _build_policy

    policy = _build_policy(
        {"max_attempts": 3, "backoff": 0.5, "backoff_multiplier": 2.0}, 0
    )
    assert policy.backoff == 0.5
    assert policy.backoff_multiplier == 2.0

    default_policy = _build_policy({"max_attempts": 2}, 0)
    assert default_policy.backoff_multiplier == 1.0
