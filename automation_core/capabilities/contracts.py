from typing import Protocol, runtime_checkable

from automation_core.capabilities.models import (
    CapabilityExecutionProfile,
    CapabilityManifest,
    CapabilityRequest,
    CapabilityResult,
)
from automation_core.execution import ExecutionContext


@runtime_checkable
class CapabilityProvider(Protocol):
    manifest: CapabilityManifest

    def execution_profile(
        self,
        request: CapabilityRequest,
    ) -> CapabilityExecutionProfile:
        ...

    async def execute(
        self,
        request: CapabilityRequest,
        context: ExecutionContext,
    ) -> CapabilityResult:
        ...
