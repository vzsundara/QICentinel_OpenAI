# QI Sentinel Source

Phase 1 scaffold, Phase 2 deterministic scanners, the bounded Phase 3 Codex analysis adapter, and the Phase 4 deterministic policy/action workflow for the QI Sentinel synthetic quality-measure compliance proof of concept.

The checked-in `mock-platform/` directory contains four intentional synthetic defects. Matching clean representations are under `tests/fixtures/baseline/mock-platform/`. Four deterministic scanners produce validated canonical JSON with stable finding fingerprints. The optional Codex adapter enriches only `QI-SEM-001`; code keeps its rule ID and `escalate` disposition authoritative. The Phase 4 workflow evaluates all six policy conditions, applies only the two code-owned allowlisted fixes in enforce mode, holds all changes in observe mode, and records complete semantic and lineage escalations. Evidence-pack generation remains deferred to Phase 5.

The adapter uses pinned `openai-codex==0.154.0`, a read-only sandbox, enterprise-compatible auto-review approval handling, an allowlisted and redacted context, a versioned structured-output schema, and an explicit deterministic fallback. It never reads the log fixture, applies a proposed patch, or treats repository text as instructions.

## Local commands

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
sentinel --help
sentinel seed
sentinel scan
sentinel scan --platform tests/fixtures/baseline/mock-platform
python -m pytest
sentinel remediate --mode observe
```

`sentinel scan` prints canonical findings JSON or writes it with `--output`. `sentinel remediate --mode observe` runs the gate and tests without changing remediation targets. Enforce mode is the policy default; it updates only the two allowlisted synthetic files after staged tests pass, then writes a local review payload and idempotency state under `artifacts/phase4/`. It does not create a Git branch, contact GitHub, push, merge, or deploy. The `verify` command remains a safe shell until Phase 5.

## Codex authentication

Local SDK execution uses the authentication available to the bundled Codex runtime. Check it without exposing credentials using the bundled CLI's `login status` command. A live read-only Phase 3 smoke test succeeded through the cached ChatGPT login on 17 September 2026. For unattended execution, use a project-scoped API key supplied only to the Codex invocation; never put a key in YAML, prompts, logs, or evidence. Live CI authentication remains disabled until Phase 5.

The integration decision and managed-environment constraints are recorded in `docs/adr/0001-official-codex-python-sdk.md`.
