import inspect

from automation_core.capabilities.errors import (
    CapabilityExecutionModeError,
    CapabilityProtocolError,
)
from automation_core.capabilities.models import CapabilityRequest, CapabilityResult
from automation_core.capabilities.registry import CapabilityRegistry


class CapabilityExecutor:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        provider = self.registry.resolve(request.capability, request.operation)
        execute = getattr(provider, "execute", None)
        if not callable(execute):
            raise CapabilityExecutionModeError(
                f"capability {request.capability} is async-only; use aexecute"
            )
        try:
            result = execute(request)
        except CapabilityProtocolError:
            raise
        except Exception as exc:
            return self._provider_failure(provider, exc)
        if inspect.isawaitable(result):
            close = getattr(result, "close", None)
            if callable(close):
                close()
            raise CapabilityExecutionModeError(
                f"capability {request.capability} returned async work; use aexecute"
            )
        return self._validate_result(result)

    async def aexecute(self, request: CapabilityRequest) -> CapabilityResult:
        provider = self.registry.resolve(request.capability, request.operation)
        aexecute = getattr(provider, "aexecute", None)
        execute = getattr(provider, "execute", None)
        try:
            if callable(aexecute):
                result = aexecute(request)
            elif callable(execute):
                raise CapabilityExecutionModeError(
                    f"capability {request.capability} is sync-only; use execute"
                )
            else:
                raise CapabilityProtocolError(
                    "provider must define execute or aexecute"
                )
            if inspect.isawaitable(result):
                result = await result
        except (CapabilityExecutionModeError, CapabilityProtocolError):
            raise
        except Exception as exc:
            return self._provider_failure(provider, exc)
        return self._validate_result(result)

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
