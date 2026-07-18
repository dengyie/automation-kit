from typing import Protocol, runtime_checkable

from automation_core.capabilities.models import (
    CapabilityManifest,
    CapabilityRequest,
    CapabilityResult,
)


@runtime_checkable
class CapabilityProvider(Protocol):
    manifest: CapabilityManifest

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        ...


@runtime_checkable
class AsyncCapabilityProvider(Protocol):
    manifest: CapabilityManifest

    async def aexecute(self, request: CapabilityRequest) -> CapabilityResult:
        ...
