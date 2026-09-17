# ADR 0001: Official Codex Python SDK

- Status: accepted
- Date: 2026-09-17

## Decision

Use the stable official `openai-codex` Python package and pin it to `0.154.0`. Keep all SDK imports under `src/qi_sentinel/agent/`.

The adapter starts an ephemeral thread rooted at the project directory with `Sandbox.read_only` and `ApprovalMode.auto_review`. The managed workspace requires the corresponding `OnRequest` policy and rejects `Never`; the read-only sandbox remains the non-overridable write boundary. The adapter passes the required JSON Schema through `Thread.run(..., output_schema=...)`. Code validates the returned JSON again and keeps the rule ID, owner, evidence sources, patch path, and `escalate` disposition outside model control.

## Verification

The official SDK documentation identifies the Python SDK as stable, requires Python 3.10 or newer, documents `pip install openai-codex`, and states that the package includes a pinned Codex CLI runtime:

- https://learn.chatgpt.com/docs/codex-sdk

Local inspection of `openai-codex==0.154.0` confirmed:

- `Codex.thread_start` accepts a model, working directory, sandbox, and approval mode;
- `Thread.run` accepts `output_schema`;
- `Sandbox.read_only` and `ApprovalMode.auto_review` are available;
- `TurnResult.final_response` carries the structured response.

The non-interactive-mode documentation says saved CLI authentication is reused, recommends API keys for automation, and recommends limiting `CODEX_API_KEY` to the Codex invocation rather than the whole job:

- https://learn.chatgpt.com/docs/non-interactive-mode

## Authentication verification

The bundled `0.154.0` CLI reported `Logged in using ChatGPT` in the owning PowerShell session. On 2026-09-17, a live SDK smoke test completed through that cached login using the production adapter, `Sandbox.read_only`, and structured output. The validated result retained `QI-SEM-001`, disposition `escalate`, and owner `quality-analytics`; it returned an optional proposed patch that remained unapplied.

The live test also confirmed two managed-environment requirements. First, the workspace permits `OnRequest` and rejects the SDK's `Never` approval policy, so the adapter uses `ApprovalMode.auto_review` while retaining the read-only sandbox as the write boundary. Second, every expected or observed source must be constrained to one exact allowlisted identifier in the runtime JSON Schema. No credential value was read or printed.

The managed test-command sandbox still cannot resolve the user's Codex home directory, so authenticated smoke testing must run outside that isolated command sandbox. Unattended CI authentication remains a Phase 5 verification item.

## Consequences

- Detection remains available without Codex.
- Model output can enrich only `QI-SEM-001` and cannot change its disposition.
- A service failure produces a labeled deterministic fallback, not fabricated model analysis.
- Model upgrades require an explicit dependency change and repeat of the Phase 3 contract tests.
