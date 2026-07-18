import asyncio

import pytest

from automation_core.capabilities import (
    CapabilityExecutionProfile,
    CapabilityExecutor,
    CapabilityManifest,
    CapabilityProtocolError,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
)
from automation_core.execution import ExecutionContext


def _request(**parameters):
    return CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters=dict(parameters),
    )


def _context():
    return ExecutionContext(run_id="run-1", task_id="step-1", workflow_name="smoke")


class AsyncProvider:
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        platforms=("web", "image"),
        default_cancellation="cooperative",
    )

    def __init__(self):
        self.calls = []

    def execution_profile(self, request):
        if request.parameters.get("context") == "image_bytes":
            return CapabilityExecutionProfile(
                cancellation="unsupported",
                blocking=True,
            )
        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        self.calls.append((request, context))
        return CapabilityResult(
            success=True,
            provider="async-provider",
            data={
                "run_id": context.run_id,
                "task_id": context.task_id,
            },
        )


def _executor(provider):
    registry = CapabilityRegistry()
    registry.register(provider)
    return CapabilityExecutor(CapabilityResolver(registry))


def test_provider_v2_executor_passes_context_and_reads_profile():
    provider = AsyncProvider()
    executor = _executor(provider)

    result = asyncio.run(executor.execute(_request(context="playwright_page"), _context()))

    assert result.success is True
    assert result.data == {"run_id": "run-1", "task_id": "step-1"}
    assert provider.execution_profile(_request(context="image_bytes")).cancellation == (
        "unsupported"
    )


def test_provider_v2_executor_normalizes_provider_exception_without_secrets():
    class BrokenProvider(AsyncProvider):
        async def execute(self, request, context):
            raise RuntimeError("engine unavailable token=secret")

    result = asyncio.run(_executor(BrokenProvider()).execute(_request(), _context()))

    assert result.success is False
    assert result.error_code == "provider_exception"
    assert result.metadata["error_type"] == "RuntimeError"
    assert "secret" not in str(result.to_dict())


def test_provider_v2_executor_preserves_cancellation():
    class CancelProvider(AsyncProvider):
        async def execute(self, request, context):
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_executor(CancelProvider()).execute(_request(), _context()))


def test_provider_v2_executor_rejects_non_result_and_missing_profile():
    class InvalidProvider(AsyncProvider):
        async def execute(self, request, context):
            return {"success": True}

    with pytest.raises(CapabilityProtocolError, match="CapabilityResult"):
        asyncio.run(_executor(InvalidProvider()).execute(_request(), _context()))

    class NoProfileProvider:
        manifest = AsyncProvider.manifest

        async def execute(self, request, context):
            return CapabilityResult(success=True, provider="x")

    with pytest.raises(Exception):
        CapabilityRegistry().register(NoProfileProvider())
