import asyncio
import time
from typing import Callable, List, Optional, Sequence
from uuid import uuid4

from automation_core.capabilities import CapabilityExecutor, CapabilityResult
from automation_core.drivers import ActionResult, ArtifactHandle, DriverSession
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
from automation_runner.collector import ReportCollector
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
        collector = ReportCollector(context)
        collector.record_event(
            {
                "event_id": f"{context.run_id}:workflow.start",
                "event_type": "workflow.start",
                "task_id": None,
                "payload": {"workflow_name": context.workflow_name},
            }
        )

        session: Optional[DriverSession] = None
        failure: Optional[ExecutionFailure] = None
        status = WorkflowStatus.SUCCEEDED
        try:
            try:
                session = self.session_factory()
                session.start()
            except Exception as exc:
                failure = ExecutionFailure(
                    category=FailureCategory.CONFIG,
                    code="session_start_failed",
                    message="session start failed",
                    retryable=False,
                    source="runtime",
                    details={"error_type": type(exc).__name__},
                )
                status = WorkflowStatus.FAILED
            else:
                for index, step in enumerate(steps, start=1):
                    step_context = context.for_step(f"step-{index}")
                    collector.record_event(
                        {
                            "event_id": f"{context.run_id}:{step_context.task_id}:start",
                            "event_type": "step.start",
                            "task_id": step_context.task_id,
                            "payload": {"step_name": step.name, "kind": step.kind},
                        }
                    )
                    try:
                        if step.kind == "action":
                            result = await self._run_action(session, step, step_context)
                        elif step.kind == "capability":
                            result = await self._run_capability(step, step_context)
                        elif step.kind == "artifact":
                            result = await self._run_artifact(session, step, step_context)
                        else:
                            result = self._unsupported_step(step, step_context)
                    except asyncio.CancelledError:
                        failure = ExecutionFailure(
                            category=FailureCategory.CANCELLED,
                            code="cancelled",
                            message="workflow cancelled",
                            retryable=False,
                            source="runtime",
                        )
                        status = WorkflowStatus.CANCELLED
                        cancelled_step = self._cancelled_step(step, step_context)
                        collector.record_step(cancelled_step)
                        collector.record_event(
                            {
                                "event_id": f"{context.run_id}:{step_context.task_id}:end",
                                "event_type": "step.end",
                                "task_id": step_context.task_id,
                                "payload": {
                                    "step_name": step.name,
                                    "status": StepStatus.CANCELLED.value,
                                },
                            }
                        )
                        break

                    collector.record_step(result)
                    if result.artifact_result is not None:
                        collector.attach_artifact(result.artifact_result)
                    if result.capability_result is not None:
                        for artifact in result.capability_result.artifacts:
                            collector.attach_artifact(artifact)
                    collector.record_event(
                        {
                            "event_id": f"{context.run_id}:{step_context.task_id}:end",
                            "event_type": "step.end",
                            "task_id": step_context.task_id,
                            "payload": {
                                "step_name": step.name,
                                "status": result.status.value,
                            },
                        }
                    )
                    if result.status is not StepStatus.SUCCEEDED:
                        failure = result.error or ExecutionFailure(
                            category=FailureCategory.BUSINESS,
                            code="step_failed",
                            message=f"step failed: {step.name}",
                            retryable=False,
                            source="runtime",
                        )
                        status = (
                            WorkflowStatus.CANCELLED
                            if result.status is StepStatus.CANCELLED
                            else WorkflowStatus.FAILED
                        )
                        break
        except asyncio.CancelledError:
            failure = ExecutionFailure(
                category=FailureCategory.CANCELLED,
                code="cancelled",
                message="workflow cancelled",
                retryable=False,
                source="runtime",
            )
            status = WorkflowStatus.CANCELLED
        finally:
            cleanup_error = self._close_session(session)
            if cleanup_error is not None:
                if failure is None:
                    failure = cleanup_error
                    status = WorkflowStatus.FAILED
                else:
                    details = dict(failure.details)
                    details["cleanup_error_type"] = cleanup_error.details.get("error_type")
                    details["cleanup_code"] = cleanup_error.code
                    failure = ExecutionFailure(
                        category=failure.category,
                        code=failure.code,
                        message=failure.message,
                        retryable=failure.retryable,
                        source=failure.source,
                        details=details,
                    )

        collector.record_event(
            {
                "event_id": f"{context.run_id}:workflow.end",
                "event_type": "workflow.end",
                "task_id": None,
                "payload": {
                    "status": status.value,
                    "failure_code": failure.code if failure is not None else None,
                },
            }
        )
        report = collector.finalize(status=status, failure=failure)
        return WorkflowResult(
            context=context,
            status=status,
            steps=tuple(collector._steps),
            artifacts=tuple(collector._artifacts),
            events=tuple(report["events"]),
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

    async def _run_artifact(
        self,
        session: DriverSession,
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepExecutionResult:
        started = time.monotonic()
        artifact_name = str(step.parameters.get("name") or step.name)
        try:
            artifact = session.capture_artifact(step.name, artifact_name)
        except Exception as exc:
            return StepExecutionResult(
                step_id=context.task_id or step.name,
                step_name=step.name,
                kind=StepKind.ARTIFACT,
                status=StepStatus.FAILED,
                attempts=1,
                duration_ms=int((time.monotonic() - started) * 1000),
                context=context,
                artifact_result=ArtifactHandle(
                    artifact_type=step.name,
                    path=artifact_name,
                    metadata={"error": "capture_failed"},
                ),
                error=ExecutionFailure(
                    category=FailureCategory.PROVIDER,
                    code="artifact_capture_failed",
                    message=f"artifact capture failed: {step.name}",
                    retryable=False,
                    source="runtime",
                    details={"error_type": type(exc).__name__},
                ),
            )
        return StepExecutionResult(
            step_id=context.task_id or step.name,
            step_name=step.name,
            kind=StepKind.ARTIFACT,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=int((time.monotonic() - started) * 1000),
            context=context,
            artifact_result=artifact,
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
    def _unsupported_step(
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepExecutionResult:
        return StepExecutionResult(
            step_id=context.task_id or step.name,
            step_name=step.name,
            kind=StepKind.ACTION,
            status=StepStatus.FAILED,
            attempts=1,
            duration_ms=0,
            context=context,
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

    @staticmethod
    def _cancelled_step(
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepExecutionResult:
        if step.kind == "capability":
            return StepExecutionResult(
                step_id=context.task_id or step.name,
                step_name=step.name,
                kind=StepKind.CAPABILITY,
                status=StepStatus.CANCELLED,
                attempts=1,
                duration_ms=0,
                context=context,
                capability_result=CapabilityResult(
                    success=False,
                    provider="runtime",
                    error_code="cancelled",
                ),
                error=ExecutionFailure(
                    category=FailureCategory.CANCELLED,
                    code="cancelled",
                    message="step cancelled",
                    retryable=False,
                    source="runtime",
                ),
            )
        if step.kind == "artifact":
            return StepExecutionResult(
                step_id=context.task_id or step.name,
                step_name=step.name,
                kind=StepKind.ARTIFACT,
                status=StepStatus.CANCELLED,
                attempts=1,
                duration_ms=0,
                context=context,
                artifact_result=ArtifactHandle(
                    artifact_type=step.name,
                    path=str(step.parameters.get("name") or step.name),
                ),
                error=ExecutionFailure(
                    category=FailureCategory.CANCELLED,
                    code="cancelled",
                    message="step cancelled",
                    retryable=False,
                    source="runtime",
                ),
            )
        return StepExecutionResult(
            step_id=context.task_id or step.name,
            step_name=step.name,
            kind=StepKind.ACTION,
            status=StepStatus.CANCELLED,
            attempts=1,
            duration_ms=0,
            context=context,
            action_result=ActionResult(success=False, message="cancelled"),
            error=ExecutionFailure(
                category=FailureCategory.CANCELLED,
                code="cancelled",
                message="step cancelled",
                retryable=False,
                source="runtime",
            ),
        )

    @staticmethod
    def _close_session(session: Optional[DriverSession]) -> Optional[ExecutionFailure]:
        if session is None:
            return None
        stop = getattr(session, "stop", None)
        if not callable(stop):
            return None
        try:
            stop()
        except Exception as exc:
            return ExecutionFailure(
                category=FailureCategory.CLEANUP,
                code="session_stop_failed",
                message="session stop failed",
                retryable=False,
                source="runtime",
                details={"error_type": type(exc).__name__},
            )
        return None

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
