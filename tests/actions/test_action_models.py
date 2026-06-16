from automation_core.actions import ActionBatch, ActionBatchResult, ActionExecutor, ActionRequest
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


def test_action_executor_returns_batch_summary_for_successful_batch():
    session = FakeSession()
    executor = ActionExecutor(session)
    batch = ActionBatch(
        actions=[
            ActionRequest(name="get"),
            ActionRequest(name="screenshot", parameters={"name": "home.png"}),
        ]
    )

    result = executor.run_batch(batch)

    assert isinstance(result, ActionBatchResult)
    assert result.success is True
    assert [action.message for action in result.results] == ["get", "screenshot"]
    assert result.skipped == []


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

    result = executor.run_batch(batch)

    assert isinstance(result, ActionBatchResult)
    assert [item.success for item in result.results] == [True, False]
    assert result.success is False
    assert [item.name for item in result.skipped] == ["after"]
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

    result = executor.run_batch(batch)

    assert isinstance(result, ActionBatchResult)
    assert [item.success for item in result.results] == [False, True]
    assert result.skipped == []
    assert session.calls == [("fail", {}), ("after", {})]


def test_action_executor_returns_empty_batch_summary_for_empty_batch():
    session = FakeSession()
    executor = ActionExecutor(session)

    result = executor.run_batch(ActionBatch(actions=[]))

    assert isinstance(result, ActionBatchResult)
    assert result.success is False
    assert result.results == []
    assert result.skipped == []


def test_action_batch_result_serializes():
    result = ActionBatchResult(
        results=[ActionResult(success=True, message="get")],
        skipped=[ActionRequest(name="after")],
    )

    assert result.to_dict() == {
        "results": [
            {"success": True, "message": "get", "data": None},
        ],
        "skipped": [
            {
                "name": "after",
                "parameters": {},
                "stop_on_failure": True,
            }
        ],
        "success": True,
    }
