"""Deterministic six-condition policy gate with a non-overridable hard floor."""

from __future__ import annotations

from qi_sentinel.models import Finding
from qi_sentinel.policy.config import PolicyConfig
from qi_sentinel.policy.models import GateCheck, PolicyDecision, RemediationProposal


class PolicyGate:
    def __init__(self, policy: PolicyConfig) -> None:
        self.policy = policy

    def evaluate(
        self,
        finding: Finding,
        proposal: RemediationProposal | None,
        *,
        tests_passed: bool,
        submitted_for_human_review: bool,
        mode: str | None = None,
    ) -> PolicyDecision:
        selected_mode = mode or self.policy.mode
        if selected_mode not in {"enforce", "observe"}:
            raise ValueError("Mode must be enforce or observe.")
        rule = self.policy.rules.get(finding.rule_id)
        proposal_matches = proposal is not None and proposal.rule_id == finding.rule_id
        category_matches = proposal is None or proposal.category == finding.category

        rule_allowed = bool(rule and rule.auto_fix_allowed and proposal_matches and category_matches)
        population_safe = bool(proposal is not None and not proposal.changes_measure_population)
        confidence_ok = finding.confidence >= self.policy.minimum_confidence
        allowlist_ok = bool(
            proposal is not None
            and set(proposal.files).issubset(self.policy.allowed_files)
            and set(proposal.commands).issubset(self.policy.allowed_commands)
        )
        review_ok = bool(
            submitted_for_human_review
            and self.policy.require_human_review
            and self.policy.merge == "never"
        )

        values = {
            "rule_allows_auto_fix": (
                rule_allowed,
                "Rule explicitly permits this matching deterministic proposal."
                if rule_allowed
                else "Rule does not permit this proposal for automatic remediation.",
            ),
            "does_not_change_measure_population": (
                population_safe,
                "Proposal does not change measure population semantics."
                if population_safe
                else "No population-safe proposal is available.",
            ),
            "confidence_meets_threshold": (
                confidence_ok,
                f"Confidence {finding.confidence:.2f} meets threshold {self.policy.minimum_confidence:.2f}."
                if confidence_ok
                else f"Confidence {finding.confidence:.2f} is below threshold {self.policy.minimum_confidence:.2f}.",
            ),
            "files_and_commands_are_allowlisted": (
                allowlist_ok,
                "Every proposed file and command is allowlisted."
                if allowlist_ok
                else "A proposed file or command is outside the allowlist.",
            ),
            "required_tests_pass": (
                tests_passed,
                "Required tests passed." if tests_passed else "Required tests did not pass.",
            ),
            "submitted_for_human_review": (
                review_ok,
                "A reviewable payload is required and merge remains never."
                if review_ok
                else "Human-review or merge-never requirements are not satisfied.",
            ),
        }
        checks = tuple(GateCheck(name, *values[name]) for name in self.policy.required_checks)

        hard_floor = finding.category in self.policy.never_auto_apply
        failed = {check.name for check in checks if not check.passed}
        if hard_floor or "rule_allows_auto_fix" in failed or "does_not_change_measure_population" in failed:
            disposition = "escalate"
        elif selected_mode == "observe":
            disposition = "held"
        elif failed:
            disposition = "held"
        else:
            disposition = "auto-fix"

        return PolicyDecision(
            finding_fingerprint=finding.fingerprint,
            rule_id=finding.rule_id,
            disposition=disposition,
            hard_floor_applied=hard_floor,
            checks=checks,
        )
