"""Multi-provider registry, priority selection, health-gated failover.

The governance gate (development.md §11.3) opens with a real second
same-capability provider; these tests exercise deterministic two-provider
failover end to end through the executor, mirroring the slidex
auto-solver -> manual-fallback pair shipped in the same wave.
"""

import asyncio

import pytest

from automation_core.capabilities import (
    CapabilityExecutionProfile,
    CapabilityExecutor,
    CapabilityManifest,
    CapabilityNotFoundError,
    CapabilityOperationNotSupportedError,
    CapabilityProviderUnavailableError,
    CapabilityRegistrationError,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
    HealthPolicy,
    ProviderHealthBook,
)
from automation_core.execution import ExecutionContext


def make_manifest(**overrides) -> CapabilityManifest:
    fields = {
        "name": "visual.challenge",
        "version": "1.0.0",
        "operations": ("solve",),
        "platforms": ("web", "android"),
        "default_cancellation": "cooperative",
    }
    fields.update(overrides)
    return CapabilityManifest(**fields)


class StubProvider:
    def __init__(
        self,
        manifest,
        *,
        outcome="success",
        error_code="temporary",
        retryable=True,
    ):
        self.manifest = manifest
        self.outcome = outcome
        self.error_code = error_code
        self.retryable = retryable
        self.calls = 0

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        self.calls += 1
        if self.outcome == "raise":
            raise RuntimeError("provider socket died")
        if self.outcome == "success":
            return CapabilityResult(
                success=True, provider=self.result_name, data={"who": self.result_name}
            )
        return CapabilityResult(
            success=False,
            provider=self.result_name,
            error_code=self.error_code,
            retryable=self.retryable,
        )


class AutoProvider(StubProvider):
    result_name = "slidex"


class ManualProvider(StubProvider):
    result_name = "slidex-manual"


def make_context() -> ExecutionContext:
    return ExecutionContext(run_id="run-1", task_id="task-1", workflow_name="wf")


def make_request(**parameters) -> CapabilityRequest:
    return CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters=parameters,
    )


def make_executor(*providers, health_policy=None) -> CapabilityExecutor:
    registry = CapabilityRegistry()
    health = ProviderHealthBook(
        health_policy or HealthPolicy(failure_threshold=2, cooldown_seconds=30.0)
    )
    resolver = CapabilityResolver(registry, health=health)
    for name, provider in providers:
        registry.register(provider, name=name)
    return CapabilityExecutor(resolver)


# --- registry multi-provider storage ----------------------------------------


def test_registry_holds_two_providers_under_one_capability():
    registry = CapabilityRegistry()
    auto = AutoProvider(make_manifest())
    manual = ManualProvider(make_manifest())

    registry.register(auto, name="slidex")
    registry.register(manual, name="slidex-manual")

    assert registry.get("visual.challenge") is auto
    assert [entry.name for entry in registry.candidates("visual.challenge")] == [
        "slidex",
        "slidex-manual",
    ]
    assert len(registry.list_manifests()) == 2


def test_registry_rejects_duplicate_registration_name():
    registry = CapabilityRegistry()
    registry.register(AutoProvider(make_manifest()), name="slidex")

    with pytest.raises(CapabilityRegistrationError, match="already registered"):
        registry.register(AutoProvider(make_manifest()), name="slidex")

    replacement = AutoProvider(make_manifest())
    registry.register(replacement, name="slidex", replace=True)
    assert registry.get("visual.challenge") is replacement


def test_unnamed_registration_keeps_single_provider_semantics():
    registry = CapabilityRegistry()
    registry.register(AutoProvider(make_manifest()))

    with pytest.raises(CapabilityRegistrationError, match="already registered"):
        registry.register(AutoProvider(make_manifest()))


def test_candidates_order_by_manifest_priority_then_insertion():
    registry = CapabilityRegistry()
    low = AutoProvider(make_manifest(priority=1))
    high = AutoProvider(make_manifest(priority=10))
    middle = AutoProvider(make_manifest(priority=5))

    registry.register(low, name="low")
    registry.register(high, name="high")
    registry.register(middle, name="middle")

    assert [entry.name for entry in registry.candidates("visual.challenge")] == [
        "high",
        "middle",
        "low",
    ]


def test_manifest_to_dict_includes_priority():
    manifest = make_manifest(priority=7)
    assert manifest.to_dict()["priority"] == 7


# --- resolver selection ------------------------------------------------------


def test_resolver_prefers_higher_priority_candidate():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(priority=1))),
        ("slidex-manual", ManualProvider(make_manifest(priority=5))),
    )

    name, provider = executor.resolver.resolve_candidate(make_request())

    assert name == "slidex-manual"
    assert isinstance(provider, ManualProvider)


def test_resolver_skips_candidates_missing_operation():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(operations=("extract",)))),
        ("slidex-manual", ManualProvider(make_manifest())),
    )

    name, _ = executor.resolver.resolve_candidate(make_request())

    assert name == "slidex-manual"


def test_resolver_raises_operation_error_when_no_candidate_supports_it():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest())),
        ("slidex-manual", ManualProvider(make_manifest())),
    )

    request = CapabilityRequest(
        capability="visual.challenge", operation="extract"
    )
    with pytest.raises(CapabilityOperationNotSupportedError):
        executor.resolver.resolve_candidate(request)


def test_resolver_skips_candidates_missing_platform():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(platforms=("web",)))),
        ("slidex-manual", ManualProvider(make_manifest(platforms=("web", "android")))),
    )

    name, _ = executor.resolver.resolve_candidate(make_request(), platform="android")

    assert name == "slidex-manual"


def test_resolver_raises_not_found_when_no_candidate_supports_platform():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(platforms=("web",)))),
        ("slidex-manual", ManualProvider(make_manifest(platforms=("web",)))),
    )

    with pytest.raises(CapabilityNotFoundError, match="platform"):
        executor.resolver.resolve_candidate(make_request(), platform="android")


# --- executor outcome recording and failover ---------------------------------


def test_executor_failover_to_secondary_on_primary_business_failure():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(), outcome="failure", retryable=False)),
        ("slidex-manual", ManualProvider(make_manifest(), outcome="success")),
    )

    result = asyncio.run(executor.execute(make_request(), make_context()))

    assert result.success is True
    assert result.data == {"who": "slidex-manual"}
    assert executor.resolver.health.snapshot("slidex").consecutive_failures == 1
    assert executor.resolver.health.snapshot("slidex-manual").state == "closed"


def test_executor_failover_on_provider_exception():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(), outcome="raise")),
        ("slidex-manual", ManualProvider(make_manifest(), outcome="success")),
    )

    result = asyncio.run(executor.execute(make_request(), make_context()))

    assert result.success is True
    assert result.data == {"who": "slidex-manual"}


def test_open_breaker_routes_to_secondary_without_touching_primary():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(), outcome="failure", retryable=False)),
        ("slidex-manual", ManualProvider(make_manifest(), outcome="success")),
    )
    primary = executor.resolver.registry.candidates("visual.challenge")[0].provider

    # Exhaust the primary breaker (threshold=2).
    asyncio.run(executor.execute(make_request(), make_context()))
    asyncio.run(executor.execute(make_request(), make_context()))
    assert primary.calls == 2

    result = asyncio.run(executor.execute(make_request(), make_context()))

    assert result.success is True
    assert result.data == {"who": "slidex-manual"}
    # The open breaker short-circuits the primary entirely.
    assert primary.calls == 2


def test_executor_raises_unavailable_when_every_breaker_is_open():
    executor = make_executor(
        ("slidex", AutoProvider(make_manifest(platforms=("web",)), outcome="failure", retryable=False)),
        ("slidex-manual", ManualProvider(make_manifest(platforms=("web",)), outcome="failure", retryable=False)),
    )

    # First two walks run every candidate (threshold=2) and return the last
    # failure; the third walk finds both breakers open and fails closed.
    first = asyncio.run(executor.execute(make_request(), make_context()))
    assert first.success is False
    assert first.provider == "slidex-manual"
    second = asyncio.run(executor.execute(make_request(), make_context()))
    assert second.success is False
    with pytest.raises(CapabilityProviderUnavailableError):
        asyncio.run(executor.execute(make_request(), make_context()))


def test_primary_recovery_after_cooldown_restores_priority_order():
    from tests.capabilities.test_health import FakeClock

    clock = FakeClock()
    book = ProviderHealthBook(
        HealthPolicy(failure_threshold=1, cooldown_seconds=10.0), clock=clock
    )
    registry = CapabilityRegistry()
    registry.register(
        AutoProvider(make_manifest(), outcome="failure", retryable=False), name="slidex"
    )
    registry.register(ManualProvider(make_manifest()), name="slidex-manual")
    executor = CapabilityExecutor(CapabilityResolver(registry, health=book))

    # Primary fails once -> breaker opens -> manual serves.
    result = asyncio.run(executor.execute(make_request(), make_context()))
    assert result.data == {"who": "slidex-manual"}

    clock.advance(10.0)
    primary = registry.candidates("visual.challenge")[0].provider
    primary.outcome = "success"
    result = asyncio.run(executor.execute(make_request(), make_context()))

    assert result.data == {"who": "slidex"}
    assert book.snapshot("slidex").state == "closed"


# --- review fixes 2026-11: walk abort paths must not brick the breaker -------


class CancelledProvider(StubProvider):
    result_name = "slidex"

    async def execute(self, request, context):
        self.calls += 1
        raise asyncio.CancelledError()


class ProtocolErrorProvider(StubProvider):
    result_name = "slidex"

    async def execute(self, request, context):
        self.calls += 1
        from automation_core.capabilities import CapabilityProtocolError

        raise CapabilityProtocolError("bad request shape")

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="cooperative")


class InvalidResultProvider(StubProvider):
    result_name = "slidex"

    async def execute(self, request, context):
        self.calls += 1
        return {"not": "a capability result"}


def make_half_open_executor(primary):
    """Primary breaker opened once, cooldown elapsed -> half_open grant."""
    from tests.capabilities.test_health import FakeClock

    clock = FakeClock()
    book = ProviderHealthBook(
        HealthPolicy(failure_threshold=1, cooldown_seconds=10.0), clock=clock
    )
    registry = CapabilityRegistry()
    registry.register(primary, name="slidex")
    registry.register(ManualProvider(make_manifest()), name="slidex-manual")
    executor = CapabilityExecutor(CapabilityResolver(registry, health=book))
    book.record_failure("slidex")
    clock.advance(10.0)
    return executor, book, clock


def test_walk_cancelled_during_half_open_does_not_brick_primary():
    executor, book, clock = make_half_open_executor(
        CancelledProvider(make_manifest())
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(executor.execute(make_request(), make_context()))

    # The grant was released, so the half-open state grants a fresh probe
    # immediately (no outcome was recorded, no cooldown restart).
    assert book.probe("slidex") is True


def test_walk_protocol_error_during_half_open_does_not_brick_primary():
    executor, book, clock = make_half_open_executor(
        ProtocolErrorProvider(make_manifest())
    )

    with pytest.raises(Exception, match="bad request shape"):
        asyncio.run(executor.execute(make_request(), make_context()))

    # Released grant: the half-open state hands out a fresh probe right away.
    assert book.probe("slidex") is True


def test_walk_invalid_result_during_half_open_does_not_brick_primary():
    executor, book, clock = make_half_open_executor(
        InvalidResultProvider(make_manifest())
    )

    with pytest.raises(Exception, match="CapabilityResult"):
        asyncio.run(executor.execute(make_request(), make_context()))

    clock.advance(10.0)
    assert book.probe("slidex") is True


def test_profile_validation_failure_does_not_consume_probe():
    """Contract validation runs before the probe: no grant to release."""
    from tests.capabilities.test_health import FakeClock

    class BadProfileProvider(StubProvider):
        result_name = "slidex"

        def execution_profile(self, request):
            return "not a profile"

    clock = FakeClock()
    book = ProviderHealthBook(
        HealthPolicy(failure_threshold=1, cooldown_seconds=10.0), clock=clock
    )
    registry = CapabilityRegistry()
    registry.register(BadProfileProvider(make_manifest()), name="slidex")
    executor = CapabilityExecutor(CapabilityResolver(registry, health=book))
    book.record_failure("slidex")
    clock.advance(10.0)

    with pytest.raises(Exception, match="execution_profile"):
        asyncio.run(executor.execute(make_request(), make_context()))

    # The breaker never left "open" (probe was not reached); once the cooldown
    # elapses the provider is probeable again — nothing was latched.
    assert book.snapshot("slidex").state == "open"
    clock.advance(10.0)
    assert book.probe("slidex") is True


def test_peek_does_not_consume_health_probe():
    from tests.capabilities.test_health import FakeClock

    clock = FakeClock()
    book = ProviderHealthBook(
        HealthPolicy(failure_threshold=1, cooldown_seconds=10.0), clock=clock
    )
    registry = CapabilityRegistry()
    registry.register(AutoProvider(make_manifest()), name="slidex")
    resolver = CapabilityResolver(registry, health=book)
    book.record_failure("slidex")
    clock.advance(10.0)

    # Advisory peek works while half-open and must not consume the single
    # probe grant the actual execution relies on.
    assert isinstance(resolver.peek(make_request()), AutoProvider)
    assert resolver.probe("slidex") is True
