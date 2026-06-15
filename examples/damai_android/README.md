# Damai Android Example Shell

This directory will eventually show how a Damai Android workflow composes
`automation_core` primitives with an Appium-based adapter.

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

No business workflow is implemented in Phase 4.
