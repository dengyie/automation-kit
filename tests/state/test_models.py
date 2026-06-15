from automation_core.state import RunState, RunStatus


def test_run_state_defaults_to_pending():
    state = RunState(run_id="run-1")

    assert state.run_id == "run-1"
    assert state.status == RunStatus.PENDING
    assert state.finished_at is None
    assert state.outcome is None
    assert isinstance(state.started_at, float)


def test_run_state_accepts_terminal_values():
    state = RunState(
        run_id="run-1",
        status=RunStatus.SUCCEEDED,
        finished_at=2.0,
        outcome="ok",
    )

    assert state.status == RunStatus.SUCCEEDED
    assert state.finished_at == 2.0
    assert state.outcome == "ok"


def test_run_state_transitions():
    state = RunState(
        run_id="run-1",
        started_at=1.0,
        finished_at=2.0,
        outcome="stale",
    )

    state.start()
    assert state.status == RunStatus.RUNNING
    assert state.started_at != 1.0
    assert state.finished_at is None
    assert state.outcome is None

    state.succeed("ok")
    assert state.status == RunStatus.SUCCEEDED
    assert state.outcome == "ok"
    assert state.finished_at is not None


def test_run_state_can_fail_and_cancel():
    state = RunState(run_id="run-1")

    state.fail()
    assert state.status == RunStatus.FAILED
    assert state.outcome == "failed"

    state = RunState(run_id="run-2")
    state.cancel()
    assert state.status == RunStatus.CANCELLED
    assert state.outcome == "cancelled"
