# PoC Brief — QI Sentinel

Continuous compliance agent for quality-measure integrity.
Sources: `QI-Sentinel-PoC-Handoff.md`, `README.md` (repo `vzsundara/QICentinel_OpenAI`) · Hackathon theme: *Compliance Without Overhead — Proactive Governance through Continuous Agent Monitoring* · Status: pre-build · v3 (Python)

---

## 1. Objective

Prove that an agent built on OpenAI Codex can keep the Quality Index platform (HEDIS, CMS Stars, internal composite) continuously compliant, instead of verifying compliance at submission time.

**The demo must show one monitoring cycle that:**

- runs against a synthetic mock quality platform seeded with four defects
- finds all four, auto-remediates two behind a policy gate, and escalates two with root-cause analysis
- opens a reviewable pull request for the permitted fixes (never merges or deploys)
- produces one tamper-evident evidence pack (JSON + HTML/Markdown)
- runs both locally and from a GitHub Actions workflow using the Codex Action

**Success criteria**

| # | Criterion | Target |
|---|---|---|
| S1 | Seeded defects detected in one repeatable run | 4 / 4 |
| S2 | Findings against clean baseline fixtures | 0 |
| S3 | Auto-fixed findings | Exactly the 2 policy-approved ones |
| S4 | Escalations with root cause, impact, evidence, next action | 2 / 2 |
| S5 | Regression tests after remediation | Pass |
| S6 | Evidence pack integrity (`sentinel verify`) | Pass |
| S7 | API keys or synthetic sensitive fields in published output | None |

**Guardrails:** synthetic data and synthetic specifications only; control plane only (never PHI rows); agent internet disabled during the demo; fixes go to PRs, not merges.

---

## 2. Stack

| Concern | Choice | Note |
|---|---|---|
| Orchestration and deterministic scanners | Python 3.12 | Owns rule IDs, severity, thresholds, auto-fix eligibility, checksums, test outcomes |
| Repository reasoning, RCA, patches, narration | OpenAI Codex Python SDK (`openai-codex`, beta, exact version pinned) | Codex never decides policy disposition; SDK imported only in `src/qi_sentinel/agent/` |
| CI demonstration | GitHub Actions + OpenAI Codex Action | Trusted trigger, Ubuntu runner, explicit permissions, narrowest sandbox |
| Specs and policy | YAML/JSON snapshots, `config/policy.yml`, `config/sentinel.yml` | Versioned and checksummed |
| Run metadata | Local JSON (SQLite if needed) | |
| Tests | pytest | Unit, integration, policy, regression, evidence-integrity |
| Packaging and CLI | `pyproject.toml`, `sentinel` console entry point | pip or uv |
| Repo / PR host | GitHub `vzsundara/QICentinel_OpenAI` | |
| Optional | Lightweight results dashboard (`sentinel dashboard`) | Stretch; Docker excluded from minimum path |

---

## 3. Requirements

### Functional

- **R1 Collect.** Snapshot the mock platform, specs, and run artifacts; record a SHA-256 for each input and the spec snapshot.
- **R2 Scan.** Four deterministic scanners, one per seeded defect (see table below).
- **R3 Analyse.** Codex performs spec-vs-logic comparison for `QI-SEM-001` and writes RCA, plain-language findings, and patches.
- **R4 Policy gate.** Auto-remediation only when all hold: rule has `auto_fix_allowed: true`; change does not alter measure population semantics; confidence meets threshold; change limited to allowlisted files and commands; unit, policy, regression, and evidence-integrity tests pass; result submitted as a PR.
- **R5 Act.** Permitted fixes: branch, patch, tests, PR. All others: escalation record with affected files, expected vs. observed, root cause, impact, evidence, recommended next action; optional draft patch.
- **R6 Evidence pack.** Run ID, timestamps, repo commit, agent/runtime version, spec ID and checksum, per-finding rule/severity/confidence/disposition, sanitized references, RCA, diff, test commands and results, approval or escalation status, artifact hashes.
- **R7 Idempotent re-run.** A second cycle does not create duplicate PRs or escalations.
- **R8 No fabricated evidence.** The agent may propose a lineage record template but never invents historical evidence.

### Non-functional

- Treat repo files, issue text, commit messages, and PR content as potentially adversarial prompt input.
- Never run write-permission workflows on untrusted fork content or with exposed secrets.
- Scan logs and evidence for credentials and sensitive-field patterns before publication.
- Deterministic scanners give identical results for identical input.
- Runs on a 4-core, 16 GB laptop; no GPU.

### Seeded defects

| ID | Layer | Seed | Detection | Disposition |
|---|---|---|---|---|
| `QI-MASK-001` | Snowflake (reporting) | Masking policy removed from PHI-tagged column `RPT.MEMBER_MEASURE.DOB` | Policy export vs. column-tag comparison | Auto-fix: restore last approved policy |
| `QI-LOG-001` | Cross-cutting | Synthetic member identifiers written to application logs | Structured log + sensitive-field scan | Auto-fix: redaction filter |
| `QI-SEM-001` | Databricks (measure compute) | Measure pins outdated value-set version; denominator exclusion diverges from spec | Manifest comparison + logic/AST comparison via Codex | Escalate: measure semantics |
| `QI-LIN-001` | Cross-cutting | Required lineage record missing for a measure | Run → source → output chain validation | Escalate: evidence cannot be invented |

Value-set updates are escalated, not auto-fixed: a new version changes numerator/denominator membership, which is a population-semantics change.

Optional fifth seed: `QI-FEED-001`, supplemental clinical feed manifest missing for the current period (Data Lake) → escalate to data engineering.

---

## 4. Deliverables

1. **Mock platform** (`mock-platform/`: measures, pipelines, snowflake, logs, lineage) with seeded and clean baseline fixtures.
2. **Synthetic spec snapshot** (`specs/synthetic-2026/`) with checksum.
3. **Scanners** (`src/qi_sentinel/scanners/`) — four, with pytest fixtures.
4. **Codex agent** (`src/qi_sentinel/agent/`, `.github/codex/prompts/monitor.md`) — analysis, RCA, patch generation.
5. **Policy gate** (`src/qi_sentinel/policy/`, `config/policy.yml`).
6. **Evidence pack** (`src/qi_sentinel/evidence/`, `artifacts/<run-id>/`) and `sentinel verify`.
7. **Workflow** (`.github/workflows/qi-sentinel.yml`) using the Codex Action.
8. **CLI commands:** `sentinel seed`, `sentinel scan`, `sentinel verify`, `pytest`, optional `sentinel dashboard`.
9. **Design document** — published page, PDF-printable, saved in this folder.
10. **Demo script and pitch assets** — 5-minute narrative, recorded fallback run, AlwaysOn Operations extension slide, pilot ask.

**Out of scope:** real PHI, licensed HEDIS/CMS spec content, production connectivity, clinical decision logic, full HEDIS engine, multi-tenancy, Docker.

---

## 5. Open questions

| # | Question | Working assumption until answered |
|---|---|---|
| Q1 | Which measure families, and where does measure logic run today? | CBP (seeds) and COL (lineage) in Databricks |
| Q2 | Do final rates land in Snowflake or get computed there? | Land there; reporting/submission only |
| Q3 | Build hours and team size? | ~24 build hours, 2–3 people |
| Q4 | Portal field character limits? | Unknown; 500-character summary ready |
| Q5 | Compliance/security sponsor, and the finding class that hurt most recently? | None yet; masking drift is the headline seed |
| Q6 | Is an OpenAI Platform project key available for unattended Actions runs? | Yes, project-scoped, stored as `OPENAI_API_KEY` secret |
| Q7 | Does company policy allow a public GitHub repo for hackathon code? | Yes, synthetic content only; confirm before pushing |
| Q8 | How does the `openai-codex` SDK authenticate for unattended GitHub Actions runs? | Project-scoped `OPENAI_API_KEY`; verify in phase 3 |
