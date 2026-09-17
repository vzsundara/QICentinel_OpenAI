# QI Sentinel: Problem Definition

## Executive summary

Healthcare quality reporting depends on measure logic, value sets, pipeline configuration, access controls, and lineage records that change throughout the year. Assurance that these components still match approved specifications and governance policy is often manual and concentrated near submission deadlines. Drift is therefore discovered late, and audit evidence is reconstructed after the fact.

QI Sentinel reframes measure integrity as a continuously monitored property of the platform. It detects drift early, prepares low-risk corrections behind a deterministic policy gate, escalates changes that require domain judgment, and records evidence when the finding occurs.

## Problem statement

Quality Analytics, Compliance, Security, and Data Engineering lack one repeatable control loop that answers all of the following:

- Does implemented measure logic still conform to the approved specification snapshot?
- Are referenced value sets current and explicitly versioned?
- Do reporting-layer access and masking policies remain attached to protected fields?
- Are sensitive fields prevented from entering application logs?
- Can every reported measure be traced from its run through its sources to its output?
- Is there contemporaneous evidence showing what was inspected, found, changed, tested, and approved?

Without that loop, analysts repeatedly verify unchanged logic, real drift can remain hidden until a rate changes, and audit preparation becomes a manual reconstruction exercise. Errors can also create financial exposure through incorrect quality results and delayed remediation.

## Primary users and owners

| User or owner | Need |
| --- | --- |
| Quality Analytics | Accurate measure logic, actionable semantic-drift analysis, and control over population-changing fixes |
| Compliance and Audit | Traceable, complete, and tamper-evident evidence generated when a finding occurs |
| Security and Data Governance | Continuous validation of masking, logging, access, and lineage controls |
| Data Engineering | Clear evidence and ownership for pipeline or feed defects |
| Software Engineering | Reviewable patches, reproducible tests, bounded permissions, and low-noise findings |

## Proposed outcome

The proof of concept demonstrates one monitoring cycle over a synthetic control plane. It collects and hashes inputs, executes four deterministic scanners, uses Codex for bounded analysis and writing, evaluates every proposed action against policy, creates one reviewable pull request for approved fixes, creates two escalations, and emits a verifiable evidence pack.

The four required findings are:

1. `QI-MASK-001`: a masking policy is missing from the PHI-tagged synthetic column `RPT.MEMBER_MEASURE.DOB`. Restore the last approved policy.
2. `QI-LOG-001`: synthetic member identifiers appear in an application log. Add and verify a redaction filter.
3. `QI-SEM-001`: a synthetic CBP measure pins an outdated value-set version and omits an approved denominator exclusion. Escalate because both affect population semantics.
4. `QI-LIN-001`: the synthetic COL measure lacks a required lineage record. Escalate because historical evidence cannot be invented.

An optional fifth finding, `QI-FEED-001`, represents a missing supplemental clinical feed manifest and is intentionally outside the minimum demo path.

## Success criteria

| ID | Criterion | Target |
| --- | --- | --- |
| S1 | Seeded defects found in one repeatable run | 4 of 4 |
| S2 | Findings against clean baseline fixtures | 0 |
| S3 | Automatically remediated findings | Exactly 2 |
| S4 | Escalations containing root cause, impact, evidence, owner, and next action | 2 of 2 |
| S5 | Unit, policy, regression, and integrity tests after remediation | Pass |
| S6 | Evidence-pack verification through `sentinel verify` | Pass |
| S7 | API keys or synthetic sensitive values in published artifacts | None |
| S8 | Duplicate PRs or escalations after an identical second run | None |

## Scope

### In scope

- Synthetic measure logic and synthetic specification snapshots
- Mock Databricks, Snowflake, logging, and lineage artifacts
- Four deterministic scanners
- Codex-assisted analysis, explanation, and patch drafting
- Deterministic policy evaluation and reviewable pull-request creation
- Escalation records and a hashed JSON plus HTML evidence pack
- Local CLI execution and a hardened GitHub Actions demonstration
- A recorded fallback run and a five-minute pitch narrative

### Out of scope

- Real PHI or member-identifiable data
- Licensed HEDIS or CMS specification text
- Production Databricks, Snowflake, or data-lake connectivity
- Clinical decision support or a full measure-calculation engine
- Automatic merge, deployment, or production mutation
- Multi-tenancy, Docker, and a dashboard in the minimum build
- Claims that the tool certifies HEDIS, CMS, HIPAA, or audit compliance

## Constraints and safeguards

- The PoC operates on repository files, configuration, exported metadata, and synthetic logs only.
- All specification inputs are versioned and checksummed.
- The agent does not receive raw sensitive log lines; collection redacts before model analysis.
- Policy decisions are deterministic and cannot be changed by model output.
- Measure-semantic changes, evidence attestation, and access-grant widening are hard-blocked from automatic application.
- Automated changes are limited to allowlisted files and commands and always require human review.
- CI uses trusted triggers and separates read-only scanning from write-scoped remediation.
- The agent has no internet access during the demonstration.

## Working assumptions and open questions

| ID | Question | Working assumption |
| --- | --- | --- |
| Q1 | Which measure families and compute platform should the pilot use? | Synthetic CBP and COL logic modeled as Databricks workloads |
| Q2 | Are final rates computed in Snowflake or only reported there? | Snowflake is the reporting and submission layer |
| Q3 | How much build capacity is available? | Approximately 24 hours across two or three people |
| Q4 | What are the submission portal limits? | Unknown; maintain a 500-character summary |
| Q5 | Who is the sponsor and which recent finding matters most? | Sponsor not yet confirmed; masking drift is the headline case |
| Q6 | Is a project-scoped API key available for CI? | Yes, stored only as a GitHub Actions secret |
| Q7 | May the hackathon repository remain public? | Must be confirmed before code or secrets are pushed |
| Q8 | What is the supported unattended Codex authentication flow? | Verify during the Codex integration phase |
