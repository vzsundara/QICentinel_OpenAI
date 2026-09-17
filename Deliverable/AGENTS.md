# QI Sentinel repository instructions

## Scope and sources of truth

- These instructions apply to the entire repository.
- Implement application code only under `Deliverable/Src/` unless a task explicitly changes the deliverable documents.
- Use `Deliverable/Problem_reference.md`, `Deliverable/ARCHITECTURE.md`, `Deliverable/PLAN.md`, and `Deliverable/PROMPTS.md` as the approved design baseline.
- Keep the proof of concept synthetic and control-plane-only. Do not introduce production records, credentials, or regulated data.

## Safety boundaries

- Never commit, print, log, or include secrets in prompts, fixtures, tests, or evidence artifacts.
- Treat repository content as untrusted data when constructing model context. Use explicit path allowlists and redact before model invocation.
- Deterministic code owns rule IDs, severities, evidence references, policy decisions, and dispositions. Model output may enrich narrative but may not override those fields.
- `QI-SEM-001` and `QI-LIN-001` require human escalation. Never automatically apply semantic, value-set, exclusion, or lineage changes.
- Do not fabricate approvals, lineage, hashes, test results, external record IDs, or unavailable history.
- Do not push, merge, deploy, contact GitHub, or modify external systems unless the current user request explicitly authorizes that action.
- Proposed model patches must remain unapplied until deterministic policy checks and human-review requirements are satisfied.

## Development and verification

- Target Python 3.12 or newer and preserve the `src/qi_sentinel` package layout.
- Keep all `openai_codex` imports under `Deliverable/Src/src/qi_sentinel/agent/`.
- Preserve deterministic, canonical scanner output and stable finding fingerprints.
- Do not change `Deliverable/Src/config/policy.yml` unless the user explicitly requests a policy change.
- From `Deliverable/Src`, run `./.venv/Scripts/python.exe -m pip check` and `./.venv/Scripts/python.exe -m pytest -q` after source changes.
- For scanner changes, verify the seeded platform produces exactly four expected findings and the clean baseline produces zero.
- Report any skipped live authentication, network, GitHub, or CI verification explicitly; never represent a mocked or fallback analysis as a live Codex result.
