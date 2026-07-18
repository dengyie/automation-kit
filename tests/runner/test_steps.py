import pytest

from automation_core.capabilities import CapabilityRequest
from automation_runner.policies import CapabilityPolicy
from automation_runner.steps import WorkflowStep


def test_workflow_step_action_and_capability_factories():
    action = WorkflowStep.action("open", url="https://example.test")
    capability = WorkflowStep.capability(
        "solve-captcha",
        request=CapabilityRequest(
            capability="visual.challenge",
            operation="solve",
            parameters={"challenge_type": "slider_captcha"},
        ),
        policy=CapabilityPolicy(timeout=1.0, max_attempts=2, backoff=0.0),
    )

    assert action.kind == "action"
    assert action.name == "open"
    assert action.parameters["url"] == "https://example.test"
    assert capability.kind == "capability"
    assert capability.name == "solve-captcha"
    assert capability.request.capability == "visual.challenge"
    assert capability.policy.max_attempts == 2


def test_workflow_step_rejects_blank_names():
    with pytest.raises(ValueError, match="action name"):
        WorkflowStep.action(" ")

    with pytest.raises(ValueError, match="capability name"):
        WorkflowStep.capability(
            "",
            request=CapabilityRequest(
                capability="visual.challenge",
                operation="solve",
            ),
        )
