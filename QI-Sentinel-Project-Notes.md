# QI Sentinel — Project Notes and Decision Log

Last updated: 17 Sep 2026. Covers everything decided while producing the design documents, so work can continue on any machine without the original chat.

---

## 1. Folder contents

| File | What it is | Status |
|---|---|---|
| `QI-Sentinel-PoC-Handoff.md` | Original handoff prompt: hackathon context, idea, first scope | Source input, unchanged |
| `README.md` | Repo README from `vzsundara/QICentinel_OpenAI`, updated with the merged plan and Python stack | Modified, not committed |
| `PoC Brief - QI Sentinel.md` | Plain brief: objective, stack, requirements, deliverables, open questions | v3 (Python) |
| `QI-Sentinel-Design-Doc.html` | Full design document, PDF-printable (browser print, A4) | v3.0 |
| `Codex-Setup-Checklist.md` | Step-by-step setup for continuing on another machine | Current |
| `QI-Sentinel-Project-Notes.md` | This file: decisions, rationale, state, next steps | Current |

**Source-of-truth order when they disagree:** Design doc v3.0 → Brief v3 → README → Handoff.

**Published copy of the design doc:** https://claude.ai/artifact/6GSDvaVP2GQ9EvLgfry4Rr (private to the owner until shared; the local HTML file is identical).

---

## 2. How the documents are produced

- **Brief first, then design doc.** Write a plain Markdown brief (objective / stack / requirements / deliverables / open questions), then build the design doc from it. This is what lets the doc land in one pass.
- **Design doc format:** published web page, printable to PDF.
- **Design system:** IBM Plex Sans + IBM Plex Mono, warm paper background `#f5f3ef`, terracotta accent, light/dark aware.
- **Structure:** numbered sections (§1–§16), ADR-style decision tables, inline code snippets, static high-fidelity UI mock panels, publishing and roadmap section last.
- **Keep in sync:** any stack or scope change updates README, brief, and design doc together; bump the doc version, add a history row in §16, and record the reasoning in an ADR.
- **Location:** all QI Sentinel documents live in `D:\Work\Quest\QI Sentinel` (this folder), which is also the git working copy.

---

## 3. Decision log

### D1 — Design doc v1.0 from the handoff (Python, six findings)
- Built directly from the handoff.
- Four seeded issues split into six findings: missing lake feed, stale value-set pin, exclusion drift, Snowflake masking removed, PHI in logs, lineage gap.
- Outcome: 2 auto-fixed, 1 PR proposed, 3 escalated.
- Stack: Python with Codex CLI / Agents SDK.

### D2 — Repo checked out into this folder
- `https://github.com/vzsundara/QICentinel_OpenAI` initialised in place (folder already had files), tracking `origin/main` at commit `81f812b` ("first commit"). Repo contained only `README.md`.
- The README conflicted with v1.0: TypeScript/Node, Codex SDK + Codex GitHub Action, four seeds with a 2 auto-fix / 2 escalate split, different layout.

### D3 — Which plan was better (review outcome)
- **README was better on:** stack for a Codex-judged hackathon (Codex SDK + Action, CI-driven PRs), and guardrails (never fabricate lineage evidence, PRs only never merge, no write-permission runs on fork PRs, repo content treated as prompt-injection input, agent internet off during demo).
- **Design doc was better on:** seed choice and platform coverage.
- **README flaw found:** it auto-fixed an outdated value-set OID, but its own gate rule 2 forbids auto-fixes that change measure population semantics. A new value-set version changes numerator/denominator membership, so that seed contradicted its own policy.
- **README gap:** no Snowflake or Data Lake coverage, although the handoff promised it.

### D4 — Merged seed set (applied to all three documents)

| ID | Layer | Defect | Disposition |
|---|---|---|---|
| `QI-MASK-001` | Snowflake | Masking policy removed from PHI-tagged `RPT.MEMBER_MEASURE.DOB` | Auto-fix: restore last approved policy |
| `QI-LOG-001` | Cross-cutting | Synthetic member identifiers in application logs | Auto-fix: redaction filter |
| `QI-SEM-001` | Databricks | Stale value-set pin **and** denominator exclusion drift in the CBP measure | Escalate: measure semantics |
| `QI-LIN-001` | Cross-cutting | Lineage record missing for measure COL | Escalate: evidence cannot be invented |
| `QI-FEED-001` | Data Lake | Supplemental clinical feed manifest missing (optional fifth seed) | Escalate to data engineering |

- Demo outcome: 4 findings → 2 auto-remediated (one PR, two commits), 2 escalated, 0 auto-merges.
- Recorded as ADR-07 in the design doc.

### D5 — Design doc v2.0 (TypeScript)
- Adopted the README stack: TypeScript on Node.js, Codex SDK, Codex GitHub Action, Vitest.
- README updated: new seed table with Layer column, value-set escalation paragraph, optional fifth seed, `snowflake/` in layout, zero-findings-on-baseline criterion.

### D6 — Design doc v3.0 (switched to Python)
- Reason: the build lead is more comfortable in Python than Node.
- Verified an official Python SDK exists: `openai-codex` on PyPI (import `openai_codex`), beta, Python ≥ 3.10, installs a pinned Codex runtime (`openai-codex-cli-bin`). Pattern: `with Codex() as codex: thread = codex.thread_start(); result = thread.run(prompt); result.final_response`.
- Risk handling: pin the exact SDK version; only `src/qi_sentinel/agent/` imports it.
- Nothing else changed: seeds, policy gate, evidence pack, CI job split, safety controls all carried over.
- README, brief, and doc updated together. ADR-03 records v1.0 Python → v2.0 TypeScript → v3.0 Python.

### D7 — Build to continue on a different machine
- Readiness checked on the original machine (section 6); setup checklist written for the new machine.

---

## 4. Current architecture (quick reference)

**Loop:** collect (hash inputs + spec) → scan (4 Python scanners) → analyse (Codex: RCA, patches, narrative) → policy gate → act (1 PR, 2 escalations) → evidence pack.

**Principle:** deterministic code owns every decision (rule IDs, severity, thresholds, auto-fix eligibility, checksums, test results). Codex only reasons and writes.

**Policy gate — auto-remediation only when all six hold:**
1. Rule has `auto_fix_allowed: true`
2. Change does not alter measure population semantics
3. Confidence meets threshold (0.95)
4. Change limited to allowlisted files and commands
5. Unit, policy, regression, evidence-integrity tests pass
6. Submitted for review, never merged

`config/policy.yml` also has `mode: enforce | observe` (demo flips to observe; pilot starts there), a `never_auto_apply` hard floor (measure-semantics, evidence-attestation, access-grant-widening), and `pull_requests.merge: never`.

**Stack:** Python 3.12, `openai-codex` (pinned), pytest, `pyproject.toml` with a `sentinel` CLI (`seed`, `scan`, `remediate`, `verify`, optional `dashboard`), YAML/JSON specs and policy, GitHub Actions with the Codex Action.

**Layout:** `.github/` (workflow, `codex/prompts/monitor.md`), `config/`, `mock-platform/` (measures, pipelines, snowflake, logs, lineage), `specs/synthetic-2026/`, `src/qi_sentinel/` (agent, evidence, policy, scanners, `cli.py`), `tests/`, `artifacts/` (generated).

**CI:** scheduled or manual triggers only. `scan` job read-only; `remediate` job gets `contents: write` + `pull-requests: write`, runs only in the owning repo, narrowest Codex sandbox, Action pinned by commit SHA.

**Evidence pack:** `artifacts/<run-id>/evidence.json` + `index.html`; SHA-256 over inputs, spec, policy, artifacts, and the pack; `sentinel verify` recomputes all hashes.

**Build phases:** 1 Scaffold → 2 Scanners → 3 Codex analysis → 4 Gate and actions → 5 Evidence and CI → 6 Pitch assets. Each phase has an exit criterion (design doc §13).

**Pitch (5 min):** problem → loop → live run → PR and escalation → evidence pack → gate flip to observe → AlwaysOn Operations extension → pilot ask (one Quality Analytics owner, one measure family, observe mode).

---

## 5. Open questions

| # | Question | Working assumption |
|---|---|---|
| Q1 | Measure families; where measure logic runs today | CBP and COL in Databricks |
| Q2 | Do final rates land in Snowflake or get computed there? | Land there; reporting only |
| Q3 | Build hours and team size | ~24 hours, 2–3 people |
| Q4 | Submission portal character limits | Unknown; 500-character summary ready |
| Q5 | Compliance/security sponsor and their most painful recent finding class | None yet; masking drift is the headline seed |
| Q6 | OpenAI Platform project key available for Actions | Yes, project-scoped, stored as a secret |
| Q7 | Does company policy allow a public GitHub repo? | Yes for synthetic content; **confirm before pushing** |
| Q8 | How does `openai-codex` authenticate for unattended Actions runs? | API key; **verify in phase 3** |

---

## 6. Readiness check — original machine (17 Sep 2026)

| Item | Result |
|---|---|
| Git | 2.51.2 ✅ |
| GitHub CLI | 2.69.0, logged in as `vzsundara`, scopes `repo`, `workflow`, `read:org`, `gist` ✅ |
| Python | 3.13.0 only (no 3.12); pip 24.2; uv 0.8.22 ✅ |
| Node / npm | v22.14.0 / 10.9.2 ✅ |
| `openai-codex` on PyPI | 0.154.0, Windows x64 runtime wheel available ✅ |
| Network | `api.openai.com` and `github.com` reachable ✅ |
| Hardware | 12 logical cores, 15.7 GB RAM, 37 GB free on D: ✅ |
| Codex CLI | Not installed ❌ |
| Codex / OpenAI auth | No `OPENAI_API_KEY`, no `~/.codex` sign-in ❌ |
| Git identity | `user.name` / `user.email` not set ❌ |
| Working tree | Docs uncommitted ⚠️ |
| Repo visibility | Public (Q7 open) ⚠️ |

---

## 7. Git state

- Remote: `https://github.com/vzsundara/QICentinel_OpenAI.git`, branch `main`, last remote commit `81f812b`.
- Local changes: `README.md` modified; brief, design doc, handoff, checklist, and these notes untracked.
- **Nothing committed or pushed.** A fresh clone elsewhere will not contain these docs — copy the folder or push after Q7.

---

## 8. Next steps

1. Settle Q7 (public repo), then either push the docs or copy this folder to the new machine.
2. Follow `Codex-Setup-Checklist.md` on the new machine (tools, sign-ins, venv, smoke tests, `AGENTS.md`, Actions secret).
3. Verify Q8 during the SDK smoke test.
4. Run the Phase 1 prompt from checklist §9; review the diff against design doc §5.
5. After Phase 5, replace the static mocks in the design doc with real screenshots (v3.2) for the submission.

---

## 9. Caveats and things not yet verified

- **Codex Action:** exact action name and inputs were not pinned in the docs; confirm against current Codex GitHub Action docs and pin by commit SHA.
- **SDK in CI:** authentication without an interactive sign-in is unverified (Q8).
- **SDK stability:** `openai-codex` is beta; public APIs may change before 1.0.
- **Mock figures:** member counts, hashes, PR numbers, and confidence values in the design doc mocks are illustrative placeholders.
- **Specifications:** all spec files must be synthetic text modelled on structure only; no licensed HEDIS/CMS content.
- **Claims boundary:** QI Sentinel reports conformance to supplied synthetic rules; it does not certify HEDIS, CMS, HIPAA, or audit compliance.
