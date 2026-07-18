def test_automation_core_imports():
    import automation_core

    assert automation_core.__version__ == "0.3.0"


def test_automation_core_actions_imports():
    from automation_core.actions import ActionBatch, ActionExecutor, ActionRequest

    assert ActionBatch
    assert ActionExecutor
    assert ActionRequest


def test_automation_core_driver_element_imports():
    from automation_core.drivers import ElementHandle, ElementLookupSession

    assert ElementHandle
    assert ElementLookupSession


def test_automation_core_task_runner_imports():
    from automation_core.tasks import TaskCancelledError, TaskResult, TaskRunner

    assert TaskCancelledError
    assert TaskResult
    assert TaskRunner


def test_automation_core_state_imports():
    from automation_core.state import RunState, RunStatus

    assert RunState
    assert RunStatus


def test_automation_core_capability_imports():
    from automation_core.capabilities import (
        CapabilityExecutor,
        CapabilityManifest,
        CapabilityRegistry,
        CapabilityRequest,
        CapabilityResult,
    )

    assert CapabilityExecutor
    assert CapabilityManifest
    assert CapabilityRegistry
    assert CapabilityRequest
    assert CapabilityResult

    from automation_core.capabilities import (
        CapabilityExecutionProfile,
        CapabilityResolver,
    )

    assert CapabilityExecutionProfile
    assert CapabilityResolver


def test_automation_core_execution_imports():
    from automation_core.execution import (
        ExecutionContext,
        ExecutionFailure,
        StepExecutionResult,
        WorkflowResult,
    )

    assert ExecutionContext
    assert ExecutionFailure
    assert StepExecutionResult
    assert WorkflowResult


def test_runner_exports_legacy_and_runtime_result_boundaries():
    from automation_core.execution import WorkflowResult as ExecutionWorkflowResult
    from automation_runner import LegacyWorkflowResult, WorkflowResult, WorkflowRuntime

    assert WorkflowResult is LegacyWorkflowResult
    assert ExecutionWorkflowResult is not LegacyWorkflowResult
    assert WorkflowRuntime


def test_example_workflow_factories_import_without_live_dependencies():
    from examples.damai_android import create_workflow as create_android_workflow
    from examples.damai_web import create_workflow as create_web_workflow

    assert callable(create_web_workflow)
    assert callable(create_android_workflow)
