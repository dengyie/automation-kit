import pytest

from automation_core.capabilities import (
    CapabilityManifest,
    CapabilityNotFoundError,
    CapabilityOperationNotSupportedError,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
)
from automation_core.execution import ExecutionContext


class FakeProvider:
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        platforms=("web", "android"),
        default_cancellation="cooperative",
    )

    def execution_profile(self, request):
        from automation_core.capabilities import CapabilityExecutionProfile

        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        return CapabilityResult(success=True, provider="fake")


def test_resolver_selects_single_provider_deterministically():
    registry = CapabilityRegistry()
    provider = FakeProvider()
    registry.register(provider)
    resolver = CapabilityResolver(registry)

    selected = resolver.resolve(
        CapabilityRequest(capability="visual.challenge", operation="solve"),
        platform="web",
    )

    assert selected is provider


def test_resolver_distinguishes_missing_capability_and_unsupported_operation():
    registry = CapabilityRegistry()
    registry.register(FakeProvider())
    resolver = CapabilityResolver(registry)

    with pytest.raises(CapabilityNotFoundError, match="document.extract"):
        resolver.resolve(
            CapabilityRequest(capability="document.extract", operation="extract")
        )

    with pytest.raises(CapabilityOperationNotSupportedError, match="inspect"):
        resolver.resolve(
            CapabilityRequest(capability="visual.challenge", operation="inspect")
        )
