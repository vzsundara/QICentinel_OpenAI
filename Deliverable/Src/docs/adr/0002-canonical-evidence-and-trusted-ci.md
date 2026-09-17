# ADR 0002: Canonical evidence and trusted CI

- Status: Accepted for the Phase 5 proof of concept
- Date: 2026-09-17

## Context

QI Sentinel needs a portable evidence pack that detects modification without publishing secrets or raw synthetic identifiers. CI must reproduce the local deterministic path while preventing fork content or untrusted pull-request text from receiving secrets or write permissions.

## Decision

Each evidence run writes `artifacts/<run-id>/evidence.json` and `index.html`. The JSON is canonical truth and contains source-file SHA-256 values, component hashes, an explicit hash over the canonical payload excluding only its own hash field, and the HTML hash. Verification recomputes those values, checks all covered source files, regenerates the HTML, and repeats publication-safety checks.

Evidence contains hashes and sanitized findings, not raw source contents. Missing approvals, external records, model responses, or repository metadata are recorded as unavailable rather than invented.

The repository-level GitHub workflow uses only scheduled and manual triggers. The scan job has `contents: read`. The optional owning-repository remediation job has only `contents: write` and `pull-requests: write`, does not persist checkout credentials, and prepares an unmerged local payload. The optional Codex job is manual, owning-repository-only, read-only, and receives the project API key solely through the action input.

Actions are pinned to reviewed commit SHAs:

- `actions/checkout` v7.0.1: `3d3c42e5aac5ba805825da76410c181273ba90b1`
- `actions/setup-python` v7.0.0: `5fda3b95a4ea91299a34e894583c3862153e4b97`
- `actions/upload-artifact` v7.0.1: `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`
- `openai/codex-action` v1.11: `7c168a233489ca36cb495409e8f1fba7b522bb40`

## Consequences

The local pack is reproducible from the checked-out sources and separates recorded facts from unavailable external facts. The self-hash detects modification but is not a digital signature and does not establish authorship. Live GitHub execution, secret availability, API billing, repository visibility, and actual pull-request creation remain environment-owned checks; local tests do not claim they succeeded.

## References

- [Official Codex GitHub Action documentation](https://learn.chatgpt.com/docs/github-action)
- [OpenAI Codex Action repository](https://github.com/openai/codex-action)
