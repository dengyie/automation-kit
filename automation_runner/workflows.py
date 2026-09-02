"""Workflow composition helpers shared by built-in examples and app repos.

A workflow factory returns a :class:`ComposedWorkflow`: a
:class:`~automation_runner.runtime.WorkflowRuntime` wired in a composition
root plus the declarative :class:`WorkflowStep` list it should execute.
"""

from typing import List

from automation_core.execution import WorkflowResult as ExecutionWorkflowResult
from automation_runner.runtime import WorkflowRuntime
from automation_runner.steps import WorkflowStep

__all__ = ["ComposedWorkflow", "WorkflowStep"]


class ComposedWorkflow:
    """A runtime plus the steps it owns; ``run`` returns the runtime result."""

    def __init__(self, runtime: WorkflowRuntime, steps: List[WorkflowStep]) -> None:
        self.runtime = runtime
        self.steps = list(steps)
        self.name = runtime.workflow_name

    async def arun(self) -> ExecutionWorkflowResult:
        return await self.runtime.arun(self.steps)

    def run(self) -> ExecutionWorkflowResult:
        return self.runtime.run(self.steps)
