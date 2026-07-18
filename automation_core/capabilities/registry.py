from typing import Dict, List

from automation_core.capabilities.errors import (
    CapabilityNotFoundError,
    CapabilityOperationNotSupportedError,
    CapabilityRegistrationError,
)
from automation_core.capabilities.models import CapabilityManifest


class CapabilityRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, object] = {}

    def register(self, provider: object, *, replace: bool = False) -> None:
        manifest = getattr(provider, "manifest", None)
        if not isinstance(manifest, CapabilityManifest):
            raise CapabilityRegistrationError(
                "provider manifest must be a CapabilityManifest"
            )
        execute = getattr(provider, "execute", None)
        aexecute = getattr(provider, "aexecute", None)
        if not callable(execute) and not callable(aexecute):
            raise CapabilityRegistrationError(
                "provider must define execute or aexecute"
            )
        if manifest.name in self._providers and not replace:
            raise CapabilityRegistrationError(
                f"capability already registered: {manifest.name}"
            )
        self._providers[manifest.name] = provider

    def unregister(self, name: str) -> object:
        try:
            return self._providers.pop(name)
        except KeyError as exc:
            raise CapabilityNotFoundError(
                f"capability is not registered: {name}"
            ) from exc

    def get(self, name: str) -> object:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(
                f"capability is not registered: {name}"
            ) from exc

    def resolve(self, name: str, operation: str) -> object:
        provider = self.get(name)
        manifest = provider.manifest
        if not manifest.supports(operation):
            raise CapabilityOperationNotSupportedError(
                f"capability {name} does not support operation: {operation}"
            )
        return provider

    def list_manifests(self) -> List[CapabilityManifest]:
        return [
            self._providers[name].manifest
            for name in sorted(self._providers)
        ]

    def find(
        self,
        *,
        operation: str,
        platform: str = None,
    ) -> List[CapabilityManifest]:
        return [
            manifest
            for manifest in self.list_manifests()
            if manifest.supports(operation, platform=platform)
        ]
