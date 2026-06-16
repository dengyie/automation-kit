# Workflow Artifact Failure Reporting Design

## Goal

When a workflow step fails while capturing an artifact, preserve the actions and
artifacts that already happened and return a structured failed workflow result.

## Problem

`run_workflow_steps(...)` currently flushes pending actions before artifact
steps. If the action batch succeeds and `session.capture_artifact(...)` then
raises, the exception escapes to `ExampleWorkflow.run(...)`.

`ExampleWorkflow.run(...)` catches the exception and returns a failed
`ExampleWorkflowResult`, but it has no access to the already executed action
results or previously captured artifacts. The JSON report can therefore show an
empty `actions` list even though the workflow already interacted with the target
page or app.

For automation runs, this loses important operational evidence. It also weakens
the existing action-batch reporting rule that reports should stay honest about
which actions actually ran.

## Proposed Shape

- Keep the behavior in `examples.workflows`; this is example workflow
  composition, not a core runtime primitive.
- When an artifact step raises inside `run_workflow_steps(...)`, return
  `ExampleWorkflowResult(success=False, ...)` with:
  - prior `actions`,
  - prior successfully captured `artifacts`,
  - current `batch_result` when any action batch ran,
  - `error="<ExceptionType>: <message>"`.
- Ensure the session is still stopped by the existing `finally` block.
- Update `ExampleWorkflow.run(...)` so returned failed workflow results with an
  `error` also produce one `error` event before `task.end`.
- Do not duplicate an `error` event when the returned workflow result already
  includes one.
- Keep exception handling for failures that happen before `run_fn` returns.
- Do not change `automation_core`.
- Do not change adapter artifact capture internals in this slice.

## Error Contract

For an artifact capture failure such as:

```python
RuntimeError("screenshot failed")
```

the returned result should include:

```python
success is False
error == "RuntimeError: screenshot failed"
```

When run through `ExampleWorkflow.run(...)`, event order should be:

```text
task.start
artifact
error
task.end
```

where prior artifact events are emitted only for artifacts captured before the
failure.

## Testing Strategy

- Add a fake session that raises from `capture_artifact(...)` only for a chosen
  artifact name.
- Add a direct `run_workflow_steps(...)` regression test proving:
  - preceding actions are preserved,
  - preceding artifacts are preserved,
  - the failed artifact is not appended,
  - `success` is false,
  - `error` is typed,
  - the session is stopped.
- Add an `ExampleWorkflow.run(...)` regression test proving returned failure
  results emit an `error` event while preserving prior artifact events.
- Add an `ExampleWorkflow.run(...)` regression test proving caller-provided
  `error` events are not duplicated.
- Run focused example workflow tests and the full suite.
