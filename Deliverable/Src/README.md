# QI Sentinel Source

Phase 1 scaffold and Phase 2 deterministic scanners for the QI Sentinel synthetic quality-measure compliance proof of concept.

The checked-in `mock-platform/` directory contains four intentional synthetic defects. Matching clean representations are under `tests/fixtures/baseline/mock-platform/`. Four deterministic scanners produce validated canonical JSON with stable finding fingerprints. Codex integration, policy execution, remediation, and evidence-pack generation remain deferred to later phases.

## Local commands

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
sentinel --help
sentinel seed
sentinel scan
sentinel scan --platform tests/fixtures/baseline/mock-platform
python -m pytest
```

`sentinel scan` prints canonical findings JSON or writes it with `--output`. The `remediate` and `verify` commands remain safe shells that return a nonzero status until their planned phases are implemented.
