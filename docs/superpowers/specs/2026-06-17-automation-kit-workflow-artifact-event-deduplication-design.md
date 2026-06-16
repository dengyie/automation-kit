# Workflow Artifact Event Deduplication Design

## Goal

Avoid duplicate `artifact` events when an example workflow returns both
artifact handles and caller-provided artifact events for the same artifact.

## Problem

`ExampleWorkflow.run(...)` preserves events returned by a workflow result and
then automatically appends one `artifact` event for every returned artifact
handle. This works for built-in workflows that only return artifact handles.
However, custom workflows can also return structured events. If a custom
workflow already emitted an `artifact` event for an artifact handle, the runner
adds a second equivalent event to the final result.

Duplicate artifact events make JSON reports noisier and can make downstream
consumers over-count captured evidence.

## Proposed Shape

- Keep automatic artifact event generation in `examples.workflows`.
- Preserve caller-provided events.
- Before adding an automatic artifact event, check whether `result.events`
  already contains an `artifact` event for the same task, artifact type, and
  path.
- Add automatic artifact events only for returned artifacts that do not already
  have a matching caller-provided event.
- Keep the existing error-event deduplication behavior unchanged.
- Keep `automation_core` unchanged and business-agnostic.

## Event Match Contract

A caller-provided artifact event matches an artifact handle when:

- `event_type == "artifact"`
- `task_id == session.info.identifier`
- `payload["artifact_type"] == artifact.artifact_type`
- `payload["path"] == str(artifact.path)`

The payload `task_name` is not used for matching because the task identity is
already represented by `task_id`, artifact type, and path.

## Testing Strategy

- Add a regression test where a custom example workflow returns one artifact
  handle plus a matching caller-provided `ArtifactEvent`.
- Verify the final event sequence contains only one `artifact` event.
- Keep existing built-in web and Android workflow event tests green.
- Run the focused example workflow tests, the full suite, `git diff --check`,
  and production review scripts.
