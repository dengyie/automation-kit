# Element Lookup Session Contract Design

## Goal

Align the core `ElementLookupSession` protocol with the real Selenium and
Appium adapter lookup shape.

## Problem

`automation_core.drivers.ElementLookupSession` currently declares:

```python
def find_element(self, selector: str) -> ElementHandle:
```

But the concrete adapters already resolve elements with a driver-style
signature that includes the lookup strategy:

```python
find_element(by, selector)
```

This mismatch makes the core contract misleading. It suggests that element
lookups only need a selector string, while the actual adapters need both a
strategy and a selector. New adapter authors can easily implement the wrong
shape if they follow the core protocol literally.

## Proposed Shape

- Update `ElementLookupSession.find_element(...)` to accept an optional
  lookup strategy and a selector:

  ```python
  def find_element(
      self,
      by: Optional[str],
      selector: str,
  ) -> ElementHandle:
  ```

- Keep the protocol business-agnostic.
- Keep the existing Selenium/Appium adapter behavior unchanged.
- Update tests and import coverage to reflect the real contract.

## Architecture

The change belongs in `automation_core.drivers` because the protocol is part of
the core boundary. The adapters already depend on this boundary and should stay
unchanged in behavior; the contract simply needs to describe them accurately.

## Testing Strategy

- Add a regression test proving `ElementLookupSession` accepts the two-argument
  lookup shape.
- Update the driver contract tests to use the matching fake lookup session
  signature.
- Keep Selenium and Appium adapter tests green without behavior changes.
- Run focused driver/import tests and the full suite.
