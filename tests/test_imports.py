import importlib.util


def test_automation_core_imports():
    import automation_core

    assert automation_core.__version__ == "0.3.0"


def test_automation_core_public_modules_import():
    from automation_core.artifacts import ArtifactStore
    from automation_core.capabilities import (
        CapabilityExecutionProfile,
        CapabilityExecutor,
        CapabilityManifest,
        CapabilityRegistry,
        CapabilityRequest,
        CapabilityResolver,
        CapabilityResult,
    )
    from automation_core.config import ConfigSource, EnvConfigSource
    from automation_core.drivers import ElementHandle, ElementLookupSession
    from automation_core.execution import (
        ExecutionContext,
        ExecutionFailure,
        StepExecutionResult,
        WorkflowResult,
    )
    from automation_core.redaction import redact
    from automation_core.retries import RetryPolicy, retry_until

    assert ArtifactStore
    assert CapabilityExecutor
    assert CapabilityExecutionProfile
    assert CapabilityManifest
    assert CapabilityRegistry
    assert CapabilityRequest
    assert CapabilityResolver
    assert CapabilityResult
    assert ConfigSource
    assert EnvConfigSource
    assert ElementHandle
    assert ElementLookupSession
    assert ExecutionContext
    assert ExecutionFailure
    assert StepExecutionResult
    assert WorkflowResult
    assert callable(redact)
    assert RetryPolicy
    assert retry_until


def test_runner_public_surface_imports():
    from automation_runner import (
        CapabilityPolicy,
        ComposedWorkflow,
        WorkflowContext,
        WorkflowOptions,
        WorkflowRuntime,
        WorkflowStep,
    )
    from automation_runner.reports import RunnerReportV2, build_report_v2
    from automation_runner.schemas import load_report_schema

    assert CapabilityPolicy
    assert ComposedWorkflow
    assert WorkflowContext
    assert WorkflowOptions
    assert WorkflowRuntime
    assert WorkflowStep
    assert RunnerReportV2
    assert build_report_v2
    assert load_report_schema


def test_removed_legacy_modules_stay_removed():
    for module in (
        "automation_core.actions",
        "automation_core.events",
        "automation_core.state",
        "automation_core.tasks",
        "automation_runner.runner",
        "examples.workflows",
    ):
        spec = importlib.util.find_spec(module)
        # A namespace spec (no loader) means only an empty stray directory
        # exists; any real resurrection would carry a source loader.
        assert spec is None or spec.loader is None, module


def test_removed_legacy_symbols_stay_removed():
    import automation_runner

    for symbol in ("LegacyWorkflowResult", "ManagedWorkflow", "WorkflowRunner"):
        assert not hasattr(automation_runner, symbol), symbol


def test_example_workflow_factories_import_without_live_dependencies():
    from examples.damai_android import build_steps as android_steps
    from examples.damai_android import create_workflow as create_android_workflow
    from examples.damai_web import build_steps as web_steps
    from examples.damai_web import create_workflow as create_web_workflow

    assert callable(create_web_workflow)
    assert callable(create_android_workflow)
    assert callable(web_steps)
    assert callable(android_steps)
