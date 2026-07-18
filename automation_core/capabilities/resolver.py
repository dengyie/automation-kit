from typing import Optional

from automation_core.capabilities.errors import (
    CapabilityNotFoundError,
    CapabilityOperationNotSupportedError,
)
from automation_core.capabilities.models import CapabilityRequest
from automation_core.capabilities.registry import CapabilityRegistry


class CapabilityResolver:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def resolve(
        self,
        request: CapabilityRequest,
        platform: Optional[str] = None,
    ) -> object:
        provider = self.registry.get(request.capability)
        manifest = provider.manifest
        if request.operation not in manifest.operations:
            raise CapabilityOperationNotSupportedError(
                f"capability {request.capability} does not support operation: "
                f"{request.operation}"
            )
        if not manifest.supports(request.operation, platform=platform):
            raise CapabilityNotFoundError(
                f"capability {request.capability} does not support platform: {platform}"
            )
        return provider
