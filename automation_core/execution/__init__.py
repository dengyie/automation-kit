"""Execution identity, failure, and step result models."""

from automation_core.execution.context import ExecutionContext
from automation_core.execution.failures import ExecutionFailure, FailureCategory
from automation_core.execution.results import (
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowResult,
    WorkflowStatus,
)

__all__ = [
    "ExecutionContext",
    "ExecutionFailure",
    "FailureCategory",
    "StepExecutionResult",
    "StepKind",
    "StepStatus",
    "WorkflowResult",
    "WorkflowStatus",
]
