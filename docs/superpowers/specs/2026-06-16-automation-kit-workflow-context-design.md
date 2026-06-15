# Workflow Context Design

## Goal

Give custom workflow factories a typed, business-agnostic execution context
without moving domain details into `automation_core`.

## Problem

`automation_runner` can already load custom workflow factories, but factories
only receive `session_factory`. That makes runner metadata, CLI toggles, and
workflow inputs spread across ad hoc keyword arguments.

## Proposed Shape

Introduce two runner-layer dataclasses:

```python
@dataclass(frozen=True)
class WorkflowContext:
    workflow_name: str
    live: bool
    workflow_factory: Optional[str] = None
    session_factory: Optional[str] = None


@dataclass(frozen=True)
class WorkflowOptions:
    url: Optional[str] = None
    app_id: Optional[str] = None
    emit_json: bool = False
    report_file: Optional[str] = None
```

Custom workflow factories receive:

```python
create_workflow(
    session_factory=make_session,
    context=context,
    options=options,
)
```

Built-in Damai workflows keep their current `url` and `app_id` signatures for
now.

## Data Flow

1. CLI and config are merged into `RunnerConfig`.
2. Runner builds `WorkflowContext` and `WorkflowOptions` from the merged
   runner settings.
3. Custom factories receive the typed context plus injected session factory.
4. Built-in Damai factories continue using their explicit parameters.
5. Reports keep serializing `workflow_factory` and `session_factory`
   separately.

## Compatibility

- Default tests remain offline.
- `automation_core` stays business-agnostic.
- Older custom workflow factories that only accept `session_factory` should
  keep working through a runner-layer compatibility fallback.

## Non-Goals

- No workflow DSL.
- No generic pass-through of arbitrary CLI kwargs.
- No business selectors, URLs, or app IDs in `automation_core`.
- No change to report JSON shape in this phase.

## Testing Strategy

- Add runner tests for the new typed context values.
- Add fixture coverage for custom factories consuming context and options.
- Keep existing built-in Damai tests green.
