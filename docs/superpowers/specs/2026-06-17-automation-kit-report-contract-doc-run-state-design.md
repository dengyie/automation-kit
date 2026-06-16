# Report Contract Documentation Run State Design

## Goal

Document `run_state` in the workflow authoring guide's runner report field list.

## Problem

Runner reports already include `run_state`, and the machine-readable schema
requires it. The workflow authoring guide's "Report Contract" field list omits
`run_state`, which makes the human-facing contract inconsistent with the code
and JSON schema.

That inconsistency matters for workflow authors and schedulers that use
`docs/adding-a-workflow.md` as the extension guide.

## Proposed Shape

Add `run_state` to the `docs/adding-a-workflow.md` report field list directly
after `run_id`, matching the report shape and schema.

Keep the change documentation-only. Do not change the runner report schema,
`build_report(...)`, or `automation_core`.

## Testing Strategy

- Add a documentation regression test that parses the "JSON reports currently
  include" bullet list.
- Assert the documented fields match a sample report's top-level keys.
- Run the focused documentation/schema test, then the full suite.
- Run production review scripts and manually verify no report runtime contract
  changed.
