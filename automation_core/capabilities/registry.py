from dataclasses import dataclass
from typing import Dict, List, Optional

from automation_core.capabilities.errors import (
    CapabilityNotFoundError,
    CapabilityRegistrationError,
)
from automation_core.capabilities.models import CapabilityManifest


@dataclass(frozen=True)
class _Registration:
    """One registered provider under a capability.

    ``name`` is the registration key (defaults to the capability name so a
    single unnamed registration keeps the pre-governance semantics); it is
    also the health-ledger key. ``order`` preserves insertion order among
    equal-priority candidates.
    """

    name: str
    provider: object
    manifest: CapabilityManifest
    order: int


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: Dict[str, List[_Registration]] = {}
        self._order = 0

    def register(
        self,
        provider: object,
        *,
        name: Optional[str] = None,
        replace: bool = False,
    ) -> None:
        """Register a capability provider.

        ``name`` is the registration key; it defaults to the capability name
        and doubles as the health-ledger key. Multiple providers may register
        under the same capability with distinct names (the multi-provider
        gate opens with a real second provider — development.md §11.3); the
        same name may only be reused with ``replace=True``.
        """
        manifest = getattr(provider, "manifest", None)
        if not isinstance(manifest, CapabilityManifest):
            raise CapabilityRegistrationError(
                "provider manifest must be a CapabilityManifest"
            )
        execute = getattr(provider, "execute", None)
        profile = getattr(provider, "execution_profile", None)
        if not callable(execute):
            raise CapabilityRegistrationError(
                "provider must define async execute"
            )
        if not callable(profile):
            raise CapabilityRegistrationError(
                "provider must define execution_profile"
            )
        key = name if name is not None else manifest.name
        if not isinstance(key, str) or not key.strip():
            raise CapabilityRegistrationError(
                "provider registration name must be a non-blank string"
            )
        entries = self._capabilities.setdefault(manifest.name, [])
        existing = next((entry for entry in entries if entry.name == key), None)
        if existing is not None and not replace:
            raise CapabilityRegistrationError(
                f"provider already registered for capability "
                f"{manifest.name}: {key}"
            )
        if existing is not None:
            entries.remove(existing)
        self._order += 1
        entries.append(
            _Registration(
                name=key,
                provider=provider,
                manifest=manifest,
                order=self._order,
            )
        )
        # Resolution order: manifest priority descending, then insertion.
        entries.sort(key=lambda entry: (-entry.manifest.priority, entry.order))

    def get(self, name: str) -> object:
        """Highest-priority provider registered under ``name``."""
        return self.candidates(name)[0].provider

    def candidates(self, name: str) -> List[_Registration]:
        """All registrations for a capability, resolution order."""
        entries = self._capabilities.get(name)
        if not entries:
            raise CapabilityNotFoundError(
                f"capability is not registered: {name}"
            )
        return list(entries)

    def list_manifests(self) -> List[CapabilityManifest]:
        manifests: List[_Registration] = []
        for capability in sorted(self._capabilities):
            manifests.extend(self._capabilities[capability])
        return [entry.manifest for entry in manifests]

    def find(
        self,
        *,
        operation: str,
        platform: Optional[str] = None,
    ) -> List[CapabilityManifest]:
        return [
            manifest
            for manifest in self.list_manifests()
            if manifest.supports(operation, platform=platform)
        ]
