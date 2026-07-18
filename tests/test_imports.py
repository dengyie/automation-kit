def test_automation_core_imports():
    import automation_core

    assert automation_core.__version__ == "0.2.0"


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


def test_example_workflow_factories_import_without_live_dependencies():
    from examples.damai_android import create_workflow as create_android_workflow
    from examples.damai_web import create_workflow as create_web_workflow

    assert callable(create_web_workflow)
    assert callable(create_android_workflow)
