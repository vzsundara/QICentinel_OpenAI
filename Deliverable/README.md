# QI Sentinel Deliverable Pack

QI Sentinel is a proof of concept for continuously monitoring the integrity of a synthetic healthcare quality-measure platform. It detects configuration and specification drift, applies only policy-approved low-risk fixes, escalates semantic or attestable changes to people, and produces a verifiable evidence pack.

This folder is the concise, implementation-ready version of the project material in the repository root. The original documents remain available as background and decision history.

## Document map

| Document | Purpose |
| --- | --- |
| [Problem_reference.md](Problem_reference.md) | Detailed business problem, users, scope, target outcome, and success measures |
| [PROBLEM_Final.md](PROBLEM_Final.md) | Evaluator-ready final theme and idea submission |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical design, agent loop, controls, repository structure, and architectural decisions |
| [PLAN.md](PLAN.md) | Phased implementation plan, exit criteria, risks, and demo sequence |
| [PROMPTS.md](PROMPTS.md) | Reusable Codex prompts and structured-output expectations for each build phase |

## Target demonstration

One repeatable monitoring cycle runs against a synthetic platform containing four seeded defects:

| Finding | Area | Expected disposition |
| --- | --- | --- |
| `QI-MASK-001` | Snowflake masking policy | Auto-fix through a reviewable pull request |
| `QI-LOG-001` | Sensitive fields in application logs | Auto-fix through the same pull request |
| `QI-SEM-001` | Measure logic and value-set drift | Escalate to Quality Analytics |
| `QI-LIN-001` | Missing lineage record | Escalate for owner attestation |

The expected result is four findings, exactly two policy-approved remediations, two analyst-ready escalations, passing tests, and one tamper-evident evidence pack. QI Sentinel never merges or deploys a generated change.

## Technology baseline

- Python 3.12 with a `sentinel` command-line interface
- Deterministic Python scanners and policy evaluation
- A pinned Codex integration isolated under `src/qi_sentinel/agent/`
- YAML and JSON for policy, configuration, specifications, and findings
- pytest for unit, integration, policy, regression, and evidence-integrity tests
- GitHub Actions with separate read-only scan and write-scoped remediation jobs
- Synthetic inputs and exported metadata only; no production systems or PHI

## Operating principles

1. Deterministic code owns rule IDs, severity, thresholds, remediation eligibility, checksums, and test results.
2. Codex supplies repository-level reasoning, root-cause analysis, patch drafts, and plain-language explanations.
3. Every automated change must pass all policy-gate conditions and be submitted for human review.
4. Changes affecting measure population semantics or requiring historical attestation are never automatically applied.
5. Evidence is generated at detection time and must be independently verifiable.
6. Repository content is treated as untrusted input; model output cannot override policy.

## Current status

Phases 1 and 2 are implemented under [`Src/`](Src/). The installable CLI now runs four deterministic scanners, emits validated canonical findings with stable fingerprints, reports four findings on the seeded platform and zero on the clean baseline, and is covered by unit and integration tests. Codex analysis begins in Phase 3 of [PLAN.md](PLAN.md).

Before code or secrets are pushed, confirm whether the repository may remain public. Also verify the exact Codex SDK authentication path and GitHub Action interface against current official documentation during the relevant implementation phases.

## Source material

These deliverables consolidate the following root-level documents:

- `QI-Sentinel-Design-Doc.html` — primary design source, version 3.0
- `PoC Brief - QI Sentinel.md` — requirements and agreed scope
- `README.md` — repository-facing overview and safeguards
- `QI-Sentinel-Project-Notes.md` — decisions, project state, and open questions
- `QI-Sentinel-PoC-Handoff.md` — original concept and hackathon context
- `Codex-Setup-Checklist.md` — environment and readiness steps

If the source documents disagree, use this precedence: design document v3.0, PoC brief v3, root README, then the original handoff. Once implementation begins, accepted changes should be reflected in this deliverable pack and recorded as architecture decisions.
