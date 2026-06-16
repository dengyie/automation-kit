# Example Action Batches Design

## Goal

Make built-in smoke workflows use `ActionExecutor.run_batch(...)` so example
reports include real action batch summaries.

## Problem

`ActionBatchResult` and runner `action_batch` reporting now exist, but the
built-in web and Android examples still collect actions manually. That means
the most visible first-run workflows do not demonstrate the batch execution
path or expose skipped-action summaries.

## Proposed Shape

- Use `ActionExecutor` and `ActionBatch` inside the Damai web smoke workflow.
- Use `ActionExecutor` and `ActionBatch` inside the Damai Android smoke
  workflow.
- Preserve existing action names:
  - web: `open`
  - Android: `launch_app`
- Keep artifact capture outside the batch for now.
- Return `batch_result` alongside the existing flat `actions` list.

## Boundaries

- No changes to `automation_core.actions` semantics.
- No new adapter aliases.
- No live browser or device requirement in tests.
- No selectors, URLs, package names, or business flow in `automation_core`.

## Testing Strategy

- Update web example tests to assert `batch_result`.
- Update Android example tests to assert `batch_result`.
- Update CLI JSON tests to assert `action_batch` for built-in dry workflows.
- Run full suite and production review scripts before committing.
