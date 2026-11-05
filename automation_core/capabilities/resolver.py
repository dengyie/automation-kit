from typing import Optional, Tuple

from automation_core.capabilities.errors import (
    CapabilityNotFoundError,
    CapabilityOperationNotSupportedError,
    CapabilityProviderUnavailableError,
)
from automation_core.capabilities.health import HealthPolicy, ProviderHealthBook
from automation_core.capabilities.models import CapabilityRequest
from automation_core.capabilities.registry import CapabilityRegistry


class CapabilityResolver:
    """Picks the executing provider for a capability request.

    Candidates come from the registry in resolution order (manifest priority
    descending, then insertion). Health gating opens only with a real second
    same-capability provider (development.md §11.3); with the default health
    book every candidate is probeable, so single-provider behaviour is
    unchanged. Selection is fail-closed: when every candidate's breaker is
    open the resolution fails with ``CapabilityProviderUnavailableError``
    instead of routing to a known-unhealthy provider.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        health: Optional[ProviderHealthBook] = None,
        health_policy: Optional[HealthPolicy] = None,
    ) -> None:
        self.registry = registry
        self.health = health or ProviderHealthBook(health_policy)

    def resolve(
        self,
        request: CapabilityRequest,
        platform: Optional[str] = None,
    ) -> object:
        return self.resolve_candidate(request, platform=platform)[1]

    def peek(
        self,
        request: CapabilityRequest,
        platform: Optional[str] = None,
    ) -> object:
        """Highest-priority supported provider without touching health.

        Advisory resolution for ``execution_profile``: the runtime asks for
        cancellation semantics before executing, and that call must not
        consume the single half-open probe the actual execution relies on.
        """
        return self._select(request, platform=platform)[0][1]

    def resolve_candidate(
        self,
        request: CapabilityRequest,
        platform: Optional[str] = None,
    ) -> Tuple[str, object]:
        """Return ``(registration_name, provider)`` for the first probeable candidate.

        Raises the same error classes as the single-provider resolver when no
        candidate supports the operation/platform, and
        ``CapabilityProviderUnavailableError`` when candidates exist but every
        breaker is open.
        """
        supported = self._select(request, platform=platform)
        for name, provider in supported:
            if self.health.probe(name):
                return name, provider
        names = ", ".join(name for name, _ in supported)
        raise CapabilityProviderUnavailableError(
            f"capability {request.capability} has no healthy provider: {names}"
        )

    def supported_candidates(
        self,
        request: CapabilityRequest,
        platform: Optional[str] = None,
    ) -> Tuple[Tuple[str, object], ...]:
        """All candidates supporting the request, in resolution order.

        No health probing happens here; callers gate each candidate through
        :meth:`probe` right before executing it so failures recorded between
        candidates re-open breakers deterministically mid-walk.
        """
        return self._select(request, platform=platform)

    def probe(self, name: str) -> bool:
        return self.health.probe(name)

    def _select(
        self,
        request: CapabilityRequest,
        platform: Optional[str] = None,
    ) -> Tuple[Tuple[str, object], ...]:
        candidates = self.registry.candidates(request.capability)
        operation_supported = [
            entry
            for entry in candidates
            if request.operation in entry.manifest.operations
        ]
        if not operation_supported:
            raise CapabilityOperationNotSupportedError(
                f"capability {request.capability} does not support operation: "
                f"{request.operation}"
            )
        platform_supported = [
            entry
            for entry in operation_supported
            if entry.manifest.supports(request.operation, platform=platform)
        ]
        if not platform_supported:
            raise CapabilityNotFoundError(
                f"capability {request.capability} does not support platform: {platform}"
            )
        return tuple(
            (entry.name, entry.provider) for entry in platform_supported
        )

    def record_success(self, name: str) -> None:
        self.health.record_success(name)

    def record_failure(self, name: str) -> None:
        self.health.record_failure(name)
