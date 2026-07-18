import asyncio

import pytest

from automation_core.capabilities import (
    CapabilityExecutionModeError,
    CapabilityExecutor,
    CapabilityManifest,
    CapabilityProtocolError,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResult,
)


def _request():
    return CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters={"value": "input"},
        metadata={"task_id": "task-1"},
    )


class SyncProvider:
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
    )

    def execute(self, request):
        return CapabilityResult(
            success=True,
            provider="sync-provider",
            data={"value": request.parameters["value"]},
        )


class AsyncProvider:
    manifest = SyncProvider.manifest

    async def aexecute(self, request):
        return CapabilityResult(
            success=True,
            provider="async-provider",
            data={"value": request.parameters["value"]},
        )


def _executor(provider):
    registry = CapabilityRegistry()
    registry.register(provider)
    return CapabilityExecutor(registry)


def test_sync_executor_calls_sync_provider():
    result = _executor(SyncProvider()).execute(_request())

    assert result.success is True
    assert result.provider == "sync-provider"
    assert result.data == {"value": "input"}


def test_sync_executor_rejects_async_only_provider():
    with pytest.raises(CapabilityExecutionModeError, match="async"):
        _executor(AsyncProvider()).execute(_request())


def test_async_executor_calls_async_provider():
    async_result = asyncio.run(_executor(AsyncProvider()).aexecute(_request()))

    assert async_result.provider == "async-provider"


def test_async_executor_rejects_sync_only_provider():
    with pytest.raises(CapabilityExecutionModeError, match="sync-only"):
        asyncio.run(_executor(SyncProvider()).aexecute(_request()))


def test_executor_normalizes_provider_exception_to_failed_result():
    class BrokenProvider(SyncProvider):
        def execute(self, request):
            raise RuntimeError("engine unavailable token=secret")

    result = _executor(BrokenProvider()).execute(_request())

    assert result.success is False
    assert result.provider == "visual.challenge"
    assert result.error_code == "provider_exception"
    assert result.retryable is False
    assert result.metadata["error_type"] == "RuntimeError"
    assert result.metadata["message"] == "provider execution failed"
    assert "secret" not in str(result.to_dict())


def test_executor_propagates_protocol_errors_from_both_entrypoints():
    class InvalidSyncProvider(SyncProvider):
        def execute(self, request):
            raise CapabilityProtocolError("invalid provider state")

    class InvalidAsyncProvider(AsyncProvider):
        async def aexecute(self, request):
            raise CapabilityProtocolError("invalid provider state")

    with pytest.raises(CapabilityProtocolError, match="invalid provider state"):
        _executor(InvalidSyncProvider()).execute(_request())

    with pytest.raises(CapabilityProtocolError, match="invalid provider state"):
        asyncio.run(_executor(InvalidAsyncProvider()).aexecute(_request()))


def test_executor_rejects_non_result_provider_output():
    class InvalidProvider(SyncProvider):
        def execute(self, request):
            return {"success": True}

    with pytest.raises(CapabilityProtocolError, match="CapabilityResult"):
        _executor(InvalidProvider()).execute(_request())
