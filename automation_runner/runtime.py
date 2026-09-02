import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence
from uuid import uuid4

from automation_core.artifacts import ArtifactStore
from automation_core.capabilities import CapabilityExecutor, CapabilityResult
from automation_core.capabilities.errors import (
    CapabilityError,
    CapabilityNotFoundError,
    CapabilityOperationNotSupportedError,
    CapabilityRegistrationError,
)
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


class _RunClock:
    """Deadline arithmetic anchored once per workflow run.

    ``ExecutionContext.deadline`` stays a wall-clock epoch (public contract);
    elapsed time is measured on the monotonic clock so NTP adjustments during
    a run can neither extend nor shrink the effective budget.
    """

    def __init__(self) -> None:
        self.wall_start = time.time()
        self.mono_start = time.monotonic()

    def remaining(self, context: ExecutionContext) -> Optional[float]:
        if context.deadline is None:
            return None
        now_wall = self.wall_start + (time.monotonic() - self.mono_start)
        return context.deadline - now_wall


def _capability_error_category(exc: Exception) -> FailureCategory:
    if isinstance(exc, CapabilityRegistrationError):
        return FailureCategory.REGISTRATION
    if isinstance(exc, (CapabilityNotFoundError, CapabilityOperationNotSupportedError)):
        return FailureCategory.RESOLUTION
    return FailureCategory.CONFIG


def _cancelled_artifact_path(context: ExecutionContext, step: WorkflowStep) -> Path:
    """Deterministic never-written path for an artifact step cancelled mid-run.

    Goes through ``ArtifactStore`` so the fabricated handle cannot carry path
    separators or traversal segments into the report.
    """
    name = str(step.parameters.get("name") or step.name)
    return ArtifactStore(Path("artifacts")).build_path(
        context.run_id,
        step.name,
        name,
    )


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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.session_factory = session_factory
        self.capability_executor = capability_executor
        self.workflow_name = workflow_name
        self.run_id = run_id
        self.correlation_id = correlation_id
        self.deadline = deadline
        self.metadata = metadata

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
            metadata=dict(self.metadata or {}),
        )
        collector = ReportCollector(context)
        clock = _RunClock()
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
                    remaining = clock.remaining(context)
                    if remaining is not None and remaining <= 0:
                        failure = ExecutionFailure(
                            category=FailureCategory.TIMEOUT,
                            code="deadline_exceeded",
                            message=f"workflow deadline exceeded before step: {step.name}",
                            retryable=False,
                            source="runtime",
                        )
                        status = WorkflowStatus.FAILED
                        break

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
                        result = await self._execute_step(
                            session, step, step_context, collector
                        )
                    except asyncio.CancelledError:
                        failure = ExecutionFailure(
                            category=FailureCategory.CANCELLED,
                            code="cancelled",
                            message="workflow cancelled",
                            retryable=False,
                            source="runtime",
                        )
                        status = WorkflowStatus.CANCELLED
                        collector.record_step(self._cancelled_step(step, step_context))
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
                    except Exception as exc:
                        # Last-resort normalization: no exception may escape a
                        # workflow run without a step result and a report.
                        result = self._unhandled_step_failure(step, step_context, exc)

                    collector.record_step(result)
                    if result.status is not StepStatus.CANCELLED:
                        self._record_terminal_event(collector, context, step_context, result)
                    artifact_count = 0
                    if result.artifact_result is not None:
                        collector.attach_artifact(result.artifact_result)
                        artifact_count += 1
                        self._record_artifact_event(
                            collector,
                            context,
                            step_context,
                            result.artifact_result,
                            artifact_count,
                        )
                    if result.capability_result is not None:
                        for artifact in result.capability_result.artifacts:
                            collector.attach_artifact(artifact)
                            artifact_count += 1
                            self._record_artifact_event(
                                collector,
                                context,
                                step_context,
                                artifact,
                                artifact_count,
                            )
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
            steps=tuple(collector.steps()),
            artifacts=tuple(collector.artifacts()),
            events=tuple(report["events"]),
            failure=failure,
        )

    @staticmethod
    def _record_terminal_event(
        collector: ReportCollector,
        context: ExecutionContext,
        step_context: ExecutionContext,
        result: StepExecutionResult,
    ) -> None:
        if result.kind is StepKind.ARTIFACT:
            # Artifact steps carry their evidence in the artifact event.
            return
        if result.kind is StepKind.CAPABILITY and result.capability_result is not None:
            payload: Dict[str, Any] = {
                "step_name": result.step_name,
                "provider": result.capability_result.provider,
                "success": result.capability_result.success,
                "error_code": result.capability_result.error_code,
            }
            event_type = "capability.end"
        else:
            payload = {
                "step_name": result.step_name,
                "success": result.status is StepStatus.SUCCEEDED,
            }
            event_type = "action.end"
        collector.record_event(
            {
                "event_id": f"{context.run_id}:{step_context.task_id}:{event_type}",
                "event_type": event_type,
                "task_id": step_context.task_id,
                "payload": payload,
            }
        )

    @staticmethod
    def _record_artifact_event(
        collector: ReportCollector,
        context: ExecutionContext,
        step_context: ExecutionContext,
        artifact: ArtifactHandle,
        index: int,
    ) -> None:
        collector.record_event(
            {
                "event_id": f"{context.run_id}:{step_context.task_id}:artifact-{index}",
                "event_type": "artifact",
                "task_id": step_context.task_id,
                "payload": {
                    "artifact_type": artifact.artifact_type,
                    "path": str(artifact.path),
                },
            }
        )

    async def _execute_step(
        self,
        session: DriverSession,
        step: WorkflowStep,
        context: ExecutionContext,
        collector: ReportCollector,
    ) -> StepExecutionResult:
        if step.kind == "action":
            return await self._run_action(session, step, context)
        if step.kind == "capability":
            return await self._run_capability(step, context, collector)
        if step.kind == "artifact":
            return await self._run_artifact(session, step, context)
        return self._unsupported_step(step, context)

    async def _run_action(
        self,
        session: DriverSession,
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepExecutionResult:
        started = time.monotonic()
        try:
            action_result = session.execute_action(step.name, **dict(step.parameters))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return StepExecutionResult(
                step_id=context.task_id or step.name,
                step_name=step.name,
                kind=StepKind.ACTION,
                status=StepStatus.FAILED,
                attempts=1,
                duration_ms=int((time.monotonic() - started) * 1000),
                context=context,
                action_result=ActionResult(
                    success=False,
                    message=f"{step.name} failed",
                ),
                error=ExecutionFailure(
                    category=FailureCategory.PROVIDER,
                    code="action_execution_failed",
                    message=f"action failed: {step.name}",
                    retryable=False,
                    source="action",
                    details={"error_type": type(exc).__name__},
                ),
            )
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
        except asyncio.CancelledError:
            raise
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
        collector: ReportCollector,
    ) -> StepExecutionResult:
        if self.capability_executor is None:
            return self._capability_missing_executor_step(step, context)

        assert self.capability_executor is not None
        policy = step.policy or CapabilityPolicy()
        started = time.monotonic()
        attempts = 0
        last_result: Optional[CapabilityResult] = None
        last_error: Optional[ExecutionFailure] = None

        try:
            profile = self.capability_executor.execution_profile(step.request)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return self._capability_wiring_failure(step, context, started, exc)

        clock = _RunClock()
        while attempts < policy.max_attempts:
            remaining = clock.remaining(context)
            if remaining is not None and remaining <= 0:
                last_error = ExecutionFailure(
                    category=FailureCategory.TIMEOUT,
                    code="deadline_exceeded",
                    message=f"workflow deadline exceeded before attempt: {step.name}",
                    retryable=False,
                    source="runtime",
                )
                last_result = CapabilityResult(
                    success=False,
                    provider="runtime",
                    error_code="deadline_exceeded",
                )
                break

            attempts += 1
            try:
                if profile.cancellation == "cooperative":
                    last_result = await self._execute_cooperative(
                        step, context, policy, remaining
                    )
                else:
                    # Unsupported cancellation: no hard timeout may be promised
                    # to a provider that cannot honor it (development.md §4.4).
                    last_result = await self.capability_executor.execute(
                        step.request,
                        context,
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
            collector.record_event(
                {
                    "event_id": f"{context.run_id}:{context.task_id}:retry-{attempts}",
                    "event_type": "retry.attempt",
                    "task_id": context.task_id,
                    "payload": {
                        "step_name": step.name,
                        "attempt": attempts,
                        "error_code": (
                            last_error.code
                            if last_error is not None
                            else (last_result.error_code if last_result else None)
                        ),
                    },
                }
            )
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

    async def _execute_cooperative(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
        policy: CapabilityPolicy,
        remaining: Optional[float],
    ) -> CapabilityResult:
        assert self.capability_executor is not None
        execution = self.capability_executor.execute(step.request, context)
        timeout = self._merge_timeout(policy.timeout, remaining)
        if timeout is None:
            return await execution
        return await asyncio.wait_for(execution, timeout=timeout)

    @staticmethod
    def _merge_timeout(
        policy_timeout: Optional[float],
        remaining: Optional[float],
    ) -> Optional[float]:
        if remaining is None:
            return policy_timeout
        if policy_timeout is None:
            return remaining
        return min(policy_timeout, remaining)

    def _capability_missing_executor_step(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepExecutionResult:
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

    def _capability_wiring_failure(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
        started: float,
        exc: Exception,
    ) -> StepExecutionResult:
        return StepExecutionResult(
            step_id=context.task_id or step.name,
            step_name=step.name,
            kind=StepKind.CAPABILITY,
            status=StepStatus.FAILED,
            attempts=0,
            duration_ms=int((time.monotonic() - started) * 1000),
            context=context,
            capability_result=CapabilityResult(
                success=False,
                provider="runtime",
                error_code=type(exc).__name__,
            ),
            error=ExecutionFailure(
                category=_capability_error_category(exc),
                code=type(exc).__name__,
                message=f"capability wiring failed: {step.name}",
                retryable=False,
                source="runtime",
            ),
        )

    def _unhandled_step_failure(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
        exc: Exception,
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
                message=f"{step.name} failed",
            ),
            error=ExecutionFailure(
                category=FailureCategory.PROVIDER,
                code="step_execution_failed",
                message=f"step failed: {step.name}",
                retryable=False,
                source="runtime",
                details={"error_type": type(exc).__name__},
            ),
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
                    path=_cancelled_artifact_path(context, step),
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
