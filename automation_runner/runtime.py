import asyncio
import time
from typing import Callable, List, Optional, Sequence, Union
from uuid import uuid4

from automation_core.capabilities import CapabilityExecutor, CapabilityResult
from automation_core.drivers import ActionResult, DriverSession
from automation_core.execution import (
    ExecutionContext,
    ExecutionFailure,
    FailureCategory,
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowResult,
    WorkflowStatus,
)
from automation_runner.policies import CapabilityPolicy
from automation_runner.steps import WorkflowStep


class WorkflowRuntime:
    def __init__(
        self,
        *,
        session_factory: Callable[[], DriverSession],
        capability_executor: Optional[CapabilityExecutor] = None,
        workflow_name: str = "workflow",
        run_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        deadline: Optional[float] = None,
    ) -> None:
        self.session_factory = session_factory
        self.capability_executor = capability_executor
        self.workflow_name = workflow_name
        self.run_id = run_id
        self.correlation_id = correlation_id
        self.deadline = deadline

    def run(self, steps: Sequence[WorkflowStep]) -> WorkflowResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(steps))
        raise RuntimeError("WorkflowRuntime.run cannot be used inside a running event loop")

    async def arun(self, steps: Sequence[WorkflowStep]) -> WorkflowResult:
        context = ExecutionContext(
            run_id=self.run_id or uuid4().hex,
            task_id=None,
            workflow_name=self.workflow_name,
            correlation_id=self.correlation_id or uuid4().hex,
            deadline=self.deadline,
        )
        session = self.session_factory()
        step_results: List[StepExecutionResult] = []
        failure: Optional[ExecutionFailure] = None
        try:
            session.start()
            for index, step in enumerate(steps, start=1):
                step_context = context.for_step(f"step-{index}")
                if step.kind == "action":
                    result = await self._run_action(session, step, step_context)
                elif step.kind == "capability":
                    result = await self._run_capability(step, step_context)
                else:
                    result = StepExecutionResult(
                        step_id=step_context.task_id or f"step-{index}",
                        step_name=step.name,
                        kind=StepKind.ACTION,
                        status=StepStatus.FAILED,
                        attempts=1,
                        duration_ms=0,
                        context=step_context,
                        action_result=ActionResult(
                            success=False,
                            message=f"unsupported workflow step kind: {step.kind}",
                        ),
                        error=ExecutionFailure(
                            category=FailureCategory.CONFIG,
                            code="unsupported_step_kind",
                            message=f"unsupported workflow step kind: {step.kind}",
                            retryable=False,
                            source="runtime",
                        ),
                    )
                step_results.append(result)
                if result.status is not StepStatus.SUCCEEDED:
                    failure = result.error or ExecutionFailure(
                        category=FailureCategory.BUSINESS,
                        code="step_failed",
                        message=f"step failed: {step.name}",
                        retryable=False,
                        source="runtime",
                    )
                    break
        finally:
            stop = getattr(session, "stop", None)
            if callable(stop):
                stop()

        status = WorkflowStatus.SUCCEEDED if failure is None else WorkflowStatus.FAILED
        return WorkflowResult(
            context=context,
            status=status,
            steps=tuple(step_results),
            failure=failure,
        )

    async def _run_action(
        self,
        session: DriverSession,
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepExecutionResult:
        started = time.monotonic()
        action_result = session.execute_action(step.name, **dict(step.parameters))
        duration_ms = int((time.monotonic() - started) * 1000)
        status = StepStatus.SUCCEEDED if action_result.success else StepStatus.FAILED
        error = None
        if not action_result.success:
            error = ExecutionFailure(
                category=FailureCategory.BUSINESS,
                code="action_failed",
                message=action_result.message or f"action failed: {step.name}",
                retryable=False,
                source="action",
            )
        return StepExecutionResult(
            step_id=context.task_id or step.name,
            step_name=step.name,
            kind=StepKind.ACTION,
            status=status,
            attempts=1,
            duration_ms=duration_ms,
            context=context,
            action_result=action_result,
            error=error,
        )

    async def _run_capability(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepExecutionResult:
        if self.capability_executor is None:
            failure = ExecutionFailure(
                category=FailureCategory.CONFIG,
                code="capability_executor_missing",
                message="capability executor is not configured",
                retryable=False,
                source="runtime",
            )
            return StepExecutionResult(
                step_id=context.task_id or step.name,
                step_name=step.name,
                kind=StepKind.CAPABILITY,
                status=StepStatus.FAILED,
                attempts=0,
                duration_ms=0,
                context=context,
                capability_result=CapabilityResult(
                    success=False,
                    provider="runtime",
                    error_code=failure.code,
                ),
                error=failure,
            )

        policy = step.policy or CapabilityPolicy()
        attempts = 0
        started = time.monotonic()
        last_result: Optional[CapabilityResult] = None
        last_error: Optional[ExecutionFailure] = None

        while attempts < policy.max_attempts:
            attempts += 1
            timeout = self._effective_timeout(policy, context)
            try:
                if timeout is None:
                    last_result = await self.capability_executor.execute(
                        step.request,
                        context,
                    )
                else:
                    last_result = await asyncio.wait_for(
                        self.capability_executor.execute(step.request, context),
                        timeout=timeout,
                    )
            except asyncio.TimeoutError:
                last_error = ExecutionFailure(
                    category=FailureCategory.TIMEOUT,
                    code="timeout",
                    message=f"capability timed out: {step.name}",
                    retryable=attempts < policy.max_attempts,
                    source="runtime",
                )
                last_result = CapabilityResult(
                    success=False,
                    provider="runtime",
                    error_code="timeout",
                    retryable=last_error.retryable,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = ExecutionFailure(
                    category=FailureCategory.PROVIDER,
                    code="provider_exception",
                    message="provider execution failed",
                    retryable=False,
                    source="runtime",
                    details={"error_type": type(exc).__name__},
                )
                last_result = CapabilityResult(
                    success=False,
                    provider="runtime",
                    error_code="provider_exception",
                )

            if last_result is not None and last_result.success:
                return StepExecutionResult(
                    step_id=context.task_id or step.name,
                    step_name=step.name,
                    kind=StepKind.CAPABILITY,
                    status=StepStatus.SUCCEEDED,
                    attempts=attempts,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    context=context,
                    capability_result=last_result,
                )

            retryable = bool(last_result and last_result.retryable)
            if last_error is not None:
                retryable = last_error.retryable
            if not retryable or attempts >= policy.max_attempts:
                break
            if policy.backoff:
                await asyncio.sleep(policy.backoff)

        if last_error is None:
            last_error = ExecutionFailure(
                category=FailureCategory.BUSINESS,
                code=(last_result.error_code if last_result else "capability_failed"),
                message=f"capability failed: {step.name}",
                retryable=False,
                source="runtime",
            )
        return StepExecutionResult(
            step_id=context.task_id or step.name,
            step_name=step.name,
            kind=StepKind.CAPABILITY,
            status=StepStatus.FAILED,
            attempts=attempts,
            duration_ms=int((time.monotonic() - started) * 1000),
            context=context,
            capability_result=last_result
            or CapabilityResult(
                success=False,
                provider="runtime",
                error_code=last_error.code,
            ),
            error=last_error,
        )

    @staticmethod
    def _effective_timeout(
        policy: CapabilityPolicy,
        context: ExecutionContext,
    ) -> Optional[float]:
        timeout = policy.timeout
        if context.deadline is None:
            return timeout
        remaining = context.deadline - time.time()
        if remaining <= 0:
            return 0.0
        if timeout is None:
            return remaining
        return min(timeout, remaining)
