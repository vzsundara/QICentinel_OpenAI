# QI Sentinel Source

Phases 1 through 5 of the QI Sentinel synthetic quality-measure compliance proof of concept: scaffold, deterministic scanners, bounded Codex analysis, policy-controlled actions, and verifiable evidence with least-privilege CI configuration.

The checked-in `mock-platform/` directory contains four intentional synthetic defects. Matching clean representations are under `tests/fixtures/baseline/mock-platform/`. Four deterministic scanners produce validated canonical JSON with stable finding fingerprints. The optional Codex adapter enriches only `QI-SEM-001`; code keeps its rule ID and `escalate` disposition authoritative. The policy workflow evaluates all six conditions, applies only the two code-owned allowlisted fixes in enforce mode, holds all changes in observe mode, and records complete semantic and lineage escalations. Phase 5 emits canonical JSON plus derived HTML, checks publication safety, and verifies every covered hash.

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
sentinel evidence --mode observe --run-id local-demo
sentinel verify artifacts/local-demo
```

`sentinel scan` prints canonical findings JSON or writes it with `--output`. `sentinel remediate --mode observe` runs the gate and tests without changing remediation targets. Enforce mode is the policy default; it updates only the two allowlisted synthetic files after staged tests pass, then writes a local review payload and idempotency state under `artifacts/phase4/`. `sentinel evidence` defaults to observe mode and creates an immutable pack under `artifacts/<run-id>/`; `sentinel verify` detects changed or missing covered sources, evidence, or HTML. Local commands do not contact GitHub, push, merge, or deploy.

## Evidence and CI

`evidence.json` is the canonical record. It includes honest runtime and repository provenance, sanitized findings and actions, source and component hashes, test results, explicit unavailable facts, and integrity hashes. `index.html` is deterministically derived for reviewer readability. Both files pass credential and raw synthetic-identifier checks before publication.

The repository workflow is located at `../../.github/workflows/qi-sentinel.yml`, because GitHub discovers workflows only from the repository-level `.github/workflows/` directory. Scheduled and manual scan runs are read-only. Remediation and Codex jobs are manual, owning-repository-only paths. Live workflow and secret verification remain pending until run by the repository owner.

## Codex authentication

Local SDK execution uses the authentication available to the bundled Codex runtime. Check it without exposing credentials using the bundled CLI's `login status` command. A live read-only Phase 3 smoke test succeeded through the cached ChatGPT login on 17 September 2026. For unattended execution, use a project-scoped API key supplied only to the Codex action through the `OPENAI_API_KEY` Actions secret; never put a key value in YAML, prompts, logs, or evidence. The optional CI job remains disabled unless explicitly selected during a trusted manual run.

The integration decision and managed-environment constraints are recorded in `docs/adr/0001-official-codex-python-sdk.md`.
