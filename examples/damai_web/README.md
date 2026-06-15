# Damai Web Example Shell

This directory will eventually show how a Damai web workflow composes
`automation_core` primitives with a Selenium-based adapter.

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

No business workflow is implemented in Phase 4.
