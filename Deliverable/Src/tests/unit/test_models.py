"""Validation and determinism tests for the raw finding schema."""

from __future__ import annotations

import pytest

from qi_sentinel.models import EvidenceReference, Finding, findings_json


def make_finding(**overrides: object) -> Finding:
    values: dict[str, object] = {
        "rule_id": "QI-TEST-001",
        "title": "Synthetic test finding",
        "severity": "high",
        "confidence": 1.0,
        "category": "test-control",
        "target": "SYNTHETIC.TARGET",
        "expected": "The synthetic control is present.",
        "observed": "The synthetic control is absent.",
        "evidence": (EvidenceReference("fixture.json", "Synthetic fixture state."),),
    }
    values.update(overrides)
    return Finding(**values)  # type: ignore[arg-type]


def test_fingerprint_uses_stable_control_identity() -> None:
    first = make_finding(observed="First wording.")
    second = make_finding(observed="Rephrased wording.")

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64


def test_canonical_json_is_independent_of_input_order() -> None:
    first = make_finding(rule_id="QI-TEST-002", target="B")
    second = make_finding(rule_id="QI-TEST-001", target="A")

    assert findings_json([first, second]) == findings_json([second, first])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rule_id", "invalid"),
        ("severity", "urgent"),
        ("confidence", 1.1),
        ("target", ""),
        ("evidence", ()),
    ],
)
def test_finding_rejects_invalid_fields(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        make_finding(**{field: value})
