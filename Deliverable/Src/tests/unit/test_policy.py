"""Unit tests for the six-condition policy gate and hard floor."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from qi_sentinel.models import EvidenceReference, Finding
from qi_sentinel.policy import PolicyConfig, PolicyConfigError, PolicyGate, RemediationProposal

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _finding(**overrides: object) -> Finding:
    values: dict[str, object] = {
        "rule_id": "QI-MASK-001",
        "title": "Synthetic masking finding",
        "severity": "critical",
        "confidence": 1.0,
        "category": "access-control-restoration",
        "target": "RPT.MEMBER_MEASURE.DOB",
        "expected": "The masking policy is attached.",
        "observed": "The masking policy is absent.",
        "evidence": (EvidenceReference("fixture.json", "Synthetic fixture state."),),
    }
    values.update(overrides)
    return Finding(**values)  # type: ignore[arg-type]


def _proposal(**overrides: object) -> RemediationProposal:
    values: dict[str, object] = {
        "rule_id": "QI-MASK-001",
        "category": "access-control-restoration",
        "changes_measure_population": False,
        "files": ("mock-platform/snowflake/policies/member_measure.sql",),
        "commands": ("python -m pytest",),
        "patch": "--- synthetic patch",
    }
    values.update(overrides)
    return RemediationProposal(**values)  # type: ignore[arg-type]


def _gate() -> PolicyGate:
    return PolicyGate(PolicyConfig.load(PROJECT_ROOT / "config/policy.yml"))


def test_all_six_gate_conditions_pass_for_masking_fix() -> None:
    decision = _gate().evaluate(
        _finding(),
        _proposal(),
        tests_passed=True,
        submitted_for_human_review=True,
    )

    assert decision.disposition == "auto-fix"
    assert [check.name for check in decision.checks] == list(_gate().policy.required_checks)
    assert all(check.passed for check in decision.checks)


@pytest.mark.parametrize(
    ("check_name", "finding", "proposal", "tests_passed", "review", "disposition"),
    [
        (
            "rule_allows_auto_fix",
            _finding(),
            _proposal(rule_id="QI-LOG-001"),
            True,
            True,
            "escalate",
        ),
        (
            "does_not_change_measure_population",
            _finding(),
            _proposal(changes_measure_population=True),
            True,
            True,
            "escalate",
        ),
        (
            "confidence_meets_threshold",
            _finding(confidence=0.5),
            _proposal(),
            True,
            True,
            "held",
        ),
        (
            "files_and_commands_are_allowlisted",
            _finding(),
            _proposal(files=("mock-platform/measures/cbp/cbp_rate.sql",)),
            True,
            True,
            "held",
        ),
        (
            "files_and_commands_are_allowlisted",
            _finding(),
            _proposal(commands=("git push",)),
            True,
            True,
            "held",
        ),
        (
            "required_tests_pass",
            _finding(),
            _proposal(),
            False,
            True,
            "held",
        ),
        (
            "submitted_for_human_review",
            _finding(),
            _proposal(),
            True,
            False,
            "held",
        ),
    ],
)
def test_each_failed_gate_condition_blocks_automatic_action(
    check_name: str,
    finding: Finding,
    proposal: RemediationProposal,
    tests_passed: bool,
    review: bool,
    disposition: str,
) -> None:
    decision = _gate().evaluate(
        finding,
        proposal,
        tests_passed=tests_passed,
        submitted_for_human_review=review,
    )

    checks = {check.name: check.passed for check in decision.checks}
    assert checks[check_name] is False
    assert decision.disposition == disposition


def test_observe_mode_holds_an_otherwise_eligible_fix() -> None:
    decision = _gate().evaluate(
        _finding(),
        _proposal(),
        tests_passed=True,
        submitted_for_human_review=True,
        mode="observe",
    )

    assert decision.disposition == "held"
    assert all(check.passed for check in decision.checks)


def test_semantic_model_patch_cannot_override_hard_floor() -> None:
    finding = _finding(
        rule_id="QI-SEM-001",
        severity="high",
        category="measure-semantics",
        target="CBP",
    )
    proposal = _proposal(
        rule_id="QI-SEM-001",
        category="measure-semantics",
        changes_measure_population=False,
        files=("mock-platform/snowflake/policies/member_measure.sql",),
    )

    decision = _gate().evaluate(
        finding,
        proposal,
        tests_passed=True,
        submitted_for_human_review=True,
    )

    assert decision.hard_floor_applied is True
    assert decision.disposition == "escalate"


def test_policy_rejects_merge_enablement(tmp_path: Path) -> None:
    payload = yaml.safe_load((PROJECT_ROOT / "config/policy.yml").read_text(encoding="utf-8"))
    payload["pull_requests"]["merge"] = "automatic"
    path = tmp_path / "policy.yml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(PolicyConfigError, match="merge must remain never"):
        PolicyConfig.load(path)
