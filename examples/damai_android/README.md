# Damai Android Example Shell

This directory shows how a Damai Android workflow composes `automation_core`
primitives with an Appium-based adapter.

## Owns

- Damai Android selectors
- app package and activity configuration
- Android-specific interaction strategies
- Appium adapter wiring for the example

## Must Not Own

- core retry policy implementation
- core task lifecycle rules
- core event models
- core artifact storage rules
- web-specific behavior

## Smoke Workflow

`run_smoke_workflow(session, app_id)` starts an injected driver session,
activates the provided app ID through the session contract, captures screenshot
and page-source artifacts, and then stops the session.

The workflow is intentionally thin. It proves wiring without embedding ticket
purchase decisions in `automation_core`.

## Workflow Factory

`create_workflow(session_factory, app_id)` returns a small object with `run()`.
That shape is the example authoring API for composing dry or live runs around
an injected session factory.
