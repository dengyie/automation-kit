"""Minimal runner facade for automation-kit examples."""

from automation_runner.context import WorkflowContext, WorkflowOptions
from automation_runner.runner import WorkflowRunner
from automation_runner.policies import CapabilityPolicy
from automation_runner.runtime import WorkflowRuntime
from automation_runner.steps import WorkflowStep
from automation_runner.workflows import (
    ManagedWorkflow,
    WorkflowResult,
    run_workflow_steps,
)

__all__ = [
    "WorkflowRunner",
    "WorkflowContext",
    "WorkflowOptions",
    "CapabilityPolicy",
    "WorkflowRuntime",
    "ManagedWorkflow",
    "WorkflowResult",
    "WorkflowStep",
    "run_workflow_steps",
]
