import asyncio
import inspect
from typing import Optional

from automation_core.capabilities.errors import CapabilityProtocolError
from automation_core.capabilities.models import (
    CapabilityExecutionProfile,
    CapabilityRequest,
    CapabilityResult,
)
from automation_core.capabilities.resolver import CapabilityResolver
from automation_core.execution import ExecutionContext


class CapabilityExecutor:
    def __init__(self, resolver: CapabilityResolver) -> None:
        self.resolver = resolver

    def execution_profile(
        self,
        request: CapabilityRequest,
        *,
        platform: Optional[str] = None,
    ) -> CapabilityExecutionProfile:
        """Resolve the provider for ``request`` and return its execution profile.

        Resolver and protocol errors propagate unchanged so callers can
        distinguish platform wiring mistakes from provider runtime failures.
        """
        provider = self.resolver.resolve(request, platform=platform)
        return self._profile(provider, request)

    async def execute(
        self,
        request: CapabilityRequest,
        context: ExecutionContext,
        *,
        platform: Optional[str] = None,
    ) -> CapabilityResult:
        provider = self.resolver.resolve(request, platform=platform)
        self._profile(provider, request)
        execute = getattr(provider, "execute", None)
        if not callable(execute):
            raise CapabilityProtocolError("provider must define async execute")
        try:
            result = execute(request, context)
            if inspect.isawaitable(result):
                result = await result
        except CapabilityProtocolError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return self._provider_failure(provider, exc)
        return self._validate_result(result)

    @staticmethod
    def _profile(
        provider: object,
        request: CapabilityRequest,
    ) -> CapabilityExecutionProfile:
        profile_fn = getattr(provider, "execution_profile", None)
        if not callable(profile_fn):
            raise CapabilityProtocolError("provider must define execution_profile")
        profile = profile_fn(request)
        if not isinstance(profile, CapabilityExecutionProfile):
            raise CapabilityProtocolError(
                "execution_profile must return CapabilityExecutionProfile"
            )
        return profile

    @staticmethod
    def _validate_result(result: object) -> CapabilityResult:
        if not isinstance(result, CapabilityResult):
            raise CapabilityProtocolError(
                "provider must return CapabilityResult"
            )
        return result

    @staticmethod
    def _provider_failure(provider: object, exc: Exception) -> CapabilityResult:
        return CapabilityResult(
            success=False,
            provider=provider.manifest.name,
            error_code="provider_exception",
            retryable=False,
            metadata={
                "error_type": type(exc).__name__,
                "message": "provider execution failed",
            },
        )
