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
