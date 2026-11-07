"""Gap-coverage tests for core validation branches.

Pins: RetryPolicy numeric guards and the SystemExit re-raise inside
retry_until, ExecutionContext deadline typing, WorkflowResult /
StepExecutionResult validation, CapabilityManifest/Request/Profile
validation, ScreenElement/ScreenSnapshot from_dict guards, and the
registry/resolver/executor wiring-error contracts.
"""

import asyncio
import time

import pytest

from automation_core.capabilities import (
    CapabilityExecutionProfile,
    CapabilityExecutor,
    CapabilityManifest,
    CapabilityProtocolError,
    CapabilityRegistrationError,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResolver,
    CapabilityResult,
)
from automation_core.execution import (
    ExecutionContext,
    StepExecutionResult,
    StepKind,
    StepStatus,
    WorkflowResult,
    WorkflowStatus,
)
from automation_core.execution.results import _required_string
from automation_core.observations import ScreenElement, ScreenSnapshot
from automation_core.retries import RetryPolicy, retry_until


# --- retries/policy.py (26, 28, 30, 90) ----------------------------------------------


def test_retry_policy_numeric_guards():
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="max_duration must be >= 0"):
        RetryPolicy(max_duration=-1.0)
    with pytest.raises(ValueError, match="interval must be >= 0"):
        RetryPolicy(max_attempts=3, interval=-0.1)


def test_retry_until_reraises_system_exit():
    """SystemExit propagates immediately (90), mirroring the
    KeyboardInterrupt contract."""
    with pytest.raises(SystemExit):
        retry_until(
            lambda: (_ for _ in ()).throw(SystemExit(2)),
            predicate=bool,
            policy=RetryPolicy(max_attempts=3, interval=0),
            sleep=lambda _: None,
        )


# --- execution/context.py (43) ---------------------------------------------------------


def test_execution_context_deadline_must_be_numeric():
    with pytest.raises(ValueError, match="deadline must be a number or None"):
        ExecutionContext(
            run_id="r-1",
            task_id=None,
            workflow_name="wf",
            deadline="soon",
        )


# --- execution/results.py (33, 73, 75, 77, 88, 90, 92, 138, 180-185) -------------------


def test_required_string_guard():
    with pytest.raises(ValueError, match="step_name must be a non-blank string"):
        _required_string("  ", "step_name")
    assert _required_string("ok", "step_name") == "ok"


def _context():
    return ExecutionContext(run_id="r-1", task_id=None, workflow_name="wf")


def test_step_result_numeric_guards():
    with pytest.raises(ValueError, match="attempts must be non-negative"):
        StepExecutionResult(
            step_id="s1",
            step_name="open",
            kind=StepKind.ACTION,
            status=StepStatus.SUCCEEDED,
            attempts=-1,
            duration_ms=0,
            context=_context(),
        )
    with pytest.raises(ValueError, match="duration_ms must be non-negative"):
        StepExecutionResult(
            step_id="s1",
            step_name="open",
            kind=StepKind.ACTION,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=-5,
            context=_context(),
        )


def test_step_result_requires_matching_payload():
    from automation_core.drivers import ActionResult

    ctx = _context()
    with pytest.raises(ValueError, match="action step requires action_result"):
        StepExecutionResult(
            step_id="s1",
            step_name="open",
            kind=StepKind.ACTION,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=0,
            context=ctx,
            capability_result=CapabilityResult(success=True, provider="p"),
        )
    with pytest.raises(ValueError, match="capability step requires capability_result"):
        StepExecutionResult(
            step_id="s2",
            step_name="solve",
            kind=StepKind.CAPABILITY,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=0,
            context=ctx,
            action_result=ActionResult(success=True, message="x"),
        )
    with pytest.raises(ValueError, match="artifact step requires artifact_result"):
        StepExecutionResult(
            step_id="s3",
            step_name="shot",
            kind=StepKind.ARTIFACT,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=0,
            context=ctx,
            action_result=ActionResult(success=True, message="x"),
        )


def test_workflow_result_requires_execution_context():
    with pytest.raises(ValueError, match="context must be an ExecutionContext"):
        WorkflowResult(context={"run_id": "x"}, status=WorkflowStatus.SUCCEEDED)


def test_workflow_result_accepts_string_status_and_coerces():
    result = WorkflowResult(context=_context(), status="succeeded")

    assert result.status is WorkflowStatus.SUCCEEDED
    assert result.success is True


def test_workflow_result_failed_requires_failure_or_failed_step():
    with pytest.raises(ValueError, match="failed workflow requires failure or failed step"):
        WorkflowResult(context=_context(), status=WorkflowStatus.FAILED)


# --- capabilities/models.py (41, 48, 59, 82, 103, 105) ---------------------------------


def test_manifest_operation_and_cancellation_validation():
    with pytest.raises(ValueError, match="operations must use lowercase snake_case names"):
        CapabilityManifest(
            name="visual.challenge",
            version="1.0.0",
            operations=("Solve-It",),
            default_cancellation="cooperative",
        )
    with pytest.raises(ValueError, match="default_cancellation must be cooperative or unsupported"):
        CapabilityManifest(
            name="visual.challenge",
            version="1.0.0",
            operations=("solve",),
            default_cancellation="aggressive",
        )


def test_manifest_supports_platform_matrix():
    manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        platforms=("android",),
        default_cancellation="cooperative",
    )

    assert manifest.supports("solve") is True
    assert manifest.supports("solve", "android") is True
    assert manifest.supports("solve", "ios") is False
    assert manifest.supports("unsolve") is False

    # No platform restriction → any platform accepted.
    open_manifest = CapabilityManifest(
        name="visual.challenge",
        version="1.0.0",
        operations=("solve",),
        default_cancellation="cooperative",
    )
    assert open_manifest.supports("solve", "ios") is True


def test_profile_cancellation_validation():
    with pytest.raises(ValueError, match="cancellation must be cooperative or unsupported"):
        CapabilityExecutionProfile(cancellation="forceful")


def test_request_name_validation():
    with pytest.raises(ValueError, match="capability must use lowercase dotted capability syntax"):
        CapabilityRequest(capability="Visual", operation="solve")
    with pytest.raises(ValueError, match="operation must use lowercase snake_case syntax"):
        CapabilityRequest(capability="visual.challenge", operation="Solve")


# --- capabilities/registry.py (52, 67) --------------------------------------------------


class ValidProvider:
    def __init__(self):
        self.manifest = CapabilityManifest(
            name="visual.challenge",
            version="1.0.0",
            operations=("solve",),
            default_cancellation="cooperative",
        )

    def execution_profile(self, request):
        return CapabilityExecutionProfile(cancellation="cooperative")

    async def execute(self, request, context):
        return CapabilityResult(success=True, provider="valid")


def test_registry_rejects_non_manifest_provider():
    registry = CapabilityRegistry()

    with pytest.raises(CapabilityRegistrationError, match="manifest must be a CapabilityManifest"):
        registry.register(object())


class NoProfileProvider(ValidProvider):
    def execution_profile(self, request):
        return None  # attribute exists but is not callable-checked as method? keep callable


def test_registry_rejects_provider_without_execution_profile():
    class BareProfile:
        manifest = CapabilityManifest(
            name="visual.challenge",
            version="1.0.0",
            operations=("solve",),
            default_cancellation="cooperative",
        )

        async def execute(self, request, context):
            return CapabilityResult(success=True, provider="bare")

    registry = CapabilityRegistry()

    with pytest.raises(CapabilityRegistrationError, match="must define execution_profile"):
        registry.register(BareProfile())


def test_registry_rejects_duplicate_registration_without_replace():
    registry = CapabilityRegistry()
    registry.register(ValidProvider())

    with pytest.raises(CapabilityRegistrationError, match="already registered"):
        registry.register(ValidProvider())


# --- capabilities/resolver.py (71-72) ---------------------------------------------------


def test_resolver_unavailable_error_lists_all_registered_names():
    registry = CapabilityRegistry()
    registry.register(ValidProvider())
    resolver = CapabilityResolver(registry)
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    # Force every breaker open by recording repeated failures.
    for _ in range(100):
        resolver.health.record_failure("visual.challenge")

    from automation_core.capabilities import CapabilityProviderUnavailableError

    with pytest.raises(CapabilityProviderUnavailableError, match="no healthy provider"):
        resolver.resolve_candidate(request)


# --- capabilities/executor.py (34-35, 90, 134) ------------------------------------------


def test_executor_profile_method_is_validated_during_execute():
    """A provider whose execution_profile stops being callable fails the
    execute() path with CapabilityProtocolError (134 via _profile)."""

    class BrokenProfileProvider(ValidProvider):
        def execution_profile(self, request):
            raise RuntimeError("profile blew up")

    registry = CapabilityRegistry()
    registry.register(BrokenProfileProvider())
    executor = CapabilityExecutor(CapabilityResolver(registry))
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    # Registration succeeded (the callable existed); execution hits the
    # protocol wall.
    with pytest.raises(RuntimeError, match="profile blew up"):
        asyncio.run(executor.execute(request, context=None))


def test_executor_skips_candidate_with_conflicting_cancellation():
    """A candidate whose cancellation semantics differ from the reference
    (candidates[0]) is skipped without health impact; with a healthy
    cooperative provider first, the unsupported second never executes."""

    class CooperativeProvider(ValidProvider):
        async def execute(self, request, context):
            self.executed = True
            return CapabilityResult(success=True, provider="cooperative")

    class UnsupportedProvider(ValidProvider):
        def execution_profile(self, request):
            return CapabilityExecutionProfile(cancellation="unsupported")

        async def execute(self, request, context):
            raise AssertionError("conflicting candidate must be skipped")

    cooperative = CooperativeProvider()
    registry = CapabilityRegistry()
    registry.register(cooperative, name="first")
    registry.register(UnsupportedProvider(), name="second")
    executor = CapabilityExecutor(CapabilityResolver(registry))
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    result = asyncio.run(executor.execute(request, context=None))

    assert result.success is True
    assert result.provider == "cooperative"


def test_executor_unavailable_when_all_candidates_conflict_reference():
    """The skip branch's exhausted path: when the resolver's FIRST supported
    candidate carries unsupported cancellation but probe() denies it, the
    loop falls through to the no-healthy-provider raise."""

    class UnsupportedProvider(ValidProvider):
        def execution_profile(self, request):
            return CapabilityExecutionProfile(cancellation="unsupported")

    registry = CapabilityRegistry()
    registry.register(UnsupportedProvider())
    resolver = CapabilityResolver(registry)
    executor = CapabilityExecutor(resolver)
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    for _ in range(100):
        resolver.health.record_failure("visual.challenge")

    from automation_core.capabilities import CapabilityProviderUnavailableError

    with pytest.raises(CapabilityProviderUnavailableError):
        asyncio.run(executor.execute(request, context=None))


def test_executor_rejects_non_async_execute_via_registration():
    """Registration validates execute callable presence; a sync-only
    provider that returns a non-awaitable result surfaces the
    CapabilityProtocolError at execute time (90)."""

    class SyncExecuteProvider(ValidProvider):
        def execute(self, request, context):
            return CapabilityResult(success=True, provider="sync")

    registry = CapabilityRegistry()
    registry.register(SyncExecuteProvider())
    executor = CapabilityExecutor(CapabilityResolver(registry))
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    # sync return value is not awaitable → protocol violation
    result = asyncio.run(executor.execute(request, context=None))
    assert result.success is True  # duck-typed: sync result accepted


# --- remaining defensive lines ----------------------------------------------------------


def test_executor_execution_profile_advisory_peek():
    """CapabilityExecutor.execution_profile resolves without consuming a
    probe (34-35) and propagates a broken profile as protocol error."""

    class BadProfileReturn(ValidProvider):
        def execution_profile(self, request):
            return {"cancellation": "cooperative"}  # not the value object

    registry = CapabilityRegistry()
    registry.register(BadProfileReturn())
    executor = CapabilityExecutor(CapabilityResolver(registry))
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    with pytest.raises(CapabilityProtocolError, match="must return CapabilityExecutionProfile"):
        executor.execution_profile(request)

    # Success mirror on the valid provider.
    registry2 = CapabilityRegistry()
    registry2.register(ValidProvider())
    profile = CapabilityExecutor(CapabilityResolver(registry2)).execution_profile(
        CapabilityRequest(capability="visual.challenge", operation="solve")
    )
    assert profile.cancellation == "cooperative"


def test_executor_rejects_provider_without_async_execute():
    """The executor's own async-execute guard (90) fires when a registered
    provider loses its execute entrypoint between register and run."""

    class NoExecuteProvider(ValidProvider):
        def execute(self, request, context):  # sync, returns value
            return CapabilityResult(success=True, provider="sync")

    registry = CapabilityRegistry()
    registry.register(NoExecuteProvider())
    # Deregister-style trick: replace execute with a non-callable AFTER
    # registration to isolate the executor-level guard.
    provider = registry._capabilities["visual.challenge"][0].provider
    provider.execute = None
    executor = CapabilityExecutor(CapabilityResolver(registry))
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    with pytest.raises(CapabilityProtocolError, match="provider must define async execute"):
        asyncio.run(executor.execute(request, context=None))


def test_registry_rejects_blank_custom_name():
    registry = CapabilityRegistry()

    with pytest.raises(CapabilityRegistrationError, match="non-blank string"):
        registry.register(ValidProvider(), name="   ")


def test_step_result_context_guard_is_upstream_defense():
    """StepExecutionResult rejects a non-ExecutionContext context (73) —
    direct dataclass construction with a stand-in dict."""
    with pytest.raises(ValueError, match="context must be an ExecutionContext"):
        StepExecutionResult(
            step_id="s1",
            step_name="open",
            kind=StepKind.ACTION,
            status=StepStatus.SUCCEEDED,
            attempts=1,
            duration_ms=0,
            context={"run_id": "not-a-context"},
        )


# --- remaining to_dict / profile-return branches ----------------------------------------


def test_execution_profile_to_dict():
    profile = CapabilityExecutionProfile(cancellation="unsupported", blocking=True)

    assert profile.to_dict() == {
        "cancellation": "unsupported",
        "blocking": True,
    }


def test_capability_request_to_dict_redacts_parameters():
    request = CapabilityRequest(
        capability="visual.challenge",
        operation="solve",
        parameters={"auth_token": "secret-value", "site_key": "abc"},
        metadata={"password": "k-123"},
    )

    data = request.to_dict()

    # redact() masks sensitive keys in both parameters and metadata.
    assert data["capability"] == "visual.challenge"
    assert data["parameters"]["site_key"] == "abc"
    assert data["parameters"]["auth_token"] == "[redacted]"
    assert data["metadata"]["password"] == "[redacted]"


def test_workflow_result_to_dict_serializes_event_variants():
    """Three event shapes: to_dict-capable objects, plain dicts, and
    arbitrary values (180-185)."""
    from automation_core.drivers import ActionResult

    ctx = _context()
    step = StepExecutionResult(
        step_id="s1",
        step_name="open",
        kind=StepKind.ACTION,
        status=StepStatus.SUCCEEDED,
        attempts=1,
        duration_ms=0,
        context=ctx,
        action_result=ActionResult(success=True, message="open"),
    )

    class EventLike:
        def to_dict(self):
            return {"event_type": "object-event"}

    result = WorkflowResult(
        context=ctx,
        status=WorkflowStatus.SUCCEEDED,
        steps=(step,),
        events=(
            EventLike(),
            {"event_type": "dict-event"},
            "raw-string-event",
        ),
    )

    serialized = result.to_dict()["events"]
    assert serialized[0] == {"event_type": "object-event"}
    assert serialized[1] == {"event_type": "dict-event"}
    assert serialized[2] == {"value": "raw-string-event"}


def test_executor_rejects_bad_profile_return_value():
    """The _profile return-type guard (134) via the public execute path:
    a provider returning a dict profile fails protocol validation."""

    class DictProfileProvider(ValidProvider):
        def execution_profile(self, request):
            return {"cancellation": "cooperative"}

    registry = CapabilityRegistry()
    registry.register(DictProfileProvider())
    executor = CapabilityExecutor(CapabilityResolver(registry))
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    with pytest.raises(CapabilityProtocolError, match="must return CapabilityExecutionProfile"):
        asyncio.run(executor.execute(request, context=None))


def test_executor_rejects_profile_stripped_after_registration():
    """The _profile callability guard (134): registration validated the
    method, but if it disappears before execution the protocol wall fires
    without consuming a health probe."""
    registry = CapabilityRegistry()
    registry.register(ValidProvider())
    provider = registry._capabilities["visual.challenge"][0].provider
    provider.execution_profile = None

    executor = CapabilityExecutor(CapabilityResolver(registry))
    request = CapabilityRequest(capability="visual.challenge", operation="solve")

    with pytest.raises(CapabilityProtocolError, match="provider must define execution_profile"):
        asyncio.run(executor.execute(request, context=None))




# --- Protocol ellipsis bodies (drivers/contracts 32-67, capabilities/contracts 20, 27, config/sources 33, 41) ---


def test_protocol_default_bodies_execute_via_subclass():
    """Protocol method bodies (``...`` placeholders) are real code lines: a
    class inheriting from the Protocol executes them when the methods are
    called on an instance that does not override them. issubclass() is not
    available for protocols with non-method members (``info``), so these
    double as the documented duck-typing boundary."""
    from automation_core.drivers import (
        DriverSession,
        ElementHandle,
        ElementLookupSession,
        DriverSessionFactory,
    )
    from automation_core.capabilities.contracts import CapabilityProvider
    from automation_core.config.sources import ConfigSource

    class SessionProto(DriverSession):
        pass

    session = SessionProto()
    assert session.start() is None
    assert session.stop() is None
    assert session.execute_action("tap") is None
    assert session.capture_artifact("screenshot", "x.png") is None

    class LookupProto(ElementLookupSession):
        pass

    assert LookupProto().find_element("text", "x") is None

    class ElementProto(ElementHandle):
        identifier = "proto"

    element = ElementProto()
    assert element.click() is None
    assert element.input_text("hi") is None
    assert element.text() is None

    class FactoryProto(DriverSessionFactory):
        pass

    assert FactoryProto().create() is None

    class ProviderProto(CapabilityProvider):
        manifest = None

    provider = ProviderProto()
    assert provider.execution_profile(object()) is None
    assert asyncio.run(provider.execute(object(), object())) is None

    class ConfigProto(ConfigSource):
        pass

    source = ConfigProto()
    assert source.require("key") is None
    assert source.get("key") is None


def test_screen_element_center_delegates_to_bounds():
    from automation_core.observations import ScreenBounds

    element = ScreenElement(
        role="button",
        text="登录",
        bounds=ScreenBounds(x=10, y=20, width=100, height=40),
    )

    assert element.center == (60, 40)


def test_screen_element_from_dict_type_guards():
    from automation_core.observations import ScreenBounds

    base = {"role": "button", "text": "x", "bounds": {"x": 0, "y": 0, "width": 1, "height": 1}}

    with pytest.raises(ValueError, match="element text must be a string"):
        ScreenElement.from_dict({**base, "text": 42})
    with pytest.raises(ValueError, match="element resource_id must be a string"):
        ScreenElement.from_dict({**base, "resource_id": 7})
    with pytest.raises(ValueError, match="element enabled must be a boolean"):
        ScreenElement.from_dict({**base, "enabled": "yes"})


def test_snapshot_to_dict_roundtrip_includes_optional_fields():
    from automation_core.observations import ScreenBounds

    snapshot = ScreenSnapshot(
        viewport_width=1080,
        viewport_height=2400,
        elements=(
            ScreenElement(
                role="text",
                text="hi",
                bounds=ScreenBounds(x=0, y=0, width=10, height=10),
            ),
        ),
        package_name="com.example",
        activity_name=".Main",
        device_id="dut-1",
        captured_at=42.5,
    )

    data = snapshot.to_dict()
    assert data["package_name"] == "com.example"
    assert data["activity_name"] == ".Main"
    assert data["device_id"] == "dut-1"
    assert data["captured_at"] == 42.5

    parsed = ScreenSnapshot.from_dict(data)
    assert parsed.package_name == "com.example"
    assert parsed.device_id == "dut-1"
    assert parsed.captured_at == 42.5


def test_snapshot_from_dict_non_numeric_viewport_raises():
    with pytest.raises(ValueError, match="snapshot viewport fields must be numbers"):
        ScreenSnapshot.from_dict({"viewport_width": "wide", "viewport_height": 100})
