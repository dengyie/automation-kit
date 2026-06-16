# Example Workflow Aliases Design

## Goal

Make the built-in example workflows use the adapter action vocabulary instead
of concrete Selenium/Appium method names.

## Problem

The adapters now expose stable aliases for common actions, but the Damai smoke
examples still call raw driver method names such as `get` and `activate_app`.
That weakens the documentation story: new workflow authors see the escape hatch
before they see the recommended action vocabulary.

## Proposed Shape

- Update the web smoke workflow to call `open(url=...)`.
- Add an Appium adapter alias `launch_app(app_id=...)`.
- Update the Android smoke workflow to call `launch_app(app_id=...)`.
- Keep raw driver-method fallback behavior for specialized framework calls.

## Boundaries

- No changes to `automation_core`.
- No imports from Selenium or Appium packages.
- No business selectors or workflow expansion.
- No live browser or device requirement in default tests.

## Testing Strategy

- Update example workflow tests to expect `open` and `launch_app`.
- Add Appium adapter coverage for `launch_app`.
- Run focused example/adapter tests before the full suite.
- Run production review scripts before committing.
