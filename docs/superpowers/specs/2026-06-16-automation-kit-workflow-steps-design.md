# Workflow Steps Design

## Goal

Give example workflows a small, composable way to describe ordered actions and
artifact captures without moving workflow DSL or business logic into
`automation_core`.

## Problem

Built-in smoke workflows already use `ActionBatch`, but each workflow still
hand-writes the same orchestration shape:

- start the injected session,
- run one or more driver actions,
- capture artifacts,
- build `ExampleWorkflowResult`,
- stop the session in `finally`.

That is enough for the current examples, but it makes the next real automation
application awkward to grow. A website or Android workflow should be able to
add more ordered action and artifact steps without duplicating lifecycle and
result assembly code.

## Proposed Shape

Add example-layer workflow step primitives in `examples.workflows`:

```python
WorkflowStep.action("open", url=url)
WorkflowStep.artifact("screenshot", "home.png")
```

Add a runner helper:

```python
run_workflow_steps(session, steps)
```

The helper should:

- start and stop the session with `try/finally`,
- execute contiguous action steps through `ActionExecutor.run_batch(...)`,
- capture artifact steps in order after the preceding action batch,
- aggregate action results, artifacts, and batch summaries into
  `ExampleWorkflowResult`,
- stop execution when an action batch fails with skipped actions,
- treat artifact-only sequences as successful and leave `batch_result` empty,
- keep exceptions propagating so `ExampleWorkflow.run()` can preserve its
  existing failure event behavior.

## Boundaries

- Keep the step API in `examples`, not `automation_core`.
- Do not introduce YAML, JSON, or another persisted workflow DSL.
- Do not add Damai/Dianping selectors, URLs, package names, or business flows
  to `automation_core`.
- Do not add Selenium/Appium imports to default workflow paths.
- Keep default tests offline and deterministic.

## Compatibility

- Existing `ExampleWorkflow` and `ExampleWorkflowResult` remain compatible.
- Built-in Damai smoke workflows keep their public `run_smoke_workflow(...)`
  and `create_workflow(...)` functions.
- Existing report fields remain unchanged.

## Testing Strategy

- Add example workflow tests for action and artifact step ordering.
- Add a failure test proving skipped action steps are surfaced in
  `batch_result` and later artifact steps are not captured after a failed
  stop-on-failure action.
- Add an artifact-only test proving no empty `action_batch` summary is emitted.
- Update Damai web and Android tests to keep proving the same public behavior.
- Run full suite and production review scripts before committing.
