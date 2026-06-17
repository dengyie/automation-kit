"""Compatibility layer for built-in examples.

External application repositories should import workflow helpers from
automation_runner.workflows. This module remains only to avoid breaking
built-in examples and existing tests during the transition.
"""

from automation_runner.workflows import (
    ExampleWorkflow,
    ExampleWorkflowResult,
    ManagedWorkflow,
    WorkflowResult,
    WorkflowStep,
    run_workflow_steps,
)

__all__ = [
    "ExampleWorkflow",
    "ExampleWorkflowResult",
    "ManagedWorkflow",
    "WorkflowResult",
    "WorkflowStep",
    "run_workflow_steps",
]
