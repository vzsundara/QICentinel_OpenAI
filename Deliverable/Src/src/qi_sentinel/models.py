"""Validated, deterministic domain models for scanner output."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Iterable

RULE_ID_PATTERN = re.compile(r"^QI-[A-Z]+-\d{3}$")
VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


@dataclass(frozen=True, slots=True, order=True)
class EvidenceReference:
    """A sanitized reference to evidence inspected by a scanner."""

    path: str
    detail: str

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValueError("Evidence path must not be empty.")
        if not self.detail.strip():
            raise ValueError("Evidence detail must not be empty.")

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class Finding:
    """A raw deterministic finding produced before policy evaluation."""

    rule_id: str
    title: str
    severity: str
    confidence: float
    category: str
    target: str
    expected: str
    observed: str
    evidence: tuple[EvidenceReference, ...]
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if not RULE_ID_PATTERN.fullmatch(self.rule_id):
            raise ValueError(f"Invalid rule ID: {self.rule_id!r}")
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0.")
        for field_name in ("title", "category", "target", "expected", "observed"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not self.evidence:
            raise ValueError("A finding must contain at least one evidence reference.")

        ordered_evidence = tuple(sorted(self.evidence))
        object.__setattr__(self, "evidence", ordered_evidence)
        fingerprint_source = json.dumps(
            {
                "expected": self.expected,
                "rule_id": self.rule_id,
                "target": self.target,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        object.__setattr__(self, "fingerprint", hashlib.sha256(fingerprint_source).hexdigest())

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "confidence": self.confidence,
            "evidence": [reference.to_dict() for reference in self.evidence],
            "expected": self.expected,
            "fingerprint": self.fingerprint,
            "observed": self.observed,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "target": self.target,
            "title": self.title,
        }


def ordered_findings(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """Return findings in the canonical cross-platform order."""

    ordered = tuple(sorted(findings, key=lambda item: (item.rule_id, item.target, item.fingerprint)))
    fingerprints = [finding.fingerprint for finding in ordered]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("Duplicate finding fingerprints are not allowed.")
    return ordered


def findings_payload(findings: Iterable[Finding]) -> dict[str, object]:
    """Build the Phase 2 canonical findings payload."""

    ordered = ordered_findings(findings)
    return {
        "schema_version": 1,
        "finding_count": len(ordered),
        "findings": [finding.to_dict() for finding in ordered],
    }


def findings_json(findings: Iterable[Finding]) -> str:
    """Serialize findings predictably for files, CLI output, and tests."""

    return json.dumps(
        findings_payload(findings),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
