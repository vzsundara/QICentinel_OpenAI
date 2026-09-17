---
associate: "Sundara Mahalingam Andavar"
case_study: "QI Sentinel"
---

# Hackathon Theme & Idea

## THEME
Compliance Without Overhead — Proactive Governance through Continuous Agent Monitoring.

## IDEA
QI Sentinel is a continuous compliance agent for healthcare quality-measure integrity. It helps Quality Analytics, Compliance, Security, and engineering teams detect specification drift, weakened data controls, sensitive logging, and missing lineage before submission or audit deadlines. Low-risk corrections are prepared behind a deterministic policy gate, while changes affecting measure meaning or requiring attestation remain under human control.

## HOW_IT_WORKS
QI Sentinel reads versioned synthetic specifications and control-plane artifacts representing measure logic, value-set references, Snowflake policy exports, application logs, and lineage metadata—never production PHI rows. Deterministic scanners identify violations, Codex supplies bounded root-cause analysis and patch drafts, and deterministic policy evaluates whether each proposed action is eligible for remediation or must be escalated. Approved fixes are placed in a reviewable pull request, and every finding, decision, test, and action is recorded in a tamper-evident JSON and HTML evidence pack.

## WHAT_MAKES_IT_DIFFERENT
Unlike an alert-only monitor or an unconstrained AI agent, QI Sentinel separates repeatable control decisions from model reasoning: code owns rule IDs, severity, thresholds, remediation eligibility, and verification, while Codex explains findings and drafts changes. It also generates evidence when a finding occurs instead of reconstructing an audit trail later, and it never automatically merges, deploys, changes measure semantics, or fabricates missing history.

## MEASURED_RESULTS
End-to-end detection and remediation results are not yet measured because scanner implementation begins in Phase 2. Phase 1 is complete: the installable CLI and synthetic fixture catalog validate successfully, all four required defects have matching clean baselines, seven JSON artifacts pass format validation, package dependency checks pass, and two CLI smoke tests pass.

The target demonstration is one repeatable cycle that detects 4 of 4 seeded defects, reports zero findings on clean fixtures, prepares exactly two policy-approved fixes, escalates two findings with actionable analysis, passes regression and evidence-integrity checks, and creates no duplicate records on an identical rerun.

## WHY_IT_FITS
The solution directly supports proactive governance by moving compliance checks from a manual submission-time event into a continuous, policy-controlled monitoring loop. It reduces avoidable re-verification and late remediation while preserving human authority over clinical meaning, compliance attestation, and production change.
