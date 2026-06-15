# Damai Web Example Shell

This directory shows how a Damai web workflow composes `automation_core`
primitives with a Selenium-based adapter.

## Owns

- Damai web selectors
- Damai login and navigation flow
- ticket selection and order-specific decisions
- Selenium adapter wiring for the example

## Must Not Own

- core retry policy implementation
- core task lifecycle rules
- core event models
- core artifact storage rules
- Android-specific behavior

## Smoke Workflow

`run_smoke_workflow(session, url)` starts an injected driver session, opens the
provided URL through the session contract, captures a screenshot artifact, and
then stops the session.

The workflow is intentionally thin. It proves wiring without embedding ticket
purchase decisions in `automation_core`.
