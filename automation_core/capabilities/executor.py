import asyncio
import inspect
from typing import Optional

from automation_core.capabilities.errors import (
    CapabilityProtocolError,
    CapabilityProviderUnavailableError,
)
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
        Advisory: resolution here never consumes a health probe.
        """
        provider = self.resolver.peek(request, platform=platform)
        return self._profile(provider, request)

    async def execute(
        self,
        request: CapabilityRequest,
        context: ExecutionContext,
        *,
        platform: Optional[str] = None,
    ) -> CapabilityResult:
        """Walk candidates in resolution order until one succeeds.

        Failover semantics (development.md §11.3): each candidate must pass a
        health probe before executing; a business failure or provider crash
        records a failure and the walk continues to the next candidate. The
        first success wins; when every candidate fails the last failure
        result is returned, and when every breaker is open the walk raises
        ``CapabilityProviderUnavailableError``. A provider crash is a health
        signal, and so is a business failure — a solver that cannot solve
        should fail over.

        Probe invariant: a granted probe is either resolved through
        ``record_success`` / ``record_failure`` or explicitly released before
        re-raising — otherwise the half-open grant latches and the provider
        is bricked for the process lifetime. Candidate contract validation
        (execution profile, async execute entrypoint) therefore runs *before*
        the probe, so wiring errors never consume a grant.
        """
        candidates = self.resolver.supported_candidates(
            request, platform=platform
        )
        last_result: Optional[CapabilityResult] = None
        for name, provider in candidates:
            # Validate the candidate contract first: failures here are
            # wiring/config errors that must propagate without consuming a
            # health probe.
            self._profile(provider, request)
            execute = getattr(provider, "execute", None)
            if not callable(execute):
                raise CapabilityProtocolError("provider must define async execute")
            if not self.resolver.probe(name):
                continue
            try:
                result = execute(request, context)
                if inspect.isawaitable(result):
                    result = await result
            except CapabilityProtocolError:
                # A provider-side contract violation is not a wiring error;
                # the probe was granted for a real execution attempt, so
                # release it before propagating to keep the ledger consistent.
                self.resolver.health.release(name)
                raise
            except asyncio.CancelledError:
                self.resolver.health.release(name)
                raise
            except Exception as exc:
                self.resolver.record_failure(name)
                last_result = self._provider_failure(provider, exc)
                continue
            try:
                result = self._validate_result(result)
            except CapabilityProtocolError:
                self.resolver.health.release(name)
                raise
            if result.success:
                self.resolver.record_success(name)
                return result
            self.resolver.record_failure(name)
            last_result = result
        if last_result is not None:
            return last_result
        names = ", ".join(name for name, _ in candidates)
        raise CapabilityProviderUnavailableError(
            f"capability {request.capability} has no healthy provider: {names}"
        )

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
