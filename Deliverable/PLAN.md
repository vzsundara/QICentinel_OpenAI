# QI Sentinel Implementation Plan

## Delivery objective

Build a reliable hackathon PoC in which one command detects four synthetic defects, prepares exactly two policy-approved fixes in one reviewable pull request, creates two actionable escalations, and produces a verifiable evidence pack. The minimum path is prioritized over live connectors and dashboard polish.

## Plan status

**Current milestone:** Phase 2 deterministic scanners complete locally; Phase 0 external decisions remain  
**Assessment date:** 17 September 2026  
**Overall state:** Phases 1 and 2 implemented and tested under `Deliverable/Src/`

| Phase | Status | Depends on | Completion evidence |
| --- | --- | --- | --- |
| 0. Readiness and decisions | In progress | None | Readiness checklist passes and decisions are recorded |
| 1. Scaffold | Complete locally | Phase 0 | Installable package, working CLI shell, and inspectable fixtures |
| 2. Deterministic scanners | Complete locally | Phase 1 | Four seeded findings, zero baseline findings, deterministic JSON |
| 3. Codex analysis | Not started | Phase 2 | Three consecutive schema-valid semantic analyses |
| 4. Policy gate and actions | Not started | Phases 2–3 | Two fixes, two escalations, and idempotent rerun |
| 5. Evidence and CI | Not started | Phase 4 | Verified evidence pack and green least-privilege workflow |
| 6. Demo and pitch | Not started | Phase 5 | Two successful five-minute rehearsals and reviewer feedback |

### Current repository baseline

| Item | Observed state | Required action |
| --- | --- | --- |
| Git | Installed; current branch is `main` | Keep implementation work reviewable on a feature branch |
| Working tree | `Deliverable/` is untracked | Review and commit the agreed document baseline before implementation |
| Python | A Python 3.14.5 virtual environment exists at `Deliverable/Src/.venv` | Install or select Python 3.12 before final CI parity testing |
| Codex CLI | `0.154.0-alpha.6.2` is installed | Verify authentication with a read-only smoke test |
| GitHub CLI | Not installed or not on `PATH` | Install and authenticate before PR or Actions work |
| Repository instructions | `AGENTS.md` is absent | Add the agreed synthetic-data and safety rules |
| Ignore rules | `Deliverable/Src/.gitignore` excludes the local environment, credentials, caches, and artifacts | Add broader repository rules later only if needed |
| Application and scanners | Implemented under `Deliverable/Src/` | Review Phase 2 output before beginning Codex integration |

Status in this table is observational, not proof of authentication, authorization, or external-service availability.

## Definition of done

The PoC is complete when all of the following are demonstrated from a clean checkout:

- `sentinel scan` reports all four seeded findings and none against the clean baseline.
- Only `QI-MASK-001` and `QI-LOG-001` are eligible for remediation.
- `QI-SEM-001` and `QI-LIN-001` produce complete escalation records.
- An identical second run creates no duplicate PR or escalation.
- All automated changes pass unit, policy, regression, and integrity tests.
- `sentinel verify` validates the generated evidence pack.
- CI reproduces the local result using trusted triggers and least privilege.
- Published output contains no secrets or synthetic sensitive values.
- A five-minute demonstration can be completed twice without intervention.

## Phase 0 — Readiness and decisions

### Work

- [ ] Review and accept the five documents under `Deliverable/` as the implementation baseline.
- [ ] Confirm whether the repository may remain public; make it private before adding secrets if approval is absent.
- [ ] Install or select Python 3.12 and confirm `python --version` from the intended virtual environment.
- [x] Confirm Git is installed.
- [ ] Install GitHub CLI, authenticate, and verify the required repository and workflow scopes.
- [x] Confirm Codex CLI is installed.
- [ ] Verify Codex authentication with a read-only repository-summary prompt.
- [ ] Add `AGENTS.md` containing the synthetic-only, no-fabrication, policy, and no-merge rules.
- [ ] Add `.gitignore` entries for `.venv/`, `.env`, `artifacts/`, `__pycache__/`, `.pytest_cache/`, and coverage output.
- [ ] Commit the accepted documentation and readiness files as a clean baseline.
- [ ] Verify the currently supported Codex SDK package, version, authentication method, and GitHub Action interface against official documentation.
- [ ] Record final answers for open questions Q1 through Q8 or retain explicit working assumptions.

### Exit criteria

- [ ] Clean committed baseline and working Python 3.12 environment.
- [ ] Repository visibility decision recorded.
- [ ] Read-only Codex smoke test succeeds.
- [ ] GitHub CLI authentication succeeds.
- [ ] Repository instructions and ignore rules are present.
- [ ] No credentials exist in tracked files.
- [ ] Phase 1 may proceed without unresolved safety or access blockers.

### Decisions required before Phase 1

| Decision | Owner | Due | Default if unanswered |
| --- | --- | --- | --- |
| Approve the deliverable documents as the build baseline | Build lead | Before first implementation commit | Continue review; do not scaffold |
| Public versus private repository | Project or security owner | Before adding code or secrets | Treat as private-required |
| Available build time and team size | Build lead | Before Phase 1 scope lock | Plan for 24 hours and two people |
| Pilot measure family and platform assumptions | Quality Analytics owner | Before replacing synthetic fixtures | Retain synthetic CBP/COL and Databricks model |
| Supported unattended Codex authentication | Technical lead | During Phase 3, before CI | Keep model-dependent CI disabled |

### Immediate execution sequence

1. Review this deliverable pack and resolve any scope changes.
2. Decide repository visibility.
3. Establish Python 3.12, GitHub CLI, `AGENTS.md`, and `.gitignore`.
4. Run read-only authentication and credential-hygiene checks.
5. Commit the clean documentation baseline.
6. Create a Phase 1 feature branch and execute Prompt 1 from [PROMPTS.md](PROMPTS.md).

## Phase 1 — Scaffold

**Status:** Complete locally on 17 September 2026. The virtual environment uses Python 3.14.5 because Python 3.12 is not installed on this machine; the package declares Python 3.12 or newer.

### Work

- [x] Create `pyproject.toml` and the `src/qi_sentinel/` package.
- [x] Add the `sentinel` CLI with `seed`, `scan`, `remediate`, and `verify` command shells.
- [x] Create `config/policy.yml` and `config/sentinel.yml`.
- [x] Add `specs/synthetic-2026/` with an original synthetic measure specification and value-set manifest.
- [x] Create the mock platform with the four agreed defects.
- [x] Add clean baseline fixtures and `tests/fixtures/seeds.json`.
- [x] Document each seed, expected detection, and allowed disposition.

### Exit criteria

- [x] The package installs locally in editable mode.
- [x] `sentinel --help` and `sentinel seed` run successfully.
- [x] Every seed is verifiable by inspection and has a clean counterpart.
- [x] Phase 1 completed before scanner or model integration began.

## Phase 2 — Deterministic scanners

**Status:** Complete locally on 17 September 2026. The suite contains 26 passing tests and the CLI produces four seeded findings, zero clean-baseline findings, and byte-for-byte identical repeated output.

### Work

- [x] Define and validate a shared finding schema.
- [x] Implement masking-policy, sensitive-log, measure-semantic, and lineage scanners.
- [x] Make scan ordering and output serialization deterministic.
- [x] Add unit tests per rule and integration tests over seeded and baseline fixtures.
- [x] Include stable finding fingerprints.

### Exit criteria

- [x] Seeded fixtures produce exactly four findings with the expected rule IDs.
- [x] Clean fixtures produce zero findings.
- [x] Repeated scans produce equivalent canonical output.
- [x] No Codex call is needed to achieve detection results.

## Phase 3 — Codex analysis

### Work

- Pin the supported Codex integration version and isolate it under `src/qi_sentinel/agent/`.
- Create the versioned monitoring prompt from [PROMPTS.md](PROMPTS.md).
- Build an allowlisted and redacted context bundle for `QI-SEM-001` and narrative enrichment.
- Validate structured output and reject unknown rules, unsupported actions, or instruction-following from repository content.
- Capture prompt, input, and response hashes without exposing secrets or sensitive values.
- Provide a deterministic fallback narrative for an unavailable model so detection and evidence can still complete honestly.

### Exit criteria

- `QI-SEM-001` returns schema-valid RCA on three consecutive test runs.
- Disposition remains `escalate` regardless of model wording.
- Raw sensitive log values never reach the model.
- Authentication behavior for unattended execution is documented.

## Phase 4 — Policy gate and actions

### Work

- Implement all six gate checks and the non-overridable hard floor.
- Support `enforce` and `observe` modes.
- Implement allowlisted patch application, branch naming, tests, and PR-body generation.
- Combine the two permitted fixes into one reviewable PR.
- Generate escalation records for semantic drift and missing lineage.
- Use fingerprints to find and update existing open records.
- Ensure no path merges or deploys a change.

### Exit criteria

- Enforce mode yields one PR containing two fixes and two escalation records.
- Observe mode yields the same findings but no applied changes.
- A second identical run creates no duplicate records.
- Any failed gate condition changes the disposition to escalation or held.

## Phase 5 — Evidence and CI

### Work

- Generate canonical `evidence.json` and reviewer-facing `index.html`.
- Hash all inputs, spec, policy, prompts, results, tests, and artifacts.
- Implement `sentinel verify` with clear tamper and missing-file failures.
- Add secret and synthetic-sensitive-pattern scans before publication.
- Create separate GitHub Actions scan and remediation jobs.
- Restrict triggers and permissions; pin third-party actions and the Codex action.
- Upload the evidence pack as a workflow artifact.

### Exit criteria

- A modified artifact causes `sentinel verify` to fail.
- Local and CI results agree.
- The workflow completes green with the intended permissions.
- A local five-minute rehearsal succeeds twice.

## Phase 6 — Demo and pitch assets

### Work

- Capture a known-good run, PR, escalations, and evidence pack.
- Prepare a recorded fallback for network or API failure.
- Replace design-document mockups with real screenshots where appropriate.
- Prepare the five-minute narrative and a concise submission summary.
- Ask one Quality Analytics reviewer to validate the seed realism and escalation usefulness.
- Frame the pilot ask: one owner, one approved measure family, and observe mode first.

### Exit criteria

- The demo is understandable without repository knowledge.
- Every screen shown contains only synthetic information.
- One domain reviewer has provided feedback.
- Live and recorded paths are ready.

## Five-minute demonstration

| Time | Narrative | Screen |
| --- | --- | --- |
| 0:00 | Measure integrity is currently checked too late | Problem statement |
| 0:40 | QI Sentinel makes integrity continuously monitored | Architecture loop |
| 1:20 | One cycle finds four defects across compute, reporting, logs, and lineage | CLI run |
| 2:30 | Two low-risk fixes are proposed; semantic drift remains human-owned | PR and escalation |
| 3:20 | Evidence exists immediately and can be independently verified | Evidence report and `sentinel verify` |
| 3:50 | Observe mode demonstrates bounded autonomy | Policy flip and rerun |
| 4:20 | The same loop can extend to operational exceptions | Extension slide |
| 4:40 | Begin with one measure family and one owner | Pilot ask |

## Work allocation for a small team

| Stream | Primary responsibility |
| --- | --- |
| Core platform | CLI, schemas, collectors, scanners, and fixtures |
| Controls and automation | Policy gate, action executor, CI, and security checks |
| Agent and experience | Codex adapter, prompts, evidence narrative, demo, and pitch assets |

Keep interfaces small so streams can work independently: findings schema, policy decision schema, action record schema, and evidence schema should be agreed before parallel implementation.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Codex analysis is unstable during the demo | High | Deterministic detection, schema validation, three-run test, and recorded fallback |
| SDK or Action interface changes | Medium | Verify current official docs, pin versions or commit SHAs, and isolate integration |
| Network or API failure | High | Preserve a verified pre-generated run and recorded demonstration |
| Public repository conflicts with company policy | Medium | Resolve visibility before code or secrets are pushed |
| Scope expands to dashboards or live connectors | Medium | Require Phase 5 exit before accepting stretch work |
| Seeds do not reflect sponsor priorities | Medium | Review with a Quality Analytics owner and adjust only through documented decisions |
| Evidence accidentally contains credentials or sensitive patterns | High | Redact at collection, scan before publication, and test negative cases |

## Change control

- Preserve the four required rule IDs and the two-fix/two-escalation outcome unless an explicit decision changes scope.
- Treat `config/policy.yml` as a governed artifact; changes require review and appear in evidence hashes.
- Record significant design changes as numbered architecture decisions.
- Update the problem, architecture, plan, prompts, and root documentation together when a change affects more than one concern.
- Never rewrite or fabricate historical evidence to make a demonstration pass.
