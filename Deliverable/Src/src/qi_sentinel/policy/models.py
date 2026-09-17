"""Validated deterministic models for policy decisions and local actions."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

from qi_sentinel.models import Finding

DISPOSITIONS = frozenset({"auto-fix", "escalate", "held"})


@dataclass(frozen=True, slots=True)
class RemediationProposal:
    rule_id: str
    category: str
    changes_measure_population: bool
    files: tuple[str, ...]
    commands: tuple[str, ...]
    patch: str | None

    def __post_init__(self) -> None:
        if not self.rule_id.strip() or not self.category.strip():
            raise ValueError("Proposal rule ID and category must not be empty.")
        if not self.files:
            raise ValueError("A remediation proposal must name at least one file.")
        if not self.commands:
            raise ValueError("A remediation proposal must name at least one command.")
        if len(set(self.files)) != len(self.files) or len(set(self.commands)) != len(self.commands):
            raise ValueError("Proposal files and commands must not contain duplicates.")

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "changes_measure_population": self.changes_measure_population,
            "files": list(self.files),
            "commands": list(self.commands),
            "patch": self.patch,
        }


@dataclass(frozen=True, slots=True)
class GateCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    finding_fingerprint: str
    rule_id: str
    disposition: str
    hard_floor_applied: bool
    checks: tuple[GateCheck, ...]

    def __post_init__(self) -> None:
        if self.disposition not in DISPOSITIONS:
            raise ValueError(f"Unsupported disposition: {self.disposition!r}.")
        if not self.checks:
            raise ValueError("A policy decision must include its gate trace.")

    def to_dict(self) -> dict[str, object]:
        return {
            "finding_fingerprint": self.finding_fingerprint,
            "rule_id": self.rule_id,
            "disposition": self.disposition,
            "hard_floor_applied": self.hard_floor_applied,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True, slots=True)
class TestResult:
    command: str
    passed: bool
    exit_code: int
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class ActionCycleResult:
    mode: str
    findings: tuple[Finding, ...]
    decisions: tuple[PolicyDecision, ...]
    test_result: TestResult
    applied_files: tuple[str, ...]
    pull_request: dict[str, object] | None
    escalations: tuple[dict[str, object], ...]
    state_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "mode": self.mode,
            "finding_count": len(self.findings),
            "findings": [finding.to_dict() for finding in self.findings],
            "decisions": [decision.to_dict() for decision in self.decisions],
            "test_result": self.test_result.to_dict(),
            "applied_files": list(self.applied_files),
            "pull_request": self.pull_request,
            "escalations": list(self.escalations),
            "state_path": self.state_path,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def ordered_decisions(decisions: Iterable[PolicyDecision]) -> tuple[PolicyDecision, ...]:
    return tuple(sorted(decisions, key=lambda item: (item.rule_id, item.finding_fingerprint)))
