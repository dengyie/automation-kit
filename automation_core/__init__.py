"""Business-agnostic automation runtime primitives."""

__version__ = "0.2.0"
from automation_core.execution import (
    ExecutionContext,
    ExecutionFailure,
    FailureCategory,
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowResult as ExecutionWorkflowResult,
    WorkflowStatus,
)

__all__ = [
    "__version__",
    "ExecutionContext",
    "ExecutionFailure",
    "ExecutionWorkflowResult",
    "FailureCategory",
    "StepExecutionResult",
    "StepKind",
    "StepStatus",
    "WorkflowStatus",
]
