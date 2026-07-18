import pytest

from automation_core.capabilities import (
    CapabilityManifest,
    CapabilityNotFoundError,
    CapabilityOperationNotSupportedError,
    CapabilityRegistrationError,
    CapabilityRegistry,
    CapabilityResult,
)


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


def test_registry_registers_and_lists_provider_deterministically():
    registry = CapabilityRegistry()

    registry.register(FakeProvider())

    assert registry.get("visual.challenge").manifest.version == "1.0.0"
    assert registry.list_manifests() == [FakeProvider.manifest]
    assert registry.find(operation="solve", platform="web") == [FakeProvider.manifest]


def test_registry_rejects_duplicate_without_explicit_replace():
    registry = CapabilityRegistry()
    registry.register(FakeProvider())

    with pytest.raises(CapabilityRegistrationError, match="already registered"):
        registry.register(FakeProvider())

    replacement = FakeProvider()
    registry.register(replacement, replace=True)

    assert registry.get("visual.challenge") is replacement


def test_registry_rejects_provider_without_execution_entrypoint():
    class InvalidProvider:
        manifest = FakeProvider.manifest

    with pytest.raises(CapabilityRegistrationError, match="execute"):
        CapabilityRegistry().register(InvalidProvider())


def test_registry_get_distinguishes_missing_capability():
    registry = CapabilityRegistry()
    registry.register(FakeProvider())

    with pytest.raises(CapabilityNotFoundError, match="document.extract"):
        registry.get("document.extract")
