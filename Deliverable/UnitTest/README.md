# Unit Tests

This directory intentionally contains no duplicate test code.

The executable test suite is colocated with the Python source project under [`../Src/tests/`](../Src/tests/):

- Unit tests: [`../Src/tests/unit/`](../Src/tests/unit/)
- Integration tests: [`../Src/tests/integration/`](../Src/tests/integration/)
- Synthetic test fixtures: [`../Src/tests/fixtures/`](../Src/tests/fixtures/)

From `Deliverable/Src`, run the complete suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Maintaining a single test tree ensures the installed package, CLI, policy gate, fixtures, and integration workflows are tested from the same project configuration.
