from automation_core.actions import ActionBatch, ActionExecutor, ActionRequest
from automation_core.drivers import ActionResult


class FakeSession:
    def __init__(self):
        self.calls = []

    def execute_action(self, action_name, **kwargs):
        self.calls.append((action_name, kwargs))
        if action_name == "fail":
            return ActionResult(success=False, message="failed")
        return ActionResult(success=True, message=action_name, data=kwargs)


def test_action_request_serializes():
    request = ActionRequest(
        name="tap",
        parameters={"x": 1, "y": 2},
        stop_on_failure=False,
    )

    assert request.to_dict() == {
        "name": "tap",
        "parameters": {"x": 1, "y": 2},
        "stop_on_failure": False,
    }


def test_action_request_uses_empty_parameters_by_default():
    request = ActionRequest(name="refresh")

    assert request.parameters == {}
    assert request.stop_on_failure is True


def test_action_batch_serializes_actions():
    batch = ActionBatch(
        actions=[
            ActionRequest(name="get", parameters={"url": "https://example.test"}),
            ActionRequest(name="screenshot"),
        ]
    )

    assert batch.to_dict() == {
        "actions": [
            {
                "name": "get",
                "parameters": {"url": "https://example.test"},
                "stop_on_failure": True,
            },
            {
                "name": "screenshot",
                "parameters": {},
                "stop_on_failure": True,
            },
        ]
    }


def test_action_executor_runs_action_against_driver_session():
    session = FakeSession()
    executor = ActionExecutor(session)

    result = executor.run(
        ActionRequest(name="get", parameters={"url": "https://example.test"})
    )

    assert result.success is True
    assert result.message == "get"
    assert result.data == {"url": "https://example.test"}
    assert session.calls == [("get", {"url": "https://example.test"})]


def test_action_executor_stops_batch_on_failure_by_default():
    session = FakeSession()
    executor = ActionExecutor(session)
    batch = ActionBatch(
        actions=[
            ActionRequest(name="get"),
            ActionRequest(name="fail"),
            ActionRequest(name="after"),
        ]
    )

    results = executor.run_batch(batch)

    assert [result.success for result in results] == [True, False]
    assert session.calls == [("get", {}), ("fail", {})]


def test_action_executor_can_continue_batch_after_failure():
    session = FakeSession()
    executor = ActionExecutor(session)
    batch = ActionBatch(
        actions=[
            ActionRequest(name="fail", stop_on_failure=False),
            ActionRequest(name="after"),
        ]
    )

    results = executor.run_batch(batch)

    assert [result.success for result in results] == [False, True]
    assert session.calls == [("fail", {}), ("after", {})]
