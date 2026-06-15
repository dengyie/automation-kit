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

    state.start(started_at=3.0)
    assert state.status == RunStatus.RUNNING
    assert state.started_at == 3.0
    assert state.finished_at is None
    assert state.outcome is None

    state.succeed("ok", finished_at=4.0)
    assert state.status == RunStatus.SUCCEEDED
    assert state.outcome == "ok"
    assert state.finished_at == 4.0


def test_run_state_can_fail_and_cancel():
    state = RunState(run_id="run-1")

    state.fail(finished_at=5.0)
    assert state.status == RunStatus.FAILED
    assert state.outcome == "failed"
    assert state.finished_at == 5.0

    state = RunState(run_id="run-2")
    state.cancel(finished_at=6.0)
    assert state.status == RunStatus.CANCELLED
    assert state.outcome == "cancelled"
    assert state.finished_at == 6.0
